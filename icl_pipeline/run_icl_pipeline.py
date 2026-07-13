#!/usr/bin/env python
"""
Orchestrator for the ICL retrieve-then-revise pipeline over the ULCX test
split (test_pairs_ulcx.jsonl, 1,786 pairs, restricted here to cases with both
prior image AND prior report -- the valid prior-conditioned population per
project memory, since the processor silently drops prior_report if
prior_frontal is None).

Per case: MAIRA-2 draft -> CheXbert change signature -> retrieve exemplars
-> Qwen revise -> CheXbert-F1 guardrail -> write result.

Resumable: re-running skips study_ids already present in the output files.
Run inside tmux (canonical: `tmux new -s lrrg`) to survive SSH disconnects.
ETA is reported every 25 cases.

Usage:
    export XDG_CACHE_HOME=/var/tmp/xdg_cache_grauperez
    unset LD_LIBRARY_PATH
    python run_icl_pipeline.py --limit 20   # smoke test
    python run_icl_pipeline.py              # full run
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from chexbert_utils import CheXbertLabeler, change_signature
from config import GUARDRAIL, PATHS, RETRIEVAL
from guardrail import Guardrail
from maira2_draft import MAIRA2Drafter
from retrieve import Retriever
from revise import Reviser


def load_manifest(path: Path) -> list:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_jsonl_index(path: Path, key: str) -> dict:
    """Load an existing jsonl output file into a {key_value: record} dict, for resumability."""
    if not path.exists():
        return {}
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec[key]] = rec
    return out


def append_jsonl(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
        f.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="cap number of cases, for smoke testing")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    print("loading test manifest...")
    all_cases = load_manifest(PATHS.test_manifest)
    # Valid population per memory: prior-conditioned arm requires both a
    # prior image and a prior report.
    cases = [
        c for c in all_cases
        if c.get("prior_image") and c.get("prior_findings") and c.get("current_image") and c.get("reference_findings")
    ]
    print(f"{len(cases)}/{len(all_cases)} test cases have both prior image + prior report (valid population)")
    if args.limit:
        cases = cases[: args.limit]
        print(f"--limit set: running on first {len(cases)} cases")

    print("loading CheXbert (f1chexbert)...")
    labeler = CheXbertLabeler(device=args.device)

    print("labeling prior reports (signed, for change signature) + ground-truth current reports (presence, for guardrail F1) -- one-time...")
    prior_signed_all = labeler.label_signed_batch([c["prior_findings"] for c in cases])
    gt_presence_all = labeler.label_presence_batch([c["reference_findings"] for c in cases])

    print("loading existing outputs for resumability...")
    draft_cache = load_jsonl_index(PATHS.draft_cache_file, key="study_id")
    final_cache = load_jsonl_index(PATHS.final_output_file, key="study_id")

    remaining = [c for c in cases if c.get("current_study_id") not in final_cache]
    print(f"{len(final_cache)} cases already done, {len(remaining)} remaining")

    if not remaining:
        print("nothing to do.")
        _print_summary_from_existing(final_cache)
        return

    print("loading MAIRA-2 drafter...")
    drafter = MAIRA2Drafter(PATHS.maira2_model_id, device=args.device)
    print("loading retriever...")
    retriever = Retriever()
    print("loading Qwen reviser...")
    reviser = Reviser(PATHS.qwen_model_id, device=args.device)
    guardrail = Guardrail(labeler, mode=GUARDRAIL.mode)

    # seed guardrail history from already-completed cases so summary() at the
    # end reflects the full run, not just this invocation's increment.
    for rec in final_cache.values():
        change = rec.get("change")
        guardrail.total_count += 1
        guardrail.draft_f1_history.append(rec["draft_f1"])
        final_f1 = rec["revised_f1"] if rec["accepted"] else rec["draft_f1"]
        guardrail.final_f1_history.append(final_f1)
        if not rec["accepted"]:
            guardrail.reject_count += 1
        if change is not None:
            guardrail.total_count_by_change[bool(change)] += 1
            guardrail.draft_f1_by_change[bool(change)].append(rec["draft_f1"])
            guardrail.final_f1_by_change[bool(change)].append(final_f1)
            if not rec["accepted"]:
                guardrail.reject_count_by_change[bool(change)] += 1

    case_index = {c["current_study_id"]: i for i, c in enumerate(cases)}
    start_time = time.time()

    for n_processed, case in enumerate(remaining, start=1):
        study_id = case["current_study_id"]
        idx = case_index[study_id]

        if study_id in draft_cache:
            draft_text = draft_cache[study_id]["draft_text"]
        else:
            draft_text = drafter.draft(
                current_frontal_path=case["current_image"],
                prior_frontal_path=case["prior_image"],
                prior_report_text=case["prior_findings"],
                indication=case.get("indication"),
                comparison=case.get("comparison"),
            )
            append_jsonl(PATHS.draft_cache_file, {"study_id": study_id, "draft_text": draft_text})

        current_signed = labeler.label_signed(draft_text)
        query_signature = change_signature(prior_signed_all[idx], current_signed)

        query_diff_embedding = None
        if RETRIEVAL.use_image_diff:
            from image_diff_utils import RadDinoEmbedder

            # NOTE: instantiated lazily and cached on the function object --
            # image-diff retrieval is opt-in and off by default, so this
            # stays simple rather than adding a module-level singleton.
            if not hasattr(main, "_embedder"):
                main._embedder = RadDinoEmbedder(PATHS.raddino_model_id, device=args.device)
            query_diff_embedding = main._embedder.embed_diff(
                [case["prior_image"]], [case["current_image"]]
            )[0]

        exemplars = retriever.retrieve(query_signature, query_diff_embedding=query_diff_embedding)
        revised_text, success = reviser.revise(draft_text, exemplars)
        result = guardrail.score_case(
            draft_text, revised_text, success, gt_presence_all[idx], change=case.get("change")
        )

        append_jsonl(
            PATHS.final_output_file,
            {
                "study_id": study_id,
                "change": case.get("change"),
                "draft_text": draft_text,
                "revised_text": revised_text,
                "final_text": result.final_text,
                "accepted": result.accepted,
                "draft_f1": result.draft_f1,
                "revised_f1": result.revised_f1,
                "revision_succeeded": success,
                "exemplar_study_ids": [e.study_id for e in exemplars],
            },
        )

        if n_processed % 25 == 0 or n_processed == len(remaining):
            elapsed = time.time() - start_time
            rate = elapsed / n_processed
            eta_seconds = rate * (len(remaining) - n_processed)
            print(
                f"[{n_processed}/{len(remaining)}] "
                f"elapsed={elapsed/60:.1f}min eta={eta_seconds/60:.1f}min "
                f"reject_rate_so_far={guardrail.reject_count / guardrail.total_count:.3f}"
            )

    print("done.")
    print(json.dumps(guardrail.summary(), indent=2))


def _print_summary_from_existing(final_cache: dict):
    if not final_cache:
        return
    draft_f1s = [r["draft_f1"] for r in final_cache.values()]
    final_f1s = [r["revised_f1"] if r["accepted"] else r["draft_f1"] for r in final_cache.values()]
    rejects = sum(1 for r in final_cache.values() if not r["accepted"])
    print(
        json.dumps(
            {
                "n_cases": len(final_cache),
                "reject_count": rejects,
                "reject_rate": rejects / len(final_cache),
                "draft_mean_f1": float(np.mean(draft_f1s)),
                "final_mean_f1": float(np.mean(final_f1s)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
