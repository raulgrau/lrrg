# MAIRA-2 + DDaTR — difference-aware encoder fusion for longitudinal CXR reporting

Plug DDaTR's difference-aware modules (DFAM / DDAM / LDConv) into MAIRA-2's
frozen RAD-DINO encoder so the model **perceives** the prior→current interval
change before the LLM ever sees it. The contribution being tested is *not*
reproducing DDaTR's table — it is: **does encoder-level difference-aware fusion
beat MAIRA-2's LLM-level late fusion of the prior, especially on change-stratum
cases?** Everything is re-measured under your existing `score.py` harness.

This is PART 1 of the plan (the DDaTR modules). PART 2 (ICL comparison
correction) is inference-only and lives outside this package.

---

## What's here

| file | role |
|---|---|
| `ddatr_modules.py` | DFAM, DDAM, LDConv, `DDaTRBlock` — ported from the repo, shape-adapted to RAD-DINO's 768×37×37 geometry. `has_prior=0` is an exact no-op. |
| `raddino_injection.py` | `InjectedRadDino` — runs RAD-DINO block-by-block, fuses the prior at injection depths (prior-stream-first-then-cache). M1 = final block; M2 = quartile blocks. |
| `maira2_ddatr_model.py` | The integration crux. Takes over the LLaVA multimodal merge via `inputs_embeds`; `build_model()` loads MAIRA-2 4-bit + QLoRA. **All cluster-specific constants live in `MAIRA2Spec` at the top.** |
| `data.py` | `LongitudinalPairDataset` + `DDaTRCollator` over your `curate_subset.py` pairs. batch=1, Findings-only CE labels, prior-report→BERT tokens. |
| `train.py` | QLoRA loop: grad accumulation, cosine+warmup, resumable checkpoints. |
| `infer.py` | Generation → resumable `score.py`-compatible JSON (carries `change_label` for stratification). |
| `probe_processor.py` | **Run once on the cluster** to print every `MAIRA2Spec` value. |

---

## Honest status (read this first)

The DDaTR cores and the merge/label logic are **CPU-validated right now** — run
any file directly (`python ddatr_modules.py`, etc.) to see its self-tests pass:
shape correctness, the `has_prior=0` no-op equals a vanilla RAD-DINO forward,
gradient flow into the injected modules, masked-scatter ordering, and
Findings-only label masking.

What could **not** be run here: a full MAIRA-2 forward (the model is gated and
7B; this sandbox has no GPU and no access to the weights). So roughly **eight
constants in `MAIRA2Spec`** — most importantly `image_token_index`, the vision
tower / projector attribute names, and the image-block order — are written with
sensible defaults but **must be confirmed on the cluster**. `probe_processor.py`
prints all of them and emits a paste-ready spec; this takes a couple of minutes.

---

## Setup

On the cluster, in your inference venv (`~/lrrg_venv`), you need the MAIRA-2
stack plus PEFT/bitsandbytes:

```bash
pip install "transformers @ git+https://github.com/huggingface/transformers.git@main" \
            accelerate peft bitsandbytes sentencepiece protobuf pillow
```

MAIRA-2 needs a specific-ish transformers; if multi-image breaks, the known
workaround is `num_additional_image_tokens=1` (already assumed: 1 CLS prefix
token → 1370 tokens/image). Make sure your HF login is active — and remember the
project pitfall: **`unset HF_TOKEN` then `hf auth login`** (an exported
`HF_TOKEN` env var shadows the saved login).

---

## Step 1 — confirm the spec (do this once)

```bash
python probe_processor.py                                   # blank images, no network
# or, to be fully faithful to real preprocessing:
python probe_processor.py --current some_frontal.jpg --prior some_prior.jpg
```

Copy its `SPEC = MAIRA2Spec(...)` block over the placeholder in
`maira2_ddatr_model.py`, and set `MAIRA2_IMAGE_STACK_ORDER` in `data.py` to match
the image-span order it reports. The two things to actually eyeball:

1. **`image_token_index`** — must match `model.config` (the probe cross-checks).
2. **image-block order** — the probe assumes spans are `(current_frontal,
   prior_frontal)` and that `pixel_values` stacks the same way. Confirm before
   using `strip_to_encoder_only` mode (additive `keep_as_tokens` mode is robust
   to this either way).

---

## Step 2 — point the loader at your data

