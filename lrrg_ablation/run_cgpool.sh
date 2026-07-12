#!/usr/bin/env bash
# Curate + run the FULL-split ablation on cgpool (inference only).
# First: activate ~/lrrg_venv and `hf auth login` (do NOT export HF_TOKEN).
# Best run inside tmux; the ablation is RESUMABLE — re-run this to continue.
# Scoring is a separate step in a separate venv (see README step 3).
set -e
# Remove system cuDNN from LD_LIBRARY_PATH — PyTorch 2.11 bundles cuDNN 9.19 but the
# system path injects 9.1.0, causing a symbol mismatch and core dump.
export LD_LIBRARY_PATH=$(echo "${LD_LIBRARY_PATH}" | tr ':' '\n' | grep -v 'cudnn' | tr '\n' ':' | sed 's/:$//')
export HF_HOME="${HF_HOME:-/graphics/scratch2/students/CHANGEME/hf}"   # scratch w/ ~20GB free
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
python curate_subset.py --prior-mode image_and_report --out subset.jsonl          # --n 0 = full split
python run_ablation.py  --subset subset.jsonl --out predictions.csv --prior-mode image_and_report
echo ">> Inference done -> predictions.csv. Score next (venv_score): see README step 3."
