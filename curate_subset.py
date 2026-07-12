#!/usr/bin/env python3
"""
curate_subset.py  —  Build a small longitudinal MIMIC-CXR test subset from a
LOCAL copy of the dataset (no downloads).

Reads:
  --meta          metadata CSV (mimic-cxr-2.0.0-metadata.csv[.gz])
  --images-root   .../mimic-cxr-jpg/<ver>/files
  --reports-root  folder containing the per-study .txt reports
  --split-csv     mimic-cxr-2.0.0-split.csv[.gz]  (auto-detected if omitted)

Writes subset.jsonl, one case per line, pointing at the on-disk image paths
(no copying). Schema is unchanged, so run_ablation.py / score.py work as-is.

Example (defaults are your cgpool paths):
    python curate_subset.py --n 40 --prior-mode report_only --out subset.jsonl
"""

import argparse
import glob
import json
import os
import random
import sys

import pandas as pd

from utils_reports import get_findings, get_prior_report, get_field

# ---- your cgpool paths as defaults ------------------------------------------
DEF_META = "/graphics/scratch2/students/mpindabe/Datasets/mimic-cxr-reports/mimic-cxr-2.0.0-metadata.csv"
DEF_IMAGES = "/graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/physionet.org/files/mimic-cxr-jpg/2.0.0/files"
DEF_REPORTS = "/graphics/scratch2/students/mpindabe/Datasets/mimic-cxr-reports/files_reports"
# -----------------------------------------------------------------------------

POS_MARKERS = [
    "prior", "previous", "interval", "compared", "unchanged",
    "stable", "improv", "worsen", "increas", "decreas", "resolv", "again",
    "persist", "new ", "removed", "redemonstrat", "re-demonstrat", "progress",
]
NEG_CONTEXTS = [
    "no prior", "no previous", "no significant interval", "no interval change",
    "no interval", "no comparison", "without comparison", "no recent",
    "no earlier", "no relevant",
]

# report path layouts tried during auto-detection ({subj2}=first 2 digits)
REPORT_TEMPLATES = [
    "{root}/p{subj2}/p{subj}/s{study}.txt",
    "{root}/files/p{subj2}/p{subj}/s{study}.txt",
    "{root}/p{subj}/s{study}.txt",
]


def has_longitudinal(findings: str) -> bool:
    f = " " + findings.lower() + " "
    for neg in NEG_CONTEXTS:
        f = f.replace(neg, " ")
    return any(p in f for p in POS_MARKERS)


def read_text(path):
    try:
        with open(path, "r", errors="ignore") as fh:
            return fh.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def image_path(images_root, subj, study, dicom):
    return os.path.join(images_root, f"p{str(subj)[:2]}", f"p{subj}",
                        f"s{study}", f"{dicom}.jpg")


def first_existing_image(images_root, subj, study, dicoms):
    for d in dicoms:
        p = image_path(images_root, subj, study, d)
        if os.path.exists(p):
            return p
    return None


def detect_report_template(reports_root, samples):
    """Return the first report-path template that resolves for sampled studies."""
    for tmpl in REPORT_TEMPLATES:
        hits = 0
        for subj, study in samples:
            p = tmpl.format(root=reports_root, subj2=str(subj)[:2], subj=subj, study=study)
            if os.path.exists(p):
                hits += 1
        if hits > 0:
            return tmpl
    return None


def report_path(tmpl, reports_root, subj, study):
    return tmpl.format(root=reports_root, subj2=str(subj)[:2], subj=subj, study=study)


def autodetect_split(images_root, meta_path):
    parent = os.path.dirname(os.path.normpath(images_root))           # .../<ver>
    bases = [parent, os.path.dirname(os.path.abspath(meta_path))]
    for base in bases:
        for name in ("mimic-cxr-2.0.0-split.csv.gz", "mimic-cxr-2.0.0-split.csv"):
            cand = os.path.join(base, name)
            if os.path.exists(cand):
                return cand
        # also a loose glob in case of a different version string
        for g in glob.glob(os.path.join(base, "*split*.csv*")):
            return g
    return None


