"""
CheXbert wrapper built on the `f1chexbert` package (already in
requirements.txt and already used by lrrg_ablation/score.py), NOT a manual
reimplementation of stanfordmlgroup/chexbert. Checked the package source
directly (f1chexbert==0.0.2):

- `F1CheXbert()` loads bert-base-uncased + the CheXbert linear heads and
  auto-downloads/caches the checkpoint at
  $XDG_CACHE_HOME/chexbert/chexbert.pth (appdirs.user_cache_dir("chexbert")),
  falling back to HF hub repo StanfordAIMI/RRG_scorers if absent. Make sure
  XDG_CACHE_HOME=/var/tmp/xdg_cache_grauperez is exported before running
  anything here (per project memory, that's where the checkpoint already
  lives) or it will try to fetch a second copy to the default location.

- `.get_label(report, mode="rrg")` returns a 14-length list of {0,1}: binary
  presence with positive-OR-uncertain counted as present. This is exactly
  the convention lrrg_ablation/score.py relies on (it calls the module's
  `forward()`, which uses this same default mode internally).

- `.get_label(report, mode="classification")` returns the finer 4-way
  per-condition label: '' (blank/no mention), 1 (positive), 0 (negative),
  -1 (uncertain). Used here only for the retrieval change signature, which
  per spec wants the full positive/negative/uncertain/no-mention distinction
  rather than the collapsed binary "rrg" presence.

- CONDITIONS below matches F1CheXbert.target_names order exactly (note "No
  Finding" is LAST, not first).

Guardrail F1: computed directly from the "rrg"-mode binary presence vectors
via sklearn f1_score, rather than re-calling F1CheXbert.forward() per case
(which would relabel the ground-truth report every single call). This is a
per-case, per-revision metric needed inside the generation loop -- for the
final reported numbers (stratified by change/no-change, with bootstrap CIs),
feed final_output_file into score.py directly rather than trusting this
module's aggregate, so the two never silently diverge.
"""
from typing import Sequence

import numpy as np

# Matches f1chexbert.F1CheXbert.target_names order exactly.
CONDITIONS = [
    "Enlarged Cardiomediastinum", "Cardiomegaly", "Lung Opacity", "Lung Lesion",
    "Edema", "Consolidation", "Pneumonia", "Atelectasis", "Pneumothorax",
    "Pleural Effusion", "Pleural Other", "Fracture", "Support Devices", "No Finding",
]
N_CONDITIONS = len(CONDITIONS)  # 14

BLANK, POSITIVE, NEGATIVE, UNCERTAIN = 0, 1, 2, 3
_CLASSIFICATION_VALUE_TO_CLASS_ID = {"": BLANK, 1: POSITIVE, 0: NEGATIVE, -1: UNCERTAIN}


class CheXbertLabeler:
    def __init__(self, device: str = None):
        from f1chexbert import F1CheXbert

        self._cb = F1CheXbert(device=device)

    def label_presence(self, text: str) -> np.ndarray:
        """(14,) binary presence array, positive-or-uncertain-as-present."""
        return np.array(self._cb.get_label(text, mode="rrg"), dtype=int)

    def label_presence_batch(self, texts: Sequence[str]) -> np.ndarray:
        return np.stack([self.label_presence(t) for t in texts], axis=0)

    def label_signed_batch(self, texts: Sequence[str]) -> np.ndarray:
        return np.stack([self.label_signed(t) for t in texts], axis=0)

    def label_signed(self, text: str) -> np.ndarray:
        """(14,) class-id array in {BLANK, POSITIVE, NEGATIVE, UNCERTAIN}."""
        raw = self._cb.get_label(text, mode="classification")
        return np.array([_CLASSIFICATION_VALUE_TO_CLASS_ID[v] for v in raw], dtype=int)


def chexbert_f1(pred_presence: np.ndarray, gt_presence: np.ndarray, average: str = "micro") -> float:
    """
    CheXbert-F1 between predicted and reference *presence* arrays (output of
    label_presence / label_presence_batch), each (N, 14) or (14,).
    """
    from sklearn.metrics import f1_score

    pred_presence = np.atleast_2d(pred_presence)
    gt_presence = np.atleast_2d(gt_presence)
    return float(f1_score(gt_presence, pred_presence, average=average, zero_division=0))


def change_signature(prior_signed: np.ndarray, current_signed: np.ndarray) -> np.ndarray:
    """
    Per-report transition vector between prior and current CheXbert signed
    labels (output of label_signed). transition_id = prior_class * 4 +
    current_class, 16 possible transitions per pathology. Shape: (14,) ints
    in [0, 15].
    """
    assert prior_signed.shape == (N_CONDITIONS,)
    assert current_signed.shape == (N_CONDITIONS,)
    return prior_signed.astype(int) * 4 + current_signed.astype(int)


def signature_similarity(sig_a: np.ndarray, sig_b: np.ndarray, metric: str = "hamming") -> float:
    """Similarity between two (14,) transition-signature vectors, in [0, 1]."""
    assert sig_a.shape == sig_b.shape == (N_CONDITIONS,)
    if metric == "hamming":
        return float(np.mean(sig_a == sig_b))
    elif metric == "cosine":
        def one_hot(sig):
            oh = np.zeros((N_CONDITIONS, 16), dtype=float)
            oh[np.arange(N_CONDITIONS), sig] = 1.0
            return oh.flatten()

        va, vb = one_hot(sig_a), one_hot(sig_b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        return float(np.dot(va, vb) / denom) if denom > 0 else 0.0
    else:
        raise ValueError(f"unknown metric: {metric}")


if __name__ == "__main__":
    # signature/similarity smoke test (no model load required)
    prior = np.array([NEGATIVE] * 14)
    current_same = np.array([NEGATIVE] * 14)
    current_diff = np.array([POSITIVE] * 7 + [NEGATIVE] * 7)
    sig1 = change_signature(prior, current_same)
    sig2 = change_signature(prior, current_diff)
    print("identical signature similarity:", signature_similarity(sig1, sig1))
    print("differing signature similarity:", signature_similarity(sig1, sig2))
