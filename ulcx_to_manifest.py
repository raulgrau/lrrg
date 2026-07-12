#!/usr/bin/env python3
"""
ulcx_to_manifest.py — turn the ULCX / Zhu split files (train.json / val.json /
test.json from github.com/CelestialShine/Longitudinal-Chest-X-Ray) into a
manifest in the EXACT schema your curate_subset.py emits, so the result is
provably the ULCX cohort rather than a near-miss of your own heuristic.

How it stays faithful AND consistent with your pipeline:
  * ULCX's json is used ONLY to get the set of study_ids in the chosen split.
    (It is robust to however ULCX names its other fields — it just needs
     `study_id` on each record.)
  * Everything else — subject grouping, chronological ordering, consecutive
    (current, prior) pairing, frontal selection, Findings/Indication/Comparison
    extraction, on-disk image paths — is reconstructed by importing and calling
    your OWN curate_subset.py + utils_reports helpers against your local MIMIC
    copy. So image paths, section extraction, and the output schema are
    identical to what curate_subset.py already produces.

Pairing matches ULCX: studies are ordered by (StudyDate, StudyTime) and EVERY
consecutive pair within a subject is emitted (a patient with v1<v2<v3 yields
(v2,v1) and (v3,v2)), which is why ULCX has many samples per patient.

Run on the cluster (defaults assume your cgpool layout via curate_subset):
    python ulcx_to_manifest.py \
        --ulcx-json /path/to/Longitudinal-Chest-X-Ray/test.json --split test \
        --prior-mode image_and_report --out test_pairs_ulcx.jsonl

    python ulcx_to_manifest.py \
        --ulcx-json /path/to/Longitudinal-Chest-X-Ray/train.json --split train \
        --prior-mode image_and_report --out train_pairs_ulcx.jsonl

If curate_subset.py / utils_reports.py are not importable, pass
--ablation-dir /home/grauperez/lrrg/lrrg_ablation (default) so they're found.
"""

import argparse
import json
import os
import sys
import re
from collections import defaultdict


# --------------------------------------------------------------------------- #
#  Pure helpers (unit-tested below; no MIMIC / curate_subset needed)
# --------------------------------------------------------------------------- #
_SID_RE = re.compile(r'(?:^|/)s(\d+)/')          # .../s50414267/<dicom>.jpg
_SID_RE_LOOSE = re.compile(r'\bs(\d{6,})\b')     # fallback: s + >=6 digits

def _sid_from_path(p: str):
    m = _SID_RE.search(p) or _SID_RE_LOOSE.search(p)
    return int(m.group(1)) if m else None

def _study_ids_from_record(r):
    """Pull study_id(s) from a record of any shape ULCX might use."""
    ids = set()
    if isinstance(r, dict):
        for k in ("study_id", "studyid", "study"):       # explicit field
            if r.get(k) is not None:
                try:
                    ids.add(int(r[k])); 
                except (ValueError, TypeError):
                    pass
        if ids:
            return ids
        if str(r.get("id", "")).isdigit():               # 'id' that is numeric
            ids.add(int(r["id"]))
        for k in ("image_path", "image_paths", "img_path", "path", "image"):
            v = r.get(k)
            for s in ([v] if isinstance(v, str) else (v or [])):
                if isinstance(s, str) and (sid := _sid_from_path(s)) is not None:
                    ids.add(sid)
        return ids
    if isinstance(r, str):                                # bare path string
        sid = _sid_from_path(r)
        return {sid} if sid is not None else set()
    if isinstance(r, list):                               # nested list of paths
        for x in r:
            ids |= _study_ids_from_record(x)
    return ids

