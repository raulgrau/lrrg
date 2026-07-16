#!/usr/bin/env python
"""
Retroactively re-run the guardrail's accept/reject decision using RadGraph-F1
instead of CheXbert-F1, from the texts already sitting in icl_final.jsonl --
no MAIRA-2/Qwen rerun needed. draft_text and revised_text for every case are
already cached; this script just re-scores them against the reference with
F1RadGraph and re-applies the same strict_per_case rule guardrail.py uses
(accept iff revised_f1 >= draft_f1, else keep the draft), swapping which F1
that rule looks at.

Rationale (see summary.md "Next steps"): CheXbert-F1 barely reacts to
comparison-sentence rephrasing, so the existing guardrail's accept/reject
decisions are close to arbitrary from RadGraph-F1's point of view (confirmed
separately: removing the CheXbert guardrail entirely barely moved BLEU-4/
ROUGE-L). If RadGraph-F1 is a more sensitive filter for this specific
intervention, gating on it directly should do a better job of keeping good
revisions and reverting bad ones than the CheXbert-gated or no-guardrail
variants did.

Outputs:
  --out-csv    same shape export_for_score.py produces (reference,
               pred_without_prior, pred_with_prior, change) -- feed straight
               into lrrg_ablation/score.py, directly comparable to
               icl_predictions_guardrailed.csv and icl_predictions_no_guardrail.csv.
  --out-jsonl  per-case decision detail (both RadGraph-F1s, both guardrails'
               accept flags side by side) -- diff this against icl_final.jsonl's
               own accepted/draft_f1/revised_f1 to see exactly which cases the
               two guardrails disagree on, and in which direction.

Usage:
    python reguardrail_radgraph.py \
        --final-output runs/icl_final.jsonl \
        --test-manifest ~/lrrg/test_pairs_ulcx.jsonl \
        --out-csv icl_predictions_radgraph_guardrail.csv \
        --out-jsonl icl_final_radgraph_guardrail.jsonl
    cd ../lrrg_ablation
    python score.py --preds ../icl_pipeline/icl_predictions_radgraph_guardrail.csv \
        --out-json icl_results_radgraph_guardrail.json
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from config import PATHS


def load_jsonl(path: Path) -> list:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-output", default=str(PATHS.final_output_file))
    parser.add_argument("--test-manifest", default=str(PATHS.test_manifest))
    parser.add_argument("--reward-level", default="partial", help="F1RadGraph reward_level, matches score.py's default")
    parser.add_argument("--out-csv", default="icl_predictions_radgraph_guardrail.csv")
    parser.add_argument("--out-jsonl", default="icl_final_radgraph_guardrail.jsonl")
    args = parser.parse_args()

    from radgraph import F1RadGraph

    print(f"loading {args.final_output} ...")
    records = load_jsonl(Path(args.final_output))
    print(f"loaded {len(records)} records")

    print(f"loading {args.test_manifest} ...")
    manifest = load_jsonl(Path(args.test_manifest))
    ref_by_id = {r["current_study_id"]: r["reference_findings"] for r in manifest}

    missing_ref = [r["study_id"] for r in records if r["study_id"] not in ref_by_id]
    if missing_ref:
        print(f"WARNING: {len(missing_ref)} records have no reference in the manifest, dropping them")
        records = [r for r in records if r["study_id"] not in ref_by_id]

    references = [ref_by_id[r["study_id"]] for r in records]
    draft_texts = [r["draft_text"] for r in records]
    revised_texts = [r["revised_text"] for r in records]

    print(f"scoring RadGraph-F1 (reward_level={args.reward_level}) for {len(records)} drafts ...")
    f1rg = F1RadGraph(reward_level=args.reward_level)
    _, rg_draft, _, _ = f1rg(hyps=draft_texts, refs=references)
    print("scoring RadGraph-F1 for revisions ...")
    _, rg_revised, _, _ = f1rg(hyps=revised_texts, refs=references)
    rg_draft = np.asarray(rg_draft, dtype=float)
    rg_revised = np.asarray(rg_revised, dtype=float)

    out_records = []
    csv_rows = []
    reject_count = 0
    disagree_count = 0  # cases where this guardrail's accept differs from the original CheXbert guardrail's
    reject_by_change = {True: 0, False: 0}
    total_by_change = {True: 0, False: 0}

    for i, rec in enumerate(records):
        change = bool(rec.get("change")) if rec.get("change") is not None else None
        revision_succeeded = rec.get("revision_succeeded", True)

        if not revision_succeeded:
            accepted = False
            final_text = rec["draft_text"]
        else:
            accepted = bool(rg_revised[i] >= rg_draft[i])
            final_text = rec["revised_text"] if accepted else rec["draft_text"]

        if not accepted:
            reject_count += 1
            if change is not None:
                reject_by_change[change] += 1
        if change is not None:
            total_by_change[change] += 1
        if accepted != rec["accepted"]:
            disagree_count += 1

        out_records.append(
            {
                "study_id": rec["study_id"],
                "change": rec.get("change"),
                "draft_radgraph_f1": float(rg_draft[i]),
                "revised_radgraph_f1": float(rg_revised[i]),
                "accepted_radgraph_guardrail": accepted,
                "accepted_chexbert_guardrail": rec["accepted"],
                "guardrails_disagree": accepted != rec["accepted"],
                "final_text": final_text,
            }
        )
        csv_rows.append(
            {
                "reference": references[i],
                "pred_without_prior": rec["draft_text"],
                "pred_with_prior": final_text,
                "change": "1" if rec.get("change") else "0",
            }
        )

    n = len(records)
    print(
        f"\nRadGraph-gated guardrail: reject_count={reject_count}/{n} "
        f"(reject_rate={reject_count / n:.3f})"
    )
    for flag, label in ((True, "change"), (False, "no_change")):
        tot = total_by_change[flag]
        if tot:
            print(f"  {label}: reject {reject_by_change[flag]}/{tot} ({reject_by_change[flag] / tot:.3f})")
    print(
        f"disagrees with the original CheXbert-gated guardrail on "
        f"{disagree_count}/{n} cases ({disagree_count / n:.3f}) -- these are exactly the cases "
        f"where CheXbert-F1 and RadGraph-F1 gave opposite verdicts on the same revision."
    )
    print(f"mean draft RadGraph-F1={rg_draft.mean():.4f}  mean revised RadGraph-F1={rg_revised.mean():.4f}")

    with open(args.out_jsonl, "w") as f:
        for rec in out_records:
            f.write(json.dumps(rec) + "\n")
    print(f"wrote {len(out_records)} per-case decisions -> {args.out_jsonl}")

    with open(args.out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["reference", "pred_without_prior", "pred_with_prior", "change"])
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"wrote {len(csv_rows)} rows -> {args.out_csv}")
    print(
        "next: cd into wherever score.py lives and run "
        f"`python score.py --preds <path-to>/{args.out_csv} --out-json icl_results_radgraph_guardrail.json`, "
        "then compare against icl_results.json (CheXbert-gated) and icl_results_no_guardrail.json"
    )


if __name__ == "__main__":
    main()
