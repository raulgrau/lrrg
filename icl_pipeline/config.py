"""
Central config for the ICL retrieve-then-revise pipeline.

Paths below match the actual repo layout (checked directly, not guessed):
  ~/lrrg/train_pairs_ulcx.jsonl   84,982 pairs, built by ulcx_to_manifest.py
                                  from ULCX's train.json
  ~/lrrg/test_pairs_ulcx.jsonl    1,786 pairs, from ULCX's test.json -- this
                                  is the eval split, NEVER used for corpus
                                  building
  ~/lrrg/ulcx/val.json            ULCX's val split IDs exist, but nobody has
                                  run ulcx_to_manifest.py against it yet, so
                                  there is no val_pairs_ulcx.jsonl on disk.
                                  val_manifest below is left pointing at where
                                  it *would* land; build_retrieval_corpus.py
                                  defaults to --splits train only until it
                                  exists (see build_retrieval_corpus.py --help).

Manifest schema (confirmed from a real record in test_pairs_ulcx.jsonl, and
matching maira_ddatr/data.py's FIELD_MAP):
    subject_id, current_study_id, prior_study_id,
    current_image, prior_image,          (absolute paths into MIMIC-CXR-JPG)
    indication, comparison,              (there is no "technique" field)
    prior_findings, reference_findings,  (Findings-section text)
    change                               (bool; curate_subset's keyword-based
                                          longitudinal-mention label -- noisy,
                                          per ulcx_to_manifest.py's own note --
                                          used here only for reporting, same
                                          as score.py's stratification)
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Paths:
    repo_root: Path = Path("~/lrrg").expanduser()

    train_manifest: Path = repo_root / "train_pairs_ulcx.jsonl"
    val_manifest: Path = repo_root / "val_pairs_ulcx.jsonl"   # not built yet -- see note above
    test_manifest: Path = repo_root / "test_pairs_ulcx.jsonl"

    # Outputs of build_retrieval_corpus.py
    corpus_dir: Path = repo_root / "icl_pipeline" / "corpus"
    corpus_file: Path = corpus_dir / "comparison_corpus.parquet"
    image_diff_index_file: Path = corpus_dir / "image_diff.faiss"
    image_diff_ids_file: Path = corpus_dir / "image_diff_ids.npy"

    # CheXbert: handled by the installed `f1chexbert` package (see
    # chexbert_utils.py), which downloads/caches its own checkpoint at
    # $XDG_CACHE_HOME/chexbert/chexbert.pth (appdirs.user_cache_dir). Project
    # memory records the checkpoint already living at
    # /var/tmp/xdg_cache_grauperez/chexbert/chexbert.pth -- make sure
    # XDG_CACHE_HOME=/var/tmp/xdg_cache_grauperez is exported before running
    # anything here, or f1chexbert will try to download a fresh copy to the
    # default cache location instead of reusing it.

    # Model identifiers (HF hub). microsoft/maira-2 is gated but instant-grant
    # (per run_ablation.py's docstring) -- accept the license on the model
    # page, then `huggingface-cli login` / `hf auth login`.
    maira2_model_id: str = "microsoft/maira-2"
    qwen_model_id: str = "Qwen/Qwen2.5-7B-Instruct"
    raddino_model_id: str = "microsoft/rad-dino"

    # Pipeline run outputs
    run_dir: Path = repo_root / "icl_pipeline" / "runs"
    draft_cache_file: Path = run_dir / "drafts.jsonl"          # MAIRA-2 drafts, resumable cache
    final_output_file: Path = run_dir / "icl_final.jsonl"      # final per-case results


@dataclass
class RetrievalConfig:
    k: int = 4                       # exemplars per query, start 3-5 per spec
    use_image_diff: bool = False     # flip on once RAD-DINO diff index is built
    alpha: float = 0.7               # weight on CheXbert-signature similarity vs image-diff similarity
    signature_metric: str = "hamming"  # "hamming" or "cosine" over the 14-dim transition vector


@dataclass
class GuardrailConfig:
    mode: str = "strict_per_case"    # "strict_per_case" or "aggregate_floor"
    # only used if mode == "aggregate_floor": require revised corpus mean F1 >=
    # draft corpus mean F1 - aggregate_floor_slack
    aggregate_floor_slack: float = 0.0


@dataclass
class ReviseConfig:
    max_new_tokens: int = 256
    temperature: float = 0.2         # low temperature: revision should be conservative, not creative
    anonymize_exemplars: bool = True


# Temporal / comparison keyword list shared by temporal_utils.py.
# First pass only -- per spec, this needs manual precision/recall review
# against a sample of ULCX reports before trusting it in all three usage sites
# (corpus build, query signature, splice targeting).
TEMPORAL_KEYWORDS = [
    "compared to", "compared with", "in comparison",
    "since the prior", "since the previous", "since prior",
    "unchanged", "stable", "no significant change", "no interval change",
    "improved", "improvement", "increased", "increasing",
    "worsened", "worsening", "decreased", "decreasing",
    "new since", "newly appeared", "new compared",
    "resolved", "resolution of",
    "redemonstrat",  # stem: redemonstrated / redemonstration
    "interval",
    "again seen", "again noted",
    "no longer seen", "no longer present",
    "persistent", "persisting",
    "progression", "progressed",
    "recurrence", "recurrent",
]

PATHS = Paths()
RETRIEVAL = RetrievalConfig()
GUARDRAIL = GuardrailConfig()
REVISE = ReviseConfig()
