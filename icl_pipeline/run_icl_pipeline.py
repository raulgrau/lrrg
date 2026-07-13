#!/usr/bin/env python
"""
Orchestrator for the ICL retrieve-then-revise pipeline over the ULCX test
split (test_pairs_ulcx.jsonl, 1,786 pairs, restricted here to cases with both
prior image AND prior report -- the valid prior-conditioned population per
project memory, since the processor silently drops prior_report if
prior_frontal is None).

Per case: MAIRA-2 draft -> CheXbert change signature -> retrieve exemplars
-> Qwen revise -> CheXbert-F1 guardrail -> write result.

IMPORTANT -- GPU memory: MAIRA-2 (RAD-DINO + Vicuna-7B) and Qwen2.5-7B-Instruct
are each ~7B params, ~15GB in bf16. Together they don't fit on a single 24GB
RTX 3090 (confirmed: loading both at once OOMs). This script therefore runs
as two stages that are never GPU-resident at the same time:
  --stage draft   loads ONLY MAIRA-2, drafts every case, caches to disk, exits.
  --stage revise  loads CheXbert + Qwen (NOT MAIRA-2), reads drafts from the
                  cache, does retrieve -> revise -> guardrail -> write.
  --stage all     (default) runs draft stage to completion, explicitly frees
                  MAIRA-2 from GPU memory, then runs revise stage in the same
                  process. Safe on a single GPU; just takes the two stages'
                  wall-clock time back to back instead of overlapping them.

Resumable: re-running skips study_ids already present in the output files
(draft stage skips studies already in drafts.jsonl; revise stage skips
studies already in icl_final.jsonl).
Run inside tmux (canonical: `tmux new -s lrrg`) to survive SSH disconnects.
ETA is reported every 25 cases.

Usage:
    export XDG_CACHE_HOME=/var/tmp/xdg_cache_grauperez
    unset LD_LIBRARY_PATH
    python run_icl_pipeline.py --limit 20            # smoke test, both stages
    python run_icl_pipeline.py --stage draft         # just draft everything
    python run_icl_pipeline.py --stage revise        # then retrieve+revise+guardrail
    python run_icl_pipeline.py                       # full run, both stages back to back
"""
import argparse
import gc
import json
import time
from pathlib import Path

import numpy as np

from chexbert_utils import CheXbertLabeler, change_signature
from config import GUARDRAIL, PATHS, RETRIEVAL
from guardrail import Guardrail
from retrieve import Retriever


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


def get_valid_cases(limit=None):
    all_cases = load_manifest(PATHS.test_manifest)
    # Valid population per memory: prior-conditioned arm requires both a
    # prior image and a prior report.
    cases = [
        c for c in all_cases
        if c.get("prior_image") and c.get("prior_findings") and c.get("current_image") and c.get("reference_findings")
    ]
    print(f"{len(cases)}/{len(all_cases)} test cases have both prior image + prior report (valid population)")
    if limit:
        cases = cases[:limit]
        print(f"--limit set: running on first {len(cases)} cases")
    return cases


def run_draft_stage(cases, device: str):
    """Loads ONLY MAIRA-2. Drafts every case not already cached, appends to
    draft_cache_file as it goes (resumable). Returns nothing -- callers read
    the cache file back."""
    from maira2_draft import MAIRA2Drafter

    draft_cache = load_jsonl_index(PATHS.draft_cache_file, key="study_id")
    remaining = [c for c in cases if c["current_study_id"] not in draft_cache]
    print(f"[draft] {len(draft_cache)} drafts already cached, {len(remaining)} remaining")
    if not remaining:
        return

    print("[draft] loading MAIRA-2...")
    drafter = MAIRA2Drafter(PATHS.maira2_model_id, device=device)

    start_time = time.time()
    for n_processed, case in enumerate(remaining, start=1):
        study_id = case["current_study_id"]
        draft_text = drafter.draft(
            current_frontal_path=case["current_image"],
            prior_frontal_path=case["prior_image"],
            prior_report_text=case["prior_findings"],
            indication=case.get("indication"),
            comparison=case.get("comparison"),
        )
        append_jsonl(PATHS.draft_cache_file, {"study_id": study_id, "draft_text": draft_text})

        if n_processed % 25 == 0 or n_processed == len(remaining):
            elapsed = time.time() - start_time
            rate = elapsed / n_processed
            eta_seconds = rate * (len(remaining) - n_processed)
            print(f"[draft] [{n_processed}/{len(remaining)}] elapsed={elapsed/60:.1f}min eta={eta_seconds/60:.1f}min")

    # Explicitly free MAIRA-2's GPU memory before the caller (run_stage="all")
    # loads Qwen -- del alone isn't enough, torch keeps the CUDA caching
    # allocator's pool around until empty_cache() is called.
    print("[draft] freeing MAIRA-2 from GPU memory...")
    import torch

    del drafter
    gc.collect()
    torch.cuda.empty_cache()


