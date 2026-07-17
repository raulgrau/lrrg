#!/usr/bin/env python3
"""
rewrite_manifest.py -- repoint a cgpool manifest at the Modal Volume mount.

The manifests (train_pairs_ulcx.jsonl / test_pairs_ulcx.jsonl) store ABSOLUTE
cgpool paths in current_image / prior_image, e.g.

  /graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/physionet.org/files/mimic-cxr-jpg/2.0.0/files/p10/...

data.py's LongitudinalPairDataset._abs() returns absolute paths untouched (it
only applies --image_root to RELATIVE paths), so on Modal those absolute paths
would dangle. We stage the images on a Volume preserving the physionet.org/...
subtree under the mount, then rewrite the manifest prefix to match.

    cgpool prefix : /graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/
    volume prefix : {--mount}/                (default /data/)

so a path becomes /data/physionet.org/files/mimic-cxr-jpg/2.0.0/files/p10/...

Run locally (no deps beyond stdlib):
    python rewrite_manifest.py --in ../train_pairs_ulcx.jsonl \
        --out train_pairs_modal.jsonl
"""

from __future__ import annotations

import argparse
import json

CGPOOL_PREFIX = "/graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/"
IMAGE_KEYS = ("current_image", "prior_image")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="source manifest (.jsonl)")
    ap.add_argument("--out", required=True, help="rewritten manifest (.jsonl)")
    ap.add_argument("--cgpool-prefix", default=CGPOOL_PREFIX,
                    help="absolute cgpool prefix to strip")
    ap.add_argument("--mount", default="/data",
                    help="Volume mount root the data is staged under")
    args = ap.parse_args()

    mount = args.mount.rstrip("/") + "/"
    n = rewritten = 0
    missing_prefix = 0
    with open(args.inp) as fin, open(args.out, "w") as fout:
        for line in fin:
            if not line.strip():
                continue
            r = json.loads(line)
            n += 1
            for k in IMAGE_KEYS:
                p = r.get(k)
                if not p:
                    continue
                if p.startswith(args.cgpool_prefix):
                    r[k] = mount + p[len(args.cgpool_prefix):]
                    rewritten += 1
                else:
                    missing_prefix += 1
            fout.write(json.dumps(r) + "\n")

    print(f"rewrote {rewritten} image paths across {n} records -> {args.out}")
    if missing_prefix:
        print(f"WARNING: {missing_prefix} image path(s) did not start with "
              f"{args.cgpool_prefix!r}; check --cgpool-prefix against your manifest.")


if __name__ == "__main__":
    main()