def load_ulcx_study_ids(path: str, split: str):
    """Return the sorted unique set of study_ids for `split` from a ULCX json.

    Robust to: {"train":[...],"test":[...]}, {"test":[...]}, or a flat list;
    and to records that are full dicts, image-path dicts, or bare path strings.
    """
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, dict) and split in data and isinstance(data[split], list):
        records = data[split]
    elif isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = [x for v in data.values() if isinstance(v, list) for x in v]
        if not records:
            raise ValueError(f"{path}: no record list found (keys={list(data.keys())})")
    else:
        raise ValueError(f"{path}: unexpected top-level type {type(data)}")

    ids = set()
    for r in records:
        ids |= _study_ids_from_record(r)
    if not ids:
        raise ValueError(f"{path}: could not extract any study_id "
                         f"(checked study_id field and s<digits> in paths)")
    return sorted(ids)


def build_consecutive_pairs(study_ids, study_meta):
    """Group study_ids by subject, order chronologically, emit ALL consecutive
    (current, prior) pairs. `study_meta[sid]` must hold subject_id / StudyDate /
    StudyTime. Studies absent from study_meta are skipped (counted).

    Pairing is done WITHIN the provided study set, which faithfully reproduces
    ULCX: filtering happens first (the set), then consecutive pairing.
    """
    by_subject = defaultdict(list)
    skipped_no_meta = 0
    for sid in study_ids:
        m = study_meta.get(sid)
        if m is None:
            skipped_no_meta += 1
            continue
        by_subject[int(m["subject_id"])].append(sid)

    pairs = []
    for subj, sids in by_subject.items():
        sids_sorted = sorted(
            sids,
            key=lambda s: (study_meta[s]["StudyDate"], study_meta[s]["StudyTime"], s))
        for i in range(1, len(sids_sorted)):
            pairs.append((sids_sorted[i], sids_sorted[i - 1]))  # (current, prior)
    return pairs, skipped_no_meta


