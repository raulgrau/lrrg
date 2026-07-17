# MAIRA-2 + DDaTR on Modal

Run the training on an 80GB A100/H100 instead of the 24GB 3090. This wraps the
**existing, cluster-tested** `maira_ddatr/train.py` unchanged — Modal only
provides the GPU, the staged data, and persistent checkpoints.

## Why move here

The 3090 is at a hard VRAM floor: batch=1 with gradient checkpointing *mandatory*
(disabling it OOMs). Even after the strip-mode win, the epoch is ~54h. On 80GB:

- drop gradient checkpointing → recovers the ~2.4x→~2x backward blowup
- keep strip mode's ~1.9x
- (later) raise batch size past 1

These compound. A rough, **unmeasured** estimate is an epoch in the ~10–16h range;
confirm with a `--profile` run on Modal exactly like we did on the 3090 before
committing to the full epoch.

## The data problem (the real friction)

No PhysioNet credentials → the images must be pushed from the **cgpool copy you
already have**, not downloaded fresh. And the manifests store **absolute cgpool
paths** (`/graphics/scratch2/...`) which `data.py._abs()` passes through
untouched, so `--image_root` can't remap them. Two steps solve it:

1. **Stage** the 112,904 referenced images (~165GB, a subset of the 558GB full
   set) onto a Modal Volume, via `stage_upload.py` — it runs on cgpool and uses
   the Modal SDK's `batch_upload` to push each file straight from the local copy
   into the Volume, preserving the `physionet.org/...` subtree. No tar, no extra
   scratch disk, no PhysioNet login. Resumable via a local progress file.
2. **Rewrite** the manifest prefix from the cgpool path to the Volume mount
   (`/data/physionet.org/...`). `run_training` does this automatically.

Only the referenced files move, not the whole dataset — the exact list is
`maira_ddatr/mimic_subset_relpaths.txt` (generated from your two manifests).

**Transfer is bounded by cgpool's outbound bandwidth**, so ~165GB is the real
cost here — likely a few hours. If you'd rather shrink it, subsampling the
training set (e.g. ~25–30k pairs) cuts both the upload *and* the epoch time
roughly proportionally; say the word and I'll add a `--subsample` path.

## One-time setup

```bash
# install modal in its OWN venv (keep it out of lrrg_venv — it downgrades protobuf)
python3 -m venv ~/modal_venv && source ~/modal_venv/bin/activate
pip install modal
modal token set --token-id ak-xxx --token-secret as-xxx   # from modal.com/settings/tokens

# gated MAIRA-2 weights (only secret needed — no PhysioNet)
modal secret create huggingface HF_TOKEN=hf_xxx
```

**Dependency pins are locked** to your cgpool venv (`torch==2.11.0+cu128`,
`transformers==4.51.3`, `peft==0.19.1`, `bitsandbytes==0.49.2`,
`accelerate==1.14.0`). Two deliberate notes:

- torch's `+cu128` build isn't on PyPI, so the image pulls it from PyTorch's
  cu128 index in a dedicated step. If a Modal GPU host's driver is too old for
  CUDA 12.8 (unlikely on A100/H100), switch `TORCH_INDEX` to `.../whl/cu124`.
- The Modal image uses **Python 3.11**, not cgpool's 3.14 — intentional (far
  better wheel availability, and none of the code needs 3.14). All pinned deps
  ship cp311 wheels.

## Run it

```bash
cd modal/

# 1. stage images from cgpool -> Volume (runs locally on cgpool; resumable)
python stage_upload.py \
    --relpaths ../mimic_subset_relpaths.txt \
    --src-root /graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/physionet.org \
    --volume mimic-cxr-jpg

# 2. train (rewrites manifest to the Volume, then launches train.py on the GPU)
modal run --detach modal_app.py::run_training --manifest ../train_pairs_ulcx.jsonl
```

Checkpoints land on the `lrrg-runs` Volume and `train.py` is resumable, so a
container restart continues where it left off.

## Recommended: profile before the full epoch

Before the 10-16h run, do a Modal `--profile` pass (add `--profile
--profile_steps 40 --max_steps 40` via `extra_args`) to get the real
per-sample time on the actual GPU — same discipline that caught the wrong
bottleneck twice on the 3090. Then decide A100 vs H100 vs multi-GPU (`gpu="H100:4"`).

## Notes / unverified bits

- **Staging assumes** the cgpool copy lives under
  `.../MIMIC-CXR-JPG/physionet.org/files/mimic-cxr-jpg/2.0.0/files/...`
  (matches the manifest paths). `stage_upload.py` fail-fasts if `--src-root` is
  wrong. Transfer speed is whatever cgpool's uplink gives.
- **Dependency pins** are a best guess (see CONFIRM above).
- **batch=1** is still hardcoded in the pipeline; real batching is a separate,
  larger refactor (padding + removing `has_prior.item()` scalar assumptions).
  The 80GB headroom makes it worthwhile later but it is not wired yet.
