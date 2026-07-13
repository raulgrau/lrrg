#!/usr/bin/env python
"""
Build the ICL retrieval corpus from ULCX train (+ val, once it exists)
reports -- never test (test_pairs_ulcx.jsonl), that would be leakage.

For each case with both a prior and current Findings text:
  1. Extract comparison sentences from the *current* report (ground truth,
     since this is train/val) via temporal_utils.
  2. CheXbert-label both the prior and current report text (signed 4-class,
     for the change signature).
  3. Compute the 14-dim change signature between them.
  4. (optional) embed the prior/current image pair with RAD-DINO for the
     image-diff FAISS index.

Output: a parquet file with one row per (comparison sentence, source report),
carrying the report-level change signature, plus an optional FAISS index
over image-diff embeddings.

Usage:
    export XDG_CACHE_HOME=/var/tmp/xdg_cache_grauperez   # reuse cached CheXbert checkpoint
    unset LD_LIBRARY_PATH                                 # cuDNN hygiene (project memory)
    python build_retrieval_corpus.py --splits train
    # add "val" once val_pairs_ulcx.jsonl has been built via:
    #   python ulcx_to_manifest.py --ulcx-json ulcx/val.json --split val \
    #       --prior-mode image_and_report --out val_pairs_ulcx.jsonl
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from chexbert_utils import CheXbertLabeler, change_signature
from config import PATHS, RETRIEVAL
from temporal_utils import extract_comparison_sentences


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
    parser.add_argument(
        "--splits", nargs="+", default=["train"], choices=["train", "val"],
        help="'val' requires val_pairs_ulcx.jsonl to exist first (see module docstring)",
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--build-image-diff-index", action="store_true", default=RETRIEVAL.use_image_diff)
    args = parser.parse_args()

    split_paths = {"train": PATHS.train_manifest, "val": PATHS.val_manifest}
    records = []
    for split in args.splits:
        path = split_paths[split]
        if not path.exists():
            print(f"skipping {split}: {path} does not exist")
            continue
        recs = load_manifest(path)
        print(f"loaded {len(recs)} records from {split} manifest ({path})")
        records.extend(recs)

    # Keep only cases with both prior and current Findings text -- required to
    # compute a change signature at all.
    usable = [r for r in records if r.get("reference_findings") and r.get("prior_findings")]
    print(f"{len(usable)}/{len(records)} records have both prior + current Findings text")

    print("loading CheXbert (f1chexbert)...")
    labeler = CheXbertLabeler(device=args.device)

    print("labeling current + prior reports (signed 4-class, for change signature)...")
    current_signed = [labeler.label_signed(r["reference_findings"]) for r in tqdm(usable, desc="current")]
    prior_signed = [labeler.label_signed(r["prior_findings"]) for r in tqdm(usable, desc="prior")]

    rows = []
    diff_embed_rows = []  # (row_index_in_usable, record) pairs needing image embeddings
    for i, rec in enumerate(tqdm(usable, desc="extracting comparison sentences")):
        sig = change_signature(prior_signed[i], current_signed[i])
        sentences = extract_comparison_sentences(rec["reference_findings"])
        for sentence in sentences:
            rows.append(
                {
                    "corpus_id": len(rows),
                    "study_id": rec.get("current_study_id"),
                    "subject_id": rec.get("subject_id"),
                    "sentence": sentence,
                    "change_signature": sig.tolist(),
                }
            )
        if sentences and args.build_image_diff_index:
            diff_embed_rows.append((i, rec))

    corpus_df = pd.DataFrame(rows)
    PATHS.corpus_dir.mkdir(parents=True, exist_ok=True)
    corpus_df.to_parquet(PATHS.corpus_file, index=False)
    print(f"wrote {len(corpus_df)} corpus rows -> {PATHS.corpus_file}")

    if args.build_image_diff_index:
        print("embedding image pairs for image-diff FAISS index...")
        from image_diff_utils import RadDinoEmbedder, build_faiss_index

        embedder = RadDinoEmbedder(PATHS.raddino_model_id, device=args.device)
        # One diff embedding per source *report* (not per sentence).
        prior_paths = [usable[i]["prior_image"] for i, _ in diff_embed_rows]
        current_paths = [usable[i]["current_image"] for i, _ in diff_embed_rows]
        diffs = embedder.embed_diff(prior_paths, current_paths)
        # Store study_id (not the transient list index) so retrieve.py can
        # join FAISS search results back onto corpus_df by study_id.
        record_study_ids = np.array([usable[i]["current_study_id"] for i, _ in diff_embed_rows], dtype=object)
        build_faiss_index(diffs, PATHS.image_diff_index_file, PATHS.image_diff_ids_file, record_study_ids)
        print(f"wrote FAISS index -> {PATHS.image_diff_index_file}")

    print("done.")


if __name__ == "__main__":
    main()
