# ICL Retrieve-then-Revise Pipeline

Implementation of the design in `icl_pipeline_spec.md`: MAIRA-2 drafts the
Findings section, Qwen2.5-7B-Instruct revises only the comparison/temporal
sentences using retrieved exemplars, and a CheXbert-F1 guardrail ensures the
revision never makes a case worse than the raw MAIRA-2 draft. No training.

## Integration with the existing repo

This was cross-checked directly against the repo contents (not guessed):

- **Manifest schema** matches `train_pairs_ulcx.jsonl` / `test_pairs_ulcx.jsonl`
  at the repo root (built by `ulcx_to_manifest.py`), and `maira_ddatr/data.py`'s
  `FIELD_MAP`: `current_study_id`, `subject_id`, `current_image`, `prior_image`,
  `indication`, `comparison`, `prior_findings`, `reference_findings`, `change`.
  There is no `technique` field.
- **CheXbert** uses the already-installed `f1chexbert` package (same one
  `lrrg_ablation/score.py` calls), not a manual stanfordmlgroup/chexbert
  clone. `chexbert_utils.py` wraps `F1CheXbert.get_label(..., mode="rrg")`
  for binary presence (score.py's own convention) and
  `mode="classification"` for the finer 4-class signal the change signature
  needs.
- **MAIRA-2 drafting** (`maira2_draft.py`) mirrors `run_ablation.py`'s
  `generate()` function almost exactly -- that call is already confirmed
  working against the gated checkpoint on cgpool. The one deliberate
  difference: `run_ablation.py` hardcodes `comparison="None."` to isolate
  the prior as a single manipulated variable for its ablation; ICL always
  runs the with-prior arm, so `comparison` is passed through from the
  manifest for realistic context instead.
- **Val split**: `ulcx/val.json` (the ULCX split file) exists, but nobody has
  run `ulcx_to_manifest.py` against it yet, so there is no
  `val_pairs_ulcx.jsonl` on disk. `build_retrieval_corpus.py` defaults to
  `--splits train` only. To add val:
  ```bash
  python ulcx_to_manifest.py --ulcx-json ulcx/val.json --split val \
      --prior-mode image_and_report --out val_pairs_ulcx.jsonl
  ```

## Setup

```bash
export XDG_CACHE_HOME=/var/tmp/xdg_cache_grauperez   # reuse the already-cached
                                                       # chexbert.pth instead of
                                                       # f1chexbert re-downloading
unset LD_LIBRARY_PATH        # avoid system cuDNN (9.1.0) vs PyTorch bundled cuDNN conflict
unset HF_TOKEN && hf auth login   # never `export HF_TOKEN`
pip install -r requirements.txt   # mostly a subset of the repo's own requirements.txt,
                                  # plus faiss-cpu / pyarrow / tqdm for this pipeline
```

Run everything inside tmux to survive SSH disconnects: `tmux new -s lrrg`

## Usage

**1. Build the retrieval corpus** (train only for now; never test --
`test_pairs_ulcx.jsonl` staying out of this is the leakage guard):

```bash
python build_retrieval_corpus.py --splits train
# add --build-image-diff-index for the optional FAISS image-diff index
# (requires config.RETRIEVAL.use_image_diff = True and RAD-DINO)
```

This labels ~85k reports with CheXbert one at a time (`f1chexbert` labels a
single report per call internally, so there's no batching speedup to be had
here) -- expect this to be the slow step; it's not resumable, so run it in
tmux and let it finish once.

**2. Before trusting the sentence classifier at scale**, hand-label ~100-200
sentences from ULCX reports and check precision/recall (per spec -- the
classifier in `temporal_utils.py` is reused for corpus building, query
signature construction, and splice targeting, so its errors compound):

```python
from temporal_utils import review_precision_recall
labeled = [("Compared to the prior study, effusion has increased.", True), ...]
print(review_precision_recall(labeled))
```

**3. Run the pipeline** over the test split (resumable -- safe to Ctrl-C and
re-run):

```bash
python run_icl_pipeline.py --limit 20   # smoke test first
python run_icl_pipeline.py              # full run (1,786 pairs, subset to valid prior-conditioned population)
```

Outputs go to `config.PATHS.draft_cache_file` (MAIRA-2 drafts, cached
separately so a slow drafting stage isn't repeated) and
`config.PATHS.final_output_file` (per-case draft/revised/final text, accept
decision, CheXbert-F1 for both, the manifest's `change` flag, and which
exemplars were used).

## Parameters worth tuning (see spec for detail)

- `RetrievalConfig.k` -- exemplar count (start 3-5)
- `RetrievalConfig.alpha` -- signature vs. image-diff weight (start 0.7)
- `GuardrailConfig.mode` -- `strict_per_case` (recommended, default) vs.
  `aggregate_floor`
- `TEMPORAL_KEYWORDS` in `config.py` -- first pass, needs manual review

## Evaluation

`guardrail.summary()` (printed at the end of `run_icl_pipeline.py`) gives
draft vs. final mean CheXbert-F1, guardrail reject rate, and both stratified
by the manifest's `change` flag (curate_subset's keyword-based
longitudinal-mention label -- noisy per its own docstring, but the same
label `score.py` stratifies on). For the full metric stack (RadGraph-F1,
Temporal-F1/TEM, GREEN, plus bootstrap CIs) feed `final_output_file`'s
`final_text` into the existing `score.py` rather than re-implementing that
here -- this repo's own F1 in `chexbert_utils.py` exists only to drive the
per-case guardrail decision inside the generation loop, and it's worth a
quick side-by-side check against `score.py`'s numbers on a handful of cases
so the two never silently diverge (`score.py` calls `f1chexbert`'s
`classification_report` "micro avg"/"macro avg" over a whole stratum at
once; this module computes per-case `sklearn.f1_score` on the same
`mode="rrg"` presence vectors -- same underlying labels, different
aggregation granularity).

## Files

| File | Role |
|---|---|
| `config.py` | paths, hyperparameters, temporal keyword list |
| `temporal_utils.py` | comparison-sentence classifier (shared across 3 usage sites) |
| `chexbert_utils.py` | f1chexbert wrapper: labeling, change signature, F1 scoring |
| `image_diff_utils.py` | optional RAD-DINO image-diff embedding + FAISS |
| `maira2_draft.py` | MAIRA-2 frozen-backbone drafting (mirrors run_ablation.py) |
| `build_retrieval_corpus.py` | CLI: builds the exemplar corpus from train (+ val) |
| `retrieve.py` | top-k exemplar retrieval, signature + optional image blend |
| `revise.py` | Qwen revision, anonymization, sentence splice |
| `guardrail.py` | CheXbert-F1 floor, accept/reject, change-stratified tracking |
| `run_icl_pipeline.py` | orchestrator CLI, resumable, ETA logging |

## Still worth a second look

- `maira2_draft.py`'s generation call has not been run on cgpool by this
  pass -- it's a direct copy of `run_ablation.py`'s pattern rather than new
  code, so it should work, but worth confirming end-to-end on a couple of
  real cases before the full run.
- The sentence classifier (`temporal_utils.TEMPORAL_KEYWORDS`) is a first
  pass; do the precision/recall check in step 2 above before trusting it at
  scale.
