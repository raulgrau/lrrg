"""
Optional image-diff retrieval: embed prior/current frontal image pairs with
RAD-DINO, take the difference vector, and index it in FAISS for
visual-similarity retrieval. Feature-flagged via config.RETRIEVAL.use_image_diff
-- the pipeline runs fine without this, using CheXbert change-signature
retrieval alone.
"""
from pathlib import Path
from typing import List, Sequence

import numpy as np
import torch
from PIL import Image


class RadDinoEmbedder:
    def __init__(self, model_id: str, device: str = "cuda"):
        from transformers import AutoImageProcessor, AutoModel

        self.device = device
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).to(device).eval()

    @torch.no_grad()
    def embed(self, image_paths: Sequence[str], batch_size: int = 8) -> np.ndarray:
        """Returns (N, D) pooled CLS embeddings."""
        all_embeds = []
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i : i + batch_size]
            images = [Image.open(p).convert("RGB") for p in batch_paths]
            inputs = self.processor(images=images, return_tensors="pt").to(self.device)
            out = self.model(**inputs)
            cls_embed = out.last_hidden_state[:, 0, :]  # (batch, D)
            all_embeds.append(cls_embed.cpu().numpy())
        return np.concatenate(all_embeds, axis=0)

    def embed_diff(self, prior_paths: Sequence[str], current_paths: Sequence[str]) -> np.ndarray:
        """(N, D) difference embeddings: current - prior."""
        prior_emb = self.embed(prior_paths)
        current_emb = self.embed(current_paths)
        return current_emb - prior_emb


def build_faiss_index(diff_embeddings: np.ndarray, index_path: Path, ids_path: Path, ids: np.ndarray):
    """
    Build a flat L2 FAISS index over (N, D) diff embeddings and persist it
    alongside a parallel array of corpus row ids for lookup after search.
    """
    import faiss

    index_path = Path(index_path)
    ids_path = Path(ids_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    dim = diff_embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(diff_embeddings.astype(np.float32))
    faiss.write_index(index, str(index_path))
    np.save(ids_path, ids)


class ImageDiffIndex:
    def __init__(self, index_path: Path, ids_path: Path):
        import faiss

        self.index = faiss.read_index(str(index_path))
        self.ids = np.load(ids_path, allow_pickle=True)

    def search(self, query_diff_embedding: np.ndarray, top_k: int = 20):
        """
        Returns (corpus_ids, distances) for the top_k nearest diff embeddings.
        Distances are L2 (smaller = more similar); convert to a similarity in
        [0, 1] with a simple negative-exponential if blending with the
        signature-similarity score in retrieve.py.
        """
        query = query_diff_embedding.astype(np.float32).reshape(1, -1)
        distances, indices = self.index.search(query, top_k)
        result_ids = self.ids[indices[0]]
        return result_ids, distances[0]


def l2_to_similarity(distances: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Convert L2 distances to a (0, 1] similarity score via negative exponential."""
    return np.exp(-distances / scale)