# --------------------------------------------------------------------------- #
#  Main: reuse curate_subset.py machinery for everything data-dependent
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ulcx-json", required=True,
                    help="ULCX repo train.json / val.json / test.json")
    ap.add_argument("--split", default="test", choices=["train", "val", "test"],
                    help="which split inside the json (and which to label pairs as)")
    ap.add_argument("--ablation-dir", default="/home/grauperez/lrrg/lrrg_ablation",
                    help="dir containing curate_subset.py + utils_reports.py")
    # data locations: default to curate_subset's own cgpool defaults (filled after import)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--images-root", default=None)
    ap.add_argument("--reports-root", default=None)
    ap.add_argument("--split-csv", default=None,
                    help="optional mimic-cxr-2.0.0-split.csv[.gz] for a leakage cross-check")
    ap.add_argument("--prior-mode", choices=["report_only", "image_and_report"],
                    default="image_and_report")
    ap.add_argument("--out", default="pairs_ulcx.jsonl")
    ap.add_argument("--min-find-chars", type=int, default=20)
    ap.add_argument("--max-find-chars", type=int, default=1200)
    ap.add_argument("--n", type=int, default=0, help="cap kept pairs (0 = all)")
    args = ap.parse_args()

    # make curate_subset importable, then pull in its helpers + defaults
    sys.path.insert(0, os.path.expanduser(args.ablation_dir))
    try:
        import curate_subset as cs
        from utils_reports import get_findings, get_prior_report, get_field
    except Exception as e:
        sys.exit(f"[ERROR] could not import curate_subset/utils_reports from "
                 f"{args.ablation_dir}: {e}\n  Pass --ablation-dir <dir with those files>.")

    import pandas as pd

    meta_path = args.meta or cs.DEF_META
    images_root = args.images_root or cs.DEF_IMAGES
    reports_root = args.reports_root or cs.DEF_REPORTS
    for label, path in [("metadata", meta_path), ("images-root", images_root),
                        ("reports-root", reports_root), ("ulcx-json", args.ulcx_json)]:
        if not os.path.exists(path):
            sys.exit(f"[ERROR] {label} not found: {path}")

    # ---- ULCX cohort (study_ids only) ----
    ulcx_ids = load_ulcx_study_ids(args.ulcx_json, args.split)
    print(f"ULCX {args.split}: {len(ulcx_ids):,} unique study_ids")

    # ---- local metadata -> frontals + per-study StudyDate/Time/subject ----
    print("Loading metadata ...")
    meta = pd.read_csv(meta_path)
    studies, study_frontals = cs.build_tables(meta)
    study_meta = studies.set_index("study_id").to_dict("index")

    # ---- optional leakage cross-check against the official split ----
    if args.split_csv and os.path.exists(args.split_csv):
        sdf = pd.read_csv(args.split_csv)
        official = sdf.groupby("study_id")["split"].first().to_dict()
        want = {"train": "train", "val": "validate", "test": "test"}[args.split]
        bad = [s for s in ulcx_ids if official.get(s) not in (want, None)]
        if bad:
            print(f"  [WARN] {len(bad)} ULCX '{args.split}' studies are NOT '{want}' "
                  f"in the official split (e.g. {bad[:3]}). Investigate before trusting.")
        else:
            print(f"  [ok] all ULCX '{args.split}' studies match official split='{want}'")

    # ---- pair within the ULCX set, chronologically ----
    pairs, skipped = build_consecutive_pairs(ulcx_ids, study_meta)
    print(f"{len(pairs):,} consecutive (current, prior) pairs "
          f"({skipped:,} studies skipped: absent from metadata or no frontal entry)\n")

    # ---- detect report layout (reuse curate_subset) ----
    sample = [(int(r.subject_id), int(r.study_id))
              for r in studies.head(12).itertuples(index=False)]
    tmpl = cs.detect_report_template(reports_root, sample)
    if tmpl is None:
        sys.exit(f"[ERROR] could not locate report .txt files under {reports_root}")
    print(f"Report layout: {tmpl}\n")

    # ---- build records (same extraction + filters + schema as curate_subset) ----
    kept, scanned = [], 0
    dropped = defaultdict(int)
    for cur_study, prior_study in pairs:
        if args.n and len(kept) >= args.n:
            break
        scanned += 1
        cm, pm = study_meta.get(cur_study), study_meta.get(prior_study)
        if cm is None or pm is None:
            dropped["no_meta"] += 1
            continue
        subj = int(cm["subject_id"])

        cur_txt = cs.read_text(cs.report_path(tmpl, reports_root, subj, cur_study))
        if not cur_txt:
            dropped["no_cur_report"] += 1
            continue
        findings = get_findings(cur_txt)
        if not (args.min_find_chars <= len(findings) <= args.max_find_chars):
            dropped["findings_len"] += 1
            continue

        prior_txt = cs.read_text(cs.report_path(tmpl, reports_root, subj, prior_study))
        if not prior_txt:
            dropped["no_prior_report"] += 1
            continue
        prior_findings = get_prior_report(prior_txt)
        if not prior_findings or len(prior_findings) < 10:
            dropped["no_prior_findings"] += 1
            continue

        cur_img = cs.first_existing_image(images_root, subj, cur_study,
                                          study_frontals.get(cur_study, []))
        if not cur_img:
            dropped["no_cur_image"] += 1
            continue

        prior_img = None
        if args.prior_mode == "image_and_report":
            prior_img = cs.first_existing_image(images_root, subj, prior_study,
                                                study_frontals.get(prior_study, []))
            if prior_img is None:
                dropped["no_prior_image"] += 1
                continue

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
            "change": bool(cs.has_longitudinal(findings)),
        })

    with open(args.out, "w") as fh:
        for rec in kept:
            fh.write(json.dumps(rec) + "\n")

    nchg = sum(k["change"] for k in kept)
    print(f"Done. Wrote {len(kept):,} pairs to {args.out} (scanned {scanned:,}).")
    print(f"  strata -> change: {nchg:,}   no-change: {len(kept) - nchg:,}")
    if dropped:
        print("  dropped:", dict(dropped))
    expect = {"train": 92374, "val": 737, "test": 2058}[args.split]
    print(f"  ULCX reference {args.split} sample count ≈ {expect:,} "
          f"(yours differs by filtering + one-frontal-per-study; see README note).")
    print("  NOTE: 'change' here is curate_subset's keyword label (noisy). For the "
          "stratified eval, relabel via L-MIMIC / CheXbert-delta.")


