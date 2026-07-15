#!/usr/bin/env python
"""
"What if we got rid of the guardrail?" -- variant of export_for_score.py that
always uses revised_text as pred_with_prior, instead of the guardrail-gated
final_text (= revised_text if accepted else draft_text).

No rerun of MAIRA-2/Qwen needed: icl_final.jsonl already has revised_text for
every case (revise.py returns the draft unchanged with revision_succeeded=False
on failure, so "no guardrail" here means "always take whatever revise.py
produced" -- for the ~2.5% of cases where revision failed to parse, that's
still just the draft, since revise.py's own fallback already put it there).

score.py's own column names (built for the DDaTR ablation) are reused as-is:
    pred_without_prior  <-  draft_text     (unchanged from the guardrailed export)
    pred_with_prior     <-  revised_text   (NOT final_text -- this is the only
                                            change vs. export_for_score.py)
    reference           <-  reference_findings, joined back from
                            test_pairs_ulcx.jsonl by study_id

Usage:
    python export_for_score_no_guardrail.py --out icl_predictions_no_guardrail.csv
    cd ../lrrg_ablation
    python score.py --preds ../icl_pipeline/icl_predictions_no_guardrail.csv --out-json icl_results_no_guardrail.json

Then diff icl_results.json (guardrailed) vs icl_results_no_guardrail.json --
if the no-guardrail numbers are close to or worse than the guardrailed ones,
the guardrail was doing real work (screening out net-harmful revisions,
consistent with the 2.5% reject rate observed on the guardrailed run). If
they're about the same, the guardrail's accept/reject decisions weren't
actually distinguishing good revisions from bad ones on this metric.
"""
import argparse
import csv
import json
from pathlib import Path

from config import PATHS


def load_manifest(path: Path) -> list:
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
    parser.add_argument("--out", default="icl_predictions_no_guardrail.csv")
    args = parser.parse_args()

    print(f"loading {args.final_output} ...")
    final_records = []
    with open(args.final_output) as f:
        for line in f:
            line = line.strip()
            if line:
                final_records.append(json.loads(line))
    print(f"loaded {len(final_records)} ICL pipeline results")

    print(f"loading {args.test_manifest} for ground-truth reference text ...")
    manifest = load_manifest(Path(args.test_manifest))
    reference_by_study_id = {r["current_study_id"]: r["reference_findings"] for r in manifest}

    rows = []
    missing_ref = 0
    would_have_been_rejected = 0
    for rec in final_records:
        study_id = rec["study_id"]
        reference = reference_by_study_id.get(study_id)
        if reference is None:
            missing_ref += 1
            continue
        if not rec.get("accepted", True):
            would_have_been_rejected += 1
        rows.append(
            {
                "reference": reference,
                "pred_without_prior": rec["draft_text"],
                "pred_with_prior": rec["revised_text"],  # <-- the only difference vs export_for_score.py
                "change": "1" if rec.get("change") else "0",
            }
        )

    if missing_ref:
        print(f"WARNING: {missing_ref} records had no matching study_id in the test manifest, skipped")
    print(
        f"{would_have_been_rejected}/{len(rows)} rows use a revised_text that the guardrail "
        f"would have rejected in the gated pipeline -- this is exactly the extra exposure "
        f"a no-guardrail deployment would take on."
    )

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["reference", "pred_without_prior", "pred_with_prior", "change"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows -> {args.out}")
    print(
        "next: cd into wherever score.py lives and run "
        f"`python score.py --preds <path-to>/{args.out} --out-json icl_results_no_guardrail.json`, "
        "then compare against the guardrailed icl_results.json"
    )


if __name__ == "__main__":
    main()