Edit `FIELD_MAP` at the top of `data.py` so each logical field maps to whatever
column/key `curate_subset.py` writes. Logical fields:
`current_frontal_path`, `findings` (target), `prior_frontal_path` (optional),
`prior_report` *or* `prior_report_path` (optional), optional MAIRA-2 context
(`indication`/`technique`/`comparison`), `study_id`, and `change_label` if you
precomputed it (lets `infer.py` carry the stratum straight into the predictions
JSON). Missing prior → leave the prior fields empty; `has_prior` becomes 0 and
DDaTR no-ops for that study.

---

## Step 3 — M1 (cheapest working version first)

Single injection at RAD-DINO's final block. RAD-DINO runs without backprop;
you train only the two modules + projector + Vicuna q/v LoRA. Train inside
`tmux`:

```bash
python train.py \
  --train_manifest /path/to/ulcx_train.jsonl \
  --image_root /graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG \
  --out_dir runs/m1 --injection M1 \
  --grad_accum 12 --epochs 1 --lr 1e-4 --save_every 500
```

Generate + score:

```bash
python infer.py \
  --eval_manifest /path/to/ulcx_test.jsonl \
  --image_root /graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG \
  --ckpt runs/m1/ckpt.pt --injection M1 \
  --out_json preds/m1_test.json

# then your existing harness, stratified change vs no-change
python score.py --pred preds/m1_test.json   # adapt flags to your score.py
```

**Gate to proceed to M2:** M1 beats base MAIRA-2 on **change-stratum
CheXbert-F1 or Temporal-F1 without hurting no-change**.

---

## Step 4 — M2 (the multi-scale version that differentiates you)

Injection at quartile blocks `{3,6,9,12}`; gradients now flow back through the
frozen upper ViT blocks, so gradient checkpointing matters (already enabled).

```bash
python train.py ... --out_dir runs/m2 --injection M2 --grad_accum 12 --epochs 1
python infer.py ... --ckpt runs/m2/ckpt.pt --injection M2 --out_json preds/m2_test.json
```

Headline ablation: **base vs +DDaTR(M1) vs +DDaTR(M2)**, change vs no-change,
with your paired bootstrap. M2-vs-M1 is the multi-level contribution.

---

## Key knobs

- `--injection` — `M1`, `M2`, or an explicit 1-indexed block list, e.g. `3,6,9,12`.
- `--prior_image_mode`
  - `keep_as_tokens` (default): prior is *also* a vanilla LLM image block; DDaTR
    *additionally* makes the current frontal difference-aware. No token surgery,
    robust. Confound: the prior is still late-fused.
  - `strip_to_encoder_only`: prior feeds **only** the encoder fusion (not the LLM
    token stream) — the clean isolation hypothesis. Needs the verified image-block
    order. This is the §1.10 "remove LLM-side prior" ablation.
- `--require_prior` — train only on pairs that actually have a prior (sharpens
  the signal; the no-prior cases are pure vanilla MAIRA-2 anyway).
- `--text_encoder` — `bert-base-uncased` (default, mirrors the repo) or
  `microsoft/BiomedVLP-CXR-BERT-specialized` for the clinical variant.

## Failure-mode test (do report it)

Re-run `infer.py` on a copy of the test manifest with the prior image swapped for
a dummy/unrelated one (or zeroed). If encoder fusion is real, scores degrade; if
they don't move, the modules are ignoring the prior. This is the dummy/corrupted-
prior degradation check from §1.9.

## If the 3090 says no

Fall back to **M1-only** (no ViT backprop), raise LoRA rank or fully unfreeze the
small projector if LoRA can't absorb the token-distribution shift, or — per the
plan's safety net — pivot to training-free CCD (already validated on MAIRA-2),
which composes with the ICL stage just as well.

---

## License & citation

⚠️ **The DDaTR repo (`github.com/xmed-lab/DDaTR`) ships no LICENSE file and its
README states no license.** The module code here is an *adaptation* of
`models/resnet.py` (PWAM/SILA → DFAM, FeatureFusion → DDAM, central-difference
conv → LDConv), reshaped for RAD-DINO. Before redistributing or publishing,
confirm reuse terms with the authors. Note also that `microsoft/maira-2` and
`microsoft/rad-dino-maira-2` are released **for research use only**.

Cite the method this is built on:

> Song et al. *DDaTR: Dynamic Difference-aware Temporal Reasoning for Longitudinal
> Radiology Report Generation.* IEEE TMI, 2025. arXiv:2505.03401.

and MAIRA-2 (arXiv:2406.04449) and RAD-DINO (Nature Machine Intelligence, 2025).
