"""
Shared temporal/comparison sentence classifier.

Used in three places (per spec, these must stay consistent since errors
compound across the pipeline):
  1. build_retrieval_corpus.py  -- selecting candidate exemplar sentences
  2. run_icl_pipeline.py        -- via chexbert_utils, classifying draft
                                    sentences to build the query signature
  3. revise.py                  -- splice targeting (which draft sentences
                                    are eligible for revision)

This is a first-pass rule-based classifier. Before relying on it, run
`review_precision_recall()` (or the CLI at the bottom of this file) against
a manually-labeled sample of ULCX reports and adjust config.TEMPORAL_KEYWORDS.
"""
import re
from typing import List, Tuple

from config import TEMPORAL_KEYWORDS

# Crude but adequate sentence splitter for radiology report prose. Reports
# are short, mostly declarative, and MIMIC text rarely has embedded
# abbreviated periods inside a Findings sentence in ways that would confuse
# this. Swap in a proper sentence tokenizer (e.g. syntok, scispacy) if the
# manual review in build_retrieval_corpus.py finds this splitting badly.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_KEYWORD_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in TEMPORAL_KEYWORDS), re.IGNORECASE
)


def split_sentences(text: str) -> List[str]:
    """Split a Findings section into sentences, stripping empties."""
    if not text or not text.strip():
        return []
    parts = _SENTENCE_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def is_comparison_sentence(sentence: str) -> bool:
    """True if the sentence contains any temporal/comparison keyword."""
    return _KEYWORD_PATTERN.search(sentence) is not None


def classify_report(text: str) -> Tuple[List[str], List[int]]:
    """
    Split a report into sentences and return a parallel list of 0/1 flags
    marking which sentences are comparison sentences.

    Returns:
        sentences: list of sentence strings, in original order
        flags:     list of ints (1 = comparison sentence, 0 = otherwise),
                   same length as sentences
    """
    sentences = split_sentences(text)
    flags = [1 if is_comparison_sentence(s) else 0 for s in sentences]
    return sentences, flags


def extract_comparison_sentences(text: str) -> List[str]:
    """Convenience wrapper: just the comparison sentences, in order."""
    sentences, flags = classify_report(text)
    return [s for s, f in zip(sentences, flags) if f == 1]


def review_precision_recall(labeled_examples: List[Tuple[str, bool]]) -> dict:
    """
    Quick precision/recall check against a manually labeled sample.

    labeled_examples: list of (sentence, is_comparison_ground_truth) tuples.
    Build this by hand-labeling ~100-200 sentences pulled from ULCX reports
    before trusting the classifier at scale.
    """
    tp = fp = fn = tn = 0
    for sentence, gt in labeled_examples:
        pred = is_comparison_sentence(sentence)
        if pred and gt:
            tp += 1
        elif pred and not gt:
            fp += 1
        elif not pred and gt:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) and precision == precision and recall == recall
        else float("nan")
    )
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1}


if __name__ == "__main__":
    # Smoke test with a couple of synthetic sentences.
    demo = (
        "There is a moderate right pleural effusion. Compared to the prior "
        "study, the effusion has increased in size. The cardiomediastinal "
        "silhouette is unremarkable. No new consolidation is seen."
    )
    sents, flags = classify_report(demo)
    for s, f in zip(sents, flags):
        print(f"[{f}] {s}")
