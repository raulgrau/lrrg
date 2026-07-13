"""
Retriever: given a query change signature (and optionally a query image-diff
embedding), return the top-k exemplar sentences from the corpus built by
build_retrieval_corpus.py.

Scoring: signature similarity always contributes; image-diff similarity is
blended in only if config.RETRIEVAL.use_image_diff is set and a FAISS index
is available. Retrieval operates at the (unique) source-report level for
scoring -- all comparison sentences from the same report share one change
signature -- then expands back out to individual sentence rows for the
final top-k so a single high-scoring report doesn't monopolize all k slots
in a way that isn't visible to the caller (see `max_per_report`).
"""
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from chexbert_utils import signature_similarity
from config import PATHS, RETRIEVAL


class RetrievedExemplar:
    def __init__(self, sentence: str, study_id, score: float):
        self.sentence = sentence
        self.study_id = study_id
        self.score = score

    def __repr__(self):
        return f"RetrievedExemplar(study_id={self.study_id!r}, score={self.score:.3f}, sentence={self.sentence!r})"


class Retriever:
    def __init__(
        self,
        corpus_file: Path = PATHS.corpus_file,
        use_image_diff: bool = RETRIEVAL.use_image_diff,
        image_index_file: Path = PATHS.image_diff_index_file,
        image_ids_file: Path = PATHS.image_diff_ids_file,
    ):
        self.corpus_df = pd.read_parquet(corpus_file)
        self.corpus_df["change_signature"] = self.corpus_df["change_signature"].apply(np.array)

        # One signature per unique study_id (they're all identical within a
        # study, since they're derived at the report level).
        self._study_signatures = (
            self.corpus_df.drop_duplicates("study_id").set_index("study_id")["change_signature"].to_dict()
        )

        self.use_image_diff = use_image_diff
        self.image_index = None
        if use_image_diff:
            from image_diff_utils import ImageDiffIndex

            self.image_index = ImageDiffIndex(image_index_file, image_ids_file)

    def retrieve(
        self,
        query_signature: np.ndarray,
        query_diff_embedding: Optional[np.ndarray] = None,
        k: int = RETRIEVAL.k,
        max_per_report: int = 2,
        alpha: float = RETRIEVAL.alpha,
        signature_metric: str = RETRIEVAL.signature_metric,
    ) -> List[RetrievedExemplar]:
        # 1. Signature similarity per unique study.
        study_ids = list(self._study_signatures.keys())
        sig_scores = {
            sid: signature_similarity(query_signature, sig, metric=signature_metric)
            for sid, sig in self._study_signatures.items()
        }

        # 2. Optional image-diff similarity, only for studies the FAISS
        # search actually returns; studies outside that pool get 0.
        img_scores = {}
        if self.use_image_diff and self.image_index is not None and query_diff_embedding is not None:
            from image_diff_utils import l2_to_similarity

            pool_size = min(len(study_ids), max(50, k * 10))
            result_ids, distances = self.image_index.search(query_diff_embedding, top_k=pool_size)
            sims = l2_to_similarity(distances)
            for sid, sim in zip(result_ids, sims):
                img_scores[sid] = float(sim)

        # 3. Combined score per study.
        combined = {}
        for sid in study_ids:
            sig_s = sig_scores.get(sid, 0.0)
            img_s = img_scores.get(sid, 0.0) if self.use_image_diff else 0.0
            combined[sid] = alpha * sig_s + (1 - alpha) * img_s if self.use_image_diff else sig_s

        ranked_study_ids = sorted(combined.keys(), key=lambda s: combined[s], reverse=True)

        # 4. Expand to sentence rows, capping per-report contribution.
        exemplars: List[RetrievedExemplar] = []
        for sid in ranked_study_ids:
            if len(exemplars) >= k:
                break
            rows = self.corpus_df[self.corpus_df["study_id"] == sid].head(max_per_report)
            for _, row in rows.iterrows():
                if len(exemplars) >= k:
                    break
                exemplars.append(RetrievedExemplar(row["sentence"], sid, combined[sid]))

        return exemplars
