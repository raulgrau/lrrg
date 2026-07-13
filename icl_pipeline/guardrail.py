"""
Guardrail: never let the ICL revision make a case's CheXbert-F1 worse than
the raw MAIRA-2 draft. This is what makes the pipeline monotonic per spec --
plain MAIRA-2 is always a safety net.

Two modes (config.GUARDRAIL.mode):
  - "strict_per_case" (default, recommended): compute CheXbert-F1 for both
    draft and revised report against ground truth, per case; reject
    (fall back to draft) whenever revised_f1 < draft_f1.
  - "aggregate_floor": always accept the revision, but track the running
    mean F1 for draft vs. revised; this mode doesn't reject any individual
    case, so treat its results as informational only unless the aggregate
    check at the end actually passes (revised_mean >= draft_mean - slack).
    Prefer strict_per_case unless you have a specific reason to look at
    aggregate behavior.

Also tracks accept/reject and F1 by the manifest's `change` flag (curate_subset's
keyword-based longitudinal-mention label), mirroring lrrg_ablation/score.py's
change-vs-no-change stratification -- this is where the spec expects the ICL
revision to matter most (Zhu et al.: ~84% error on changed-label cases vs
~11% on stable cases).
"""
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from chexbert_utils import CheXbertLabeler, chexbert_f1
from config import GUARDRAIL


@dataclass
class GuardrailResult:
    accepted: bool
    draft_f1: float
    revised_f1: float
    final_text: str


class Guardrail:
    def __init__(self, labeler: CheXbertLabeler, mode: str = GUARDRAIL.mode):
        self.labeler = labeler
        self.mode = mode
        # overall
        self.draft_f1_history: List[float] = []
        self.final_f1_history: List[float] = []
        self.reject_count = 0
        self.total_count = 0
        # stratified by manifest `change` flag
        self.draft_f1_by_change = {True: [], False: []}
        self.final_f1_by_change = {True: [], False: []}
        self.reject_count_by_change = {True: 0, False: 0}
        self.total_count_by_change = {True: 0, False: 0}

    def score_case(
        self,
        draft_text: str,
        revised_text: str,
        revision_succeeded: bool,
        gt_presence: np.ndarray,
        change: Optional[bool] = None,
    ) -> GuardrailResult:
        """
        gt_presence: precomputed (14,) CheXbert binary-presence array for the
        ground truth report (labeler.label_presence(gt_text)) -- precompute
        once per case upstream (see run_icl_pipeline.py) rather than
        relabeling gt on every call.
        change: the manifest's `change` bool flag for this case, if available,
        for stratified bookkeeping only (does not affect the accept/reject
        decision).
        """
        self.total_count += 1
        if change is not None:
            self.total_count_by_change[bool(change)] += 1

        def _record(accept: bool, draft_f1: float, final_f1: float):
            self.draft_f1_history.append(draft_f1)
            self.final_f1_history.append(final_f1)
            if not accept:
                self.reject_count += 1
            if change is not None:
                self.draft_f1_by_change[bool(change)].append(draft_f1)
                self.final_f1_by_change[bool(change)].append(final_f1)
                if not accept:
                    self.reject_count_by_change[bool(change)] += 1

        if not revision_succeeded:
            # revise.py already returned the draft unchanged on failure;
            # nothing to score differently, this is an automatic reject.
            draft_presence = self.labeler.label_presence(draft_text)
            draft_f1 = chexbert_f1(draft_presence, gt_presence)
            _record(False, draft_f1, draft_f1)
            return GuardrailResult(False, draft_f1, draft_f1, draft_text)

        draft_presence = self.labeler.label_presence(draft_text)
        revised_presence = self.labeler.label_presence(revised_text)
        draft_f1 = chexbert_f1(draft_presence, gt_presence)
        revised_f1 = chexbert_f1(revised_presence, gt_presence)

        if self.mode == "strict_per_case":
            accept = revised_f1 >= draft_f1
            final_text = revised_text if accept else draft_text
            final_f1 = revised_f1 if accept else draft_f1
            _record(accept, draft_f1, final_f1)
            return GuardrailResult(accept, draft_f1, revised_f1, final_text)

        elif self.mode == "aggregate_floor":
            # Always accept; floor is checked in aggregate via summary().
            _record(True, draft_f1, revised_f1)
            return GuardrailResult(True, draft_f1, revised_f1, revised_text)

        else:
            raise ValueError(f"unknown guardrail mode: {self.mode}")

    def summary(self) -> dict:
        def _mean(xs):
            return float(np.mean(xs)) if xs else float("nan")

        draft_mean = _mean(self.draft_f1_history)
        final_mean = _mean(self.final_f1_history)
        reject_rate = self.reject_count / self.total_count if self.total_count else float("nan")
        aggregate_pass = (
            final_mean >= draft_mean - GUARDRAIL.aggregate_floor_slack
            if self.mode == "aggregate_floor"
            else None
        )

        by_change = {}
        for flag, label in ((True, "change"), (False, "no_change")):
            n = self.total_count_by_change[flag]
            by_change[label] = {
                "n_cases": n,
                "reject_count": self.reject_count_by_change[flag],
                "reject_rate": (self.reject_count_by_change[flag] / n) if n else float("nan"),
                "draft_mean_f1": _mean(self.draft_f1_by_change[flag]),
                "final_mean_f1": _mean(self.final_f1_by_change[flag]),
            }

        return {
            "n_cases": self.total_count,
            "reject_count": self.reject_count,
            "reject_rate": reject_rate,
            "draft_mean_f1": draft_mean,
            "final_mean_f1": final_mean,
            "mode": self.mode,
            "aggregate_floor_pass": aggregate_pass,
            "by_change_flag": by_change,
        }