def build_tables(meta: pd.DataFrame):
    meta = meta.copy()
    meta["StudyTime"] = pd.to_numeric(meta["StudyTime"], errors="coerce").fillna(0)
    meta["StudyDate"] = pd.to_numeric(meta["StudyDate"], errors="coerce").fillna(0).astype("int64")

    frontal = meta[meta["ViewPosition"].isin(["PA", "AP"])].copy()
    frontal["vp_rank"] = (frontal["ViewPosition"] == "PA").astype(int)
    frontal = frontal.sort_values(["study_id", "vp_rank"], ascending=[True, False])
    study_frontals = frontal.groupby("study_id")["dicom_id"].apply(list).to_dict()

    studies = (meta.groupby("study_id")
               .agg(subject_id=("subject_id", "first"),
                    StudyDate=("StudyDate", "min"),
                    StudyTime=("StudyTime", "min"))
               .reset_index())
    # keep only studies that have a frontal image entry
    studies = studies[studies["study_id"].isin(study_frontals.keys())]
    return studies, study_frontals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default=DEF_META)
    ap.add_argument("--images-root", default=DEF_IMAGES)
    ap.add_argument("--reports-root", default=DEF_REPORTS)
    ap.add_argument("--split-csv", default=None, help="auto-detected if omitted")
    ap.add_argument("--n", type=int, default=0, help="cases to collect; 0 = ALL longitudinal test cases")
    ap.add_argument("--prior-mode", choices=["report_only", "image_and_report"],
                    default="report_only")
    ap.add_argument("--out", default="subset.jsonl")
    ap.add_argument("--max-scan", type=int, default=200000)
    ap.add_argument("--min-find-chars", type=int, default=20)
    ap.add_argument("--max-find-chars", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pairs-csv", default=None,
                    help="optional CSV with columns current_study_id,prior_study_id")
    args = ap.parse_args()

    for label, path in [("metadata", args.meta), ("images-root", args.images_root),
                        ("reports-root", args.reports_root)]:
        if not os.path.exists(path):
            sys.exit(f"[ERROR] {label} not found: {path}")

    print("Loading metadata ...")
    meta = pd.read_csv(args.meta)             # pandas infers .gz from extension
    print(f"  {len(meta):,} image rows")
    studies, study_frontals = build_tables(meta)
    study_meta = studies.set_index("study_id").to_dict("index")

    # ---- split (to restrict 'current' studies to the official test set) ----
    split_path = args.split_csv or autodetect_split(args.images_root, args.meta)
    if split_path and os.path.exists(split_path):
        sdf = pd.read_csv(split_path)
        study_split = sdf.groupby("study_id")["split"].first().to_dict()
        ntest = sum(1 for v in study_split.values() if v == "test")
        print(f"Split file: {split_path}  ({ntest:,} test studies)")
    else:
        study_split = {}
        print("Split file: NOT FOUND -> using ALL studies as candidates.\n"
              "  (MAIRA-2 was trained on MIMIC-CXR; the with/without-prior DELTA is\n"
              "   still valid, but absolute numbers may be optimistic. Pass --split-csv\n"
              "   if you can locate mimic-cxr-2.0.0-split.csv[.gz].)")

    # ---- detect report directory layout ----
    sample = [(int(r.subject_id), int(r.study_id))
              for r in studies.head(12).itertuples(index=False)]
    tmpl = detect_report_template(args.reports_root, sample)
    if tmpl is None:
        ex = REPORT_TEMPLATES[0].format(root=args.reports_root, subj2="10",
                                        subj="10000032", study="50414267")
        sys.exit(f"[ERROR] Could not find report .txt files under {args.reports_root}\n"
                 f"  Tried layouts like: {ex}\n"
                 f"  Check the folder structure and re-run with the correct --reports-root.")
    print(f"Report layout: {tmpl}")

    # ---- build (current, prior) candidate pairs ----
    if args.pairs_csv:
        pdf = pd.read_csv(args.pairs_csv)
        candidates = list(zip(pdf["current_study_id"].astype("int64"),
                              pdf["prior_study_id"].astype("int64")))
    else:
        ss = studies.sort_values(["subject_id", "StudyDate", "StudyTime", "study_id"])
        candidates = []
        prev_study, prev_subj = None, None
        for row in ss.itertuples(index=False):
            if row.subject_id == prev_subj and prev_study is not None:
                if (not study_split) or study_split.get(row.study_id) == "test":
                    candidates.append((int(row.study_id), int(prev_study)))
            prev_study, prev_subj = row.study_id, row.subject_id
        random.Random(args.seed).shuffle(candidates)

    print(f"{len(candidates):,} candidate pairs with a prior. "
          f"Scanning up to {args.max_scan} to collect {args.n} ...\n")

    kept, scanned = [], 0
    for cur_study, prior_study in candidates:
        if (args.n and len(kept) >= args.n) or scanned >= args.max_scan:
            break
        scanned += 1
        cm, pm = study_meta.get(cur_study), study_meta.get(prior_study)
        if cm is None or pm is None:
            continue
        subj = int(cm["subject_id"])

        cur_txt = read_text(report_path(tmpl, args.reports_root, subj, cur_study))
        if not cur_txt:
            continue
        findings = get_findings(cur_txt)
        if not (args.min_find_chars <= len(findings) <= args.max_find_chars):
            continue
        # NB: no longer filtered on comparative language — every longitudinal case
        # is kept and LABELLED change/no-change for stratified analysis.

        prior_txt = read_text(report_path(tmpl, args.reports_root, subj, prior_study))
        if not prior_txt:
            continue
        prior_findings = get_prior_report(prior_txt)
        if not prior_findings or len(prior_findings) < 10:
            continue

        cur_img = first_existing_image(args.images_root, subj, cur_study,
                                       study_frontals.get(cur_study, []))
        if not cur_img:
            continue

        prior_img = None
        if args.prior_mode == "image_and_report":
            prior_img = first_existing_image(args.images_root, subj, prior_study,
                                             study_frontals.get(prior_study, []))
            if prior_img is None:
                continue  # need the prior image for the prior to reach MAIRA-2

        kept.append({
            "subject_id": subj,
            "current_study_id": cur_study,
            "prior_study_id": prior_study,
            "current_image": cur_img,
            "prior_image": prior_img,
            "indication": get_field(cur_txt, "indication"),
            "comparison": get_field(cur_txt, "comparison"),
            "prior_findings": prior_findings,
            "reference_findings": findings,
            "change": bool(has_longitudinal(findings)),  # GT mentions interval change
        })
        if len(kept) % 50 == 0:
            nc = sum(k["change"] for k in kept)
            print(f"  kept {len(kept)}  (change {nc} / no-change {len(kept)-nc}; scanned {scanned})")

    with open(args.out, "w") as fh:
        for rec in kept:
            fh.write(json.dumps(rec) + "\n")

    nchg = sum(k["change"] for k in kept)
    print(f"\nDone. Wrote {len(kept)} cases to {args.out} (scanned {scanned}).")
    print(f"  strata -> change: {nchg}   no-change: {len(kept) - nchg}")
    if args.n and len(kept) < args.n:
        print("NOTE: collected fewer than requested -> raise --max-scan or lower --n.")


if __name__ == "__main__":
    main()
