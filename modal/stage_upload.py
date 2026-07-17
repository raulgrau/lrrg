#!/usr/bin/env python3
"""
stage_upload.py -- push the referenced MIMIC-CXR-JPG subset from cgpool straight
into a Modal Volume, using the Modal SDK's batch_upload (no PhysioNet creds, no
tar, no extra disk on scratch).

Run this ON CGPOOL, in modal_venv (where `modal` is installed and authed), from
the copy of the data you already have read access to:

    source ~/modal_venv/bin/activate
    python stage_upload.py \
        --relpaths ../mimic_subset_relpaths.txt \
        --src-root /graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/physionet.org \
        --volume mimic-cxr-jpg

Resumable: a local progress file (--progress) records which chunks are committed,
so a re-run skips them. Bounded only by the cluster's outbound bandwidth.

Path mapping
------------
relpath (in the list)   : files/mimic-cxr-jpg/2.0.0/files/p10/.../x.jpg
local source            : {src-root}/files/mimic-cxr-jpg/.../x.jpg
volume remote path      : /physionet.org/files/mimic-cxr-jpg/.../x.jpg
   -> mounted at /data on the training container this is
      /data/physionet.org/...  which is exactly what rewrite() produces.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relpaths", required=True,
                    help="mimic_subset_relpaths.txt (paths relative to physionet.org/)")
    ap.add_argument("--src-root", required=True,
                    help="cgpool dir that CONTAINS the physionet.org/ subtree's files, "
                         "i.e. .../MIMIC-CXR-JPG/physionet.org")
    ap.add_argument("--volume", default="mimic-cxr-jpg")
    ap.add_argument("--remote-prefix", default="/physionet.org",
                    help="path prefix inside the Volume (matches rewrite/-> /data mount)")
    ap.add_argument("--chunk", type=int, default=2000,
                    help="files per batch_upload commit (resume granularity)")
    ap.add_argument("--progress", default="stage_progress.txt",
                    help="local file recording completed chunk indices")
    args = ap.parse_args()

    import modal

    rels = [ln.strip() for ln in open(args.relpaths) if ln.strip()]
    total = len(rels)
    print(f"[stage] {total} files to upload, chunk={args.chunk}")

    # verify a couple of sources exist up front (fail fast on a wrong --src-root)
    for probe in rels[:3]:
        p = os.path.join(args.src_root, probe)
        if not os.path.exists(p):
            sys.exit(f"[stage] source not found: {p}\n"
                     f"  check --src-root (should contain the 'files/...' subtree)")

    done_chunks = set()
    if os.path.exists(args.progress):
        done_chunks = {int(x) for x in open(args.progress).read().split() if x.strip()}
        print(f"[stage] resuming: {len(done_chunks)} chunks already committed")

    vol = modal.Volume.from_name(args.volume, create_if_missing=True)

    n_chunks = (total + args.chunk - 1) // args.chunk
    uploaded = 0
    t0 = time.time()
    for ci in range(n_chunks):
        if ci in done_chunks:
            continue
        lo, hi = ci * args.chunk, min((ci + 1) * args.chunk, total)
        batch_rels = rels[lo:hi]
        missing = 0
        with vol.batch_upload(force=True) as batch:
            for rel in batch_rels:
                local = os.path.join(args.src_root, rel)
                if not os.path.exists(local):
                    missing += 1
                    continue
                remote = args.remote_prefix.rstrip("/") + "/" + rel
                batch.put_file(local, remote)
        # record this chunk as committed
        with open(args.progress, "a") as pf:
            pf.write(f"{ci}\n")
        uploaded += (hi - lo) - missing
        elapsed = time.time() - t0
        rate = uploaded / elapsed if elapsed else 0
        eta = (total - hi) / rate if rate else float("nan")
        print(f"[stage] chunk {ci+1}/{n_chunks}  files {hi}/{total}  "
              f"missing_in_chunk={missing}  {rate:.0f} files/s  ETA {eta/60:.0f}m",
              flush=True)

    print(f"[stage] done: uploaded ~{uploaded} files in {(time.time()-t0)/60:.1f}m")
    print("[stage] the Volume is now ready; run training with modal_app.py::run_training")


if __name__ == "__main__":
    main()
