#!/usr/bin/env python3
"""
make_battery_manifests.py -- build the 8-arm counterfactual-prior battery from the
test manifest, for auditing whether base MAIRA-2 actually *uses* the prior study.

Each arm is just the test manifest with the prior fields (prior_image /
prior_findings) substituted a particular way, so baseline_infer.py runs UNCHANGED
on each arm manifest -- no model-side code changes, and every substituted image is
guaranteed already staged on the Modal Volume because substitute priors are drawn
ONLY from the test set's own prior pool.

Arms (Zhou-style battery):
    A0 no_prior          : prior image + report removed              (no-prior floor)
    A1 full              : correct image + correct report            (longitudinal ceiling)
    A2 image_only        : correct image + BLANK report              (does the image carry it?)
    A3 wrong_patient     : another patient's prior (image+report),   KEY CONTROL
                           MATCHED on view position + time-gap bin   (identity is the only change)
    A4 img_ok_rep_wrong  : correct image + wrong-patient report      (which modality dominates?)
    A5 img_wrong_rep_ok  : wrong-patient image + correct report      (reversed)
    A6 dup_current       : current image duplicated as prior + report(induces a 'no change' prior)
    A7 temporal_swap     : current<->prior images AND reports swapped (is direction-of-change modelled?)

A3/A4/A5 matching: for each case we find a donor prior from a DIFFERENT subject whose
prior shares the current case's (view position, time-gap bin). Falls back to same-view/
any-bin, then any different-subject prior, logging how many needed each fallback.

Run ON CGPOOL (needs the metadata CSV):
    python make_battery_manifests.py \
        --manifest ../test_pairs_ulcx.jsonl \
        --meta /graphics/scratch2/students/mpindabe/Datasets/mimic-cxr-reports/mimic-cxr-2.0.0-metadata.csv \
        --out-dir battery_manifests
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
from collections import defaultdict

GAP_BINS = [(0, 7), (7, 30), (30, 180), (180, 10**9)]   # days: <7, 7-30, 30-180, >180


def gap_bin(days):
    if days is None:
        return "unknown"
    for lo, hi in GAP_BINS:
        if lo <= days < hi:
            return f"{lo}-{hi}"
    return "unknown"


def parse_ids_from_path(p):
    """Extract (study_id, dicom_id) from a MIMIC-CXR-JPG path .../sSTUDY/DICOM.jpg."""
    if not p:
        return None, None
    m_study = re.search(r"/s(\d+)/", p)
    dicom = os.path.splitext(os.path.basename(p))[0] or None
    study = m_study.group(1) if m_study else None
    return study, dicom


def load_metadata(meta_path):
    """study_id -> StudyDate(int YYYYMMDD);  dicom_id -> ViewPosition."""
    study_date, dicom_view = {}, {}
    with open(meta_path, newline="") as f:
        for row in csv.DictReader(f):
            sid = str(row.get("study_id", "")).strip()
            did = str(row.get("dicom_id", "")).strip()
            sd = str(row.get("StudyDate", "")).strip()
            vp = (row.get("ViewPosition") or "").strip().upper() or "UNK"
            if sid and sd.isdigit():
                study_date[sid] = int(sd)
            if did:
                dicom_view[did] = vp
    return study_date, dicom_view


def days_between(cur_yyyymmdd, prior_yyyymmdd):
    import datetime
    def d(x):
        s = str(x)
        return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    try:
        return (d(cur_yyyymmdd) - d(prior_yyyymmdd)).days
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--meta", required=True, help="mimic-cxr-2.0.0-metadata.csv")
    ap.add_argument("--out-dir", default="battery_manifests")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    rng = random.Random(args.seed)

    recs = [json.loads(l) for l in open(args.manifest) if l.strip()]
    n = len(recs)
    print(f"[battery] {n} test cases")

    study_date, dicom_view = load_metadata(args.meta)
    print(f"[battery] metadata: {len(study_date)} study dates, {len(dicom_view)} dicom views")

    # annotate each case with prior view + time-gap bin
    for r in recs:
        cur_study, _ = parse_ids_from_path(r.get("current_image"))
        pri_study, pri_dicom = parse_ids_from_path(r.get("prior_image"))
        view = dicom_view.get(pri_dicom or "", "UNK")
        gap = None
        if cur_study in study_date and pri_study in study_date:
            gap = days_between(study_date[cur_study], study_date[pri_study])
        r["_view"] = view
        r["_bin"] = gap_bin(gap)
        r["_subj"] = str(r.get("subject_id"))
        r["_prior"] = {"prior_image": r.get("prior_image"), "prior_findings": r.get("prior_findings")}

    # donor pools keyed by (view, bin) and (view) for fallback
    pool_vb, pool_v, pool_all = defaultdict(list), defaultdict(list), []
    for i, r in enumerate(recs):
        pool_vb[(r["_view"], r["_bin"])].append(i)
        pool_v[r["_view"]].append(i)
        pool_all.append(i)

    fb = {"vb": 0, "v": 0, "any": 0}

    def pick_donor(i):
        """A different-subject donor index, matched view+bin, with graded fallback."""
        r = recs[i]
        for key, pool, tag in ((( r["_view"], r["_bin"]), pool_vb, "vb"),
                               (r["_view"], pool_v, "v"),
                               (None, pool_all, "any")):
            cands = pool[key] if key is not None else pool
            cands = [j for j in cands if recs[j]["_subj"] != r["_subj"]]
            if cands:
                fb[tag] += 1
                return rng.choice(cands)
        return i  # degenerate (should never happen with 1,786 cases)

    donor = [pick_donor(i) for i in range(n)]

    def base(r):
        """A clean copy of a record without the internal _ fields."""
        return {k: v for k, v in r.items() if not k.startswith("_")}

    arms = {}   # name -> list of records
    arms["A0_no_prior"] = []
    arms["A1_full"] = []
    arms["A2_image_only"] = []
    arms["A3_wrong_patient"] = []
    arms["A4_img_ok_rep_wrong"] = []
    arms["A5_img_wrong_rep_ok"] = []
    arms["A6_dup_current"] = []
    arms["A7_temporal_swap"] = []

    for i, r in enumerate(recs):
        d = recs[donor[i]]
        dpi, dpr = d["_prior"]["prior_image"], d["_prior"]["prior_findings"]

        a0 = base(r); a0["prior_image"] = None; a0["prior_findings"] = None
        arms["A0_no_prior"].append(a0)

        arms["A1_full"].append(base(r))

        a2 = base(r); a2["prior_findings"] = ""            # blank report, image kept
        arms["A2_image_only"].append(a2)

        a3 = base(r); a3["prior_image"] = dpi; a3["prior_findings"] = dpr
        arms["A3_wrong_patient"].append(a3)

        a4 = base(r); a4["prior_findings"] = dpr           # correct image, wrong report
        arms["A4_img_ok_rep_wrong"].append(a4)

        a5 = base(r); a5["prior_image"] = dpi              # wrong image, correct report
        arms["A5_img_wrong_rep_ok"].append(a5)

        a6 = base(r); a6["prior_image"] = r.get("current_image")   # duplicate current
        arms["A6_dup_current"].append(a6)

        # A7 (EXPLORATORY): reverse the timeline. The model now describes the
        # prior image conditioned on the current as its "prior", so we score
        # against the PRIOR study's report, not the current's. Interpret with
        # care -- this arm probes direction-sensitivity, not accuracy per se.
        a7 = base(r)
        a7["current_image"], a7["prior_image"] = r.get("prior_image"), r.get("current_image")
        a7["prior_findings"] = r.get("reference_findings")  # condition on the (future) current report
        a7["reference_findings"] = r.get("prior_findings")  # score against the prior study's report
        arms["A7_temporal_swap"].append(a7)

    for name, rows in arms.items():
        path = os.path.join(args.out_dir, f"{name}.jsonl")
        with open(path, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        print(f"  wrote {name:22s} {len(rows)} cases -> {path}")

    # coverage report for A3 matching (goes in the methods section)
    matched = fb["vb"]
    print(f"\n[battery] A3 donor matching over {n} cases:")
    print(f"    exact (view + time-gap bin) : {fb['vb']}  ({100*fb['vb']/n:.1f}%)")
    print(f"    fallback (view only)        : {fb['v']}")
    print(f"    fallback (any diff-subject) : {fb['any']}")
    print(f"[battery] report this coverage; exact-match rate should be high enough "
          f"that identity is the dominant varied factor.")
    # view/bin distribution for the write-up
    from collections import Counter
    print("\n[battery] prior view distribution:", dict(Counter(r["_view"] for r in recs)))
    print("[battery] time-gap bin distribution:", dict(Counter(r["_bin"] for r in recs)))


if __name__ == "__main__":
    main()
