# Longitudinal CXR — Prior-Conditioning Ablation (full test split)

Runs on cgpool (RTX 3090) against the local MIMIC-CXR copy. Three stages:
curate -> run_ablation -> score. Scaled to the **full longitudinal test split**
(~2,000 pairs) so the change-vs-no-change comparison has real statistical power.

**Question:** does conditioning on the prior study improve generated Findings,
and is the effect concentrated in cases that describe interval change?

## Local data (defaults in curate_subset.py)
- images   : /graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/physionet.org/files/mimic-cxr-jpg/2.0.0/files
- reports  : /graphics/scratch2/students/mpindabe/Datasets/mimic-cxr-reports/files_reports
- metadata : /graphics/scratch2/students/mpindabe/Datasets/mimic-cxr-reports/mimic-cxr-2.0.0-metadata.csv

The scorer stratifies on `change` (does the GT mention interval change?
prior/previous/unchanged/improved/increased/...). Curation now keeps EVERY
longitudinal test case and just labels it change/no-change.

## 0. MAIRA-2 access + env (one-time)
Accept terms at https://huggingface.co/microsoft/maira-2 (instant), make a token.
```bash
python -m venv --system-site-packages ~/lrrg_venv && source ~/lrrg_venv/bin/activate
python -c "import torch" || pip install torch
pip install transformers==4.51.3 accelerate huggingface_hub pillow sentencepiece protobuf pandas
hf auth login                                   # paste token; do NOT also export HF_TOKEN
export HF_HOME=/graphics/scratch2/students/<you>/hf     # scratch w/ ~20GB free
```

## 1. Curate the full split  (~5-10 min, local I/O)
```bash
python curate_subset.py --prior-mode image_and_report --out subset.jsonl     # --n 0 = ALL
```
Prints the strata counts, e.g. `change: ~700   no-change: ~1300`. Writes one
case per line with a `change` flag. (Use `--n 200` for a quick pilot first.)

## 2. Run the ablation  (LONG — run in tmux; resumable)
~2,000 pairs x 2 generations on one 3090 is roughly **3-6 hours**. It is
**resumable**: if the session drops or you Ctrl-C, just re-run the same command
and it skips cases already in predictions.csv.
```bash
tmux new -s lrrg          # so a dropped SSH connection can't kill it
python run_ablation.py --subset subset.jsonl --out predictions.csv --prior-mode image_and_report
#   detach with Ctrl-b then d ; reattach later with: tmux attach -t lrrg
```
Prints ETA every 25 cases. Pilot first with `--limit 200` to confirm timing,
then run the full set (it will resume past the pilot's 200). `--overwrite` forces
a fresh start.

## 3. Score — stratified + significance  (separate venv, ~few min)
```bash
deactivate ; python -m venv venv_score && source venv_score/bin/activate
pip install -r requirements-score.txt
# checkpoint for CheXbert (one file, exact path the package expects):
hf download StanfordAIMI/RRG_scorers chexbert.pth --local-dir /var/tmp/xdg_cache_grauperez/chexbert
python score.py --preds predictions.csv          # writes results_stratified.json
```
Prints each metric OVERALL / change / no-change with a **paired bootstrap 95% CI
and 2-sided p-value** (1,000 resamples) for BLEU-4, ROUGE-L, METEOR, and
RadGraph-F1; CheXbert-F1 as a per-stratum point estimate. `*` = p<0.05.

To enable RadGraph-F1 (clinical, gets CIs): uncomment `radgraph` in
requirements-score.txt before installing. If its deps clash with f1chexbert,
give it its own venv.

## Reading it (for the talk)
- The headline is now the **interaction**: if the prior helps, the effect should
  be larger (and significant) in the **change** stratum and ~null in **no-change**.
  That's the clinically sensible pattern and the story the stratification tests.
- At n~700/1300 per stratum, CheXbert point estimates are stable; RadGraph carries
  the clinical significance (entity-level, with CIs).
- `results_stratified.json` has every number for regenerating slides.

## Swaps / knobs
- `--bootstrap N` (default 1000) trades runtime for CI precision.
- Fully-open MAIRA-2 alternative: `aehrc/cxrmate-tf` (swap `generate()` only).
  Note `cxrmate-rrg24` is non-longitudinal.
- AFS note: keep the model cache on /graphics/scratch (HF_HOME above), not your
  AFS home, and run inside the session's token lifetime (tmux on the node).