def run_revise_stage(cases, device: str):
    """Loads CheXbert + Qwen (NOT MAIRA-2). Reads drafts from draft_cache_file
    (must already exist -- run --stage draft first if running stages
    separately), does retrieve -> revise -> guardrail -> write."""
    from revise import Reviser

    print("[revise] loading CheXbert (f1chexbert)...")
    labeler = CheXbertLabeler(device=device)

    print("[revise] labeling prior reports (signed) + ground-truth current reports (presence) -- one-time...")
    prior_signed_all = labeler.label_signed_batch([c["prior_findings"] for c in cases])
    gt_presence_all = labeler.label_presence_batch([c["reference_findings"] for c in cases])

    draft_cache = load_jsonl_index(PATHS.draft_cache_file, key="study_id")
    final_cache = load_jsonl_index(PATHS.final_output_file, key="study_id")

    missing_drafts = [c for c in cases if c["current_study_id"] not in draft_cache and c["current_study_id"] not in final_cache]
    if missing_drafts:
        print(
            f"[revise] WARNING: {len(missing_drafts)} cases have no cached draft and aren't in "
            f"final output either -- run `--stage draft` first (or `--stage all`) to cover them. "
            f"Skipping them for now."
        )

    remaining = [
        c for c in cases
        if c["current_study_id"] not in final_cache and c["current_study_id"] in draft_cache
    ]
    print(f"[revise] {len(final_cache)} cases already done, {len(remaining)} remaining")

    if not remaining:
        print("[revise] nothing to do.")
        _print_summary_from_existing(final_cache)
        return

    print("[revise] loading retriever...")
    retriever = Retriever()
    print("[revise] loading Qwen reviser...")
    reviser = Reviser(PATHS.qwen_model_id, device=device)
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
        draft_text = draft_cache[study_id]["draft_text"]

        current_signed = labeler.label_signed(draft_text)
        query_signature = change_signature(prior_signed_all[idx], current_signed)

        query_diff_embedding = None
        if RETRIEVAL.use_image_diff:
            from image_diff_utils import RadDinoEmbedder

            if not hasattr(run_revise_stage, "_embedder"):
                run_revise_stage._embedder = RadDinoEmbedder(PATHS.raddino_model_id, device=device)
            query_diff_embedding = run_revise_stage._embedder.embed_diff(
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
                f"[revise] [{n_processed}/{len(remaining)}] "
                f"elapsed={elapsed/60:.1f}min eta={eta_seconds/60:.1f}min "
                f"reject_rate_so_far={guardrail.reject_count / guardrail.total_count:.3f}"
            )

    print("[revise] done.")
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="cap number of cases, for smoke testing")
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--stage", choices=["draft", "revise", "all"], default="all",
        help="run just the MAIRA-2 drafting stage, just the retrieve/revise/guardrail "
             "stage (requires drafts already cached), or both back to back (default). "
             "MAIRA-2 and Qwen are never loaded on the GPU at the same time.",
    )
    args = parser.parse_args()

    print("loading test manifest...")
    cases = get_valid_cases(limit=args.limit)

    if args.stage in ("draft", "all"):
        run_draft_stage(cases, device=args.device)
        if args.stage == "draft":
            print("[draft] stage complete. Run `--stage revise` next.")
            return

    if args.stage in ("revise", "all"):
        run_revise_stage(cases, device=args.device)


if __name__ == "__main__":
    main()
