#!/usr/bin/env python
"""
Convert icl_final.jsonl into the CSV shape lrrg_ablation/score.py expects,
so you get the real metric stack (RadGraph-F1, CheXbert-F1 stratified with
bootstrap CIs) instead of relying on this pipeline's own guardrail F1 --
which, as observed on a real run, is often identical between draft and
final: CheXbert-14 scores pathology presence, not comparison-sentence
phrasing, so it's structurally blind to whether the ICL revision actually
improved temporal/comparison quality. RadGraph-F1 and the manual read are
the more informative signal for that.

score.py expects columns: reference, pred_without_prior, pred_with_prior,
change (optional). Column names are score.py's own (built for the DDaTR
with/without-prior ablation) -- reused as-is here so score.py doesn't need
touching, with a semantic remap documented below rather than in the column
names themselves:
    pred_without_prior  <-  draft_text   (MAIRA-2 draft, pre-ICL)
    pred_with_prior     <-  final_text   (post-ICL: revised if the guardrail
                                          accepted it, draft otherwise)
    reference           <-  reference_findings, joined back from
                            test_pairs_ulcx.jsonl by study_id (icl_final.jsonl
                            doesn't carry the ground-truth text itself)

Usage:
    python export_for_score.py --out icl_predictions.csv
    cd ../lrrg_ablation   # or wherever score.py lives
    python score.py --preds ../icl_pipeline/icl_predictions.csv --out-json icl_results.json
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
    parser.add_argument("--out", default="icl_predictions.csv")
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
    for rec in final_records:
        study_id = rec["study_id"]
        reference = reference_by_study_id.get(study_id)
        if reference is None:
            missing_ref += 1
            continue
        rows.append(
            {
                "reference": reference,
                "pred_without_prior": rec["draft_text"],
                "pred_with_prior": rec["final_text"],
                "change": "1" if rec.get("change") else "0",
            }
        )

    if missing_ref:
        print(f"WARNING: {missing_ref} records had no matching study_id in the test manifest, skipped")

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["reference", "pred_without_prior", "pred_with_prior", "change"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows -> {args.out}")
    print(
        "next: cd into wherever score.py lives and run "
        f"`python score.py --preds <path-to>/{args.out} --out-json icl_results.json`"
    )


if __name__ == "__main__":
    main()