# --------------------------------------------------------------------------- #
#  CPU self-tests for the pure helpers (no MIMIC, no curate_subset)
# --------------------------------------------------------------------------- #
if __name__ == "__main__" and "--ulcx-json" not in sys.argv and "--help" not in sys.argv \
        and "-h" not in sys.argv:
    import tempfile

    # --- load_ulcx_study_ids: all three shapes ---
    with tempfile.TemporaryDirectory() as d:
        p1 = os.path.join(d, "combined.json")
        json.dump({"train": [{"study_id": 1}, {"study_id": 2}],
                   "test": [{"study_id": 9}, {"study_id": 9}, {"study_id": 7}]}, open(p1, "w"))
        assert load_ulcx_study_ids(p1, "test") == [7, 9], "dedup+sort combined"
        assert load_ulcx_study_ids(p1, "train") == [1, 2]

        p2 = os.path.join(d, "single.json")
        json.dump({"test": [{"study_id": 5, "subject_id": 100}, {"study_id": 3}]}, open(p2, "w"))
        assert load_ulcx_study_ids(p2, "test") == [3, 5], "single-split dict"

        p3 = os.path.join(d, "flat.json")
        json.dump([{"study_id": 11, "report": "x"}, {"study_id": 4}], open(p3, "w"))
        assert load_ulcx_study_ids(p3, "test") == [4, 11], "flat list"
    print("[ok] load_ulcx_study_ids handles combined / single-split / flat shapes")

    # --- build_consecutive_pairs: chronological order + all consecutive pairs ---
    # subject 100: studies 5(date2),3(date1),8(date3)  -> ordered 3,5,8 -> (5,3),(8,5)
    # subject 200: single study 9                       -> no pair
    # study 77: absent from meta                        -> skipped
    study_meta = {
        3: {"subject_id": 100, "StudyDate": 20180101, "StudyTime": 100.0},
        5: {"subject_id": 100, "StudyDate": 20180202, "StudyTime": 100.0},
        8: {"subject_id": 100, "StudyDate": 20180303, "StudyTime": 100.0},
        9: {"subject_id": 200, "StudyDate": 20190101, "StudyTime": 100.0},
    }
    pairs, skipped = build_consecutive_pairs([5, 3, 8, 9, 77], study_meta)
    assert skipped == 1, f"one study absent from meta, got {skipped}"
    assert (5, 3) in pairs and (8, 5) in pairs, f"consecutive pairs wrong: {pairs}"
    assert (8, 3) not in pairs, "must pair consecutively, not skip-prior"
    assert len([p for p in pairs if p[0] == 9 or p[1] == 9]) == 0, "singleton subject -> no pair"
    assert len(pairs) == 2, f"expected 2 pairs, got {len(pairs)}: {pairs}"

    # tie-break: same date+time -> order by study_id
    sm2 = {1: {"subject_id": 1, "StudyDate": 1, "StudyTime": 0.0},
           2: {"subject_id": 1, "StudyDate": 1, "StudyTime": 0.0}}
    p2, _ = build_consecutive_pairs([2, 1], sm2)
    assert p2 == [(2, 1)], f"tie-break by study_id failed: {p2}"
    print("[ok] build_consecutive_pairs: chronological, all-consecutive, tie-break, singleton-safe")
    print("all ulcx_to_manifest pure-function tests passed")
else:
    if __name__ == "__main__":
        main()
