"""
modal_app.py -- run MAIRA-2 + DDaTR training on Modal (A100/H100).

Why: the RTX 3090 hits a hard 24GB VRAM floor at batch=1 -- gradient
checkpointing is mandatory there, and even strip mode leaves an ~54h epoch.
On an 80GB A100/H100 the same run can (a) drop checkpointing (recovers the
~2.4x->~2x backward ratio), (b) keep strip mode's ~1.9x, and (c) eventually
raise batch size -- compounding to a far shorter epoch.

Data staging is a SEPARATE local script -- `stage_upload.py` -- because there
are no PhysioNet credentials; the images must be pushed from the cgpool copy you
already have, via the Modal SDK's batch_upload. Run that FIRST (on cgpool), then
this app's entrypoints:
    1. rewrite  -- repoint the manifest's image paths at the Volume mount.
    2. train    -- the GPU training run, wrapping the EXISTING, cluster-tested
                   train.py unchanged.

------------------------------------------------------------------------------
BEFORE RUNNING -- two things to confirm (marked CONFIRM below):
  * transformers/peft/bitsandbytes versions must match your WORKING cgpool venv
    (MAIRA-2 uses trust_remote_code; version drift breaks the custom modeling).
    Dump them on cgpool:  pip freeze | grep -Ei 'transformers|peft|bitsandbytes|accelerate|torch'
  * HuggingFace token secret (MAIRA-2 is gated):
    modal secret create huggingface HF_TOKEN=hf_...
------------------------------------------------------------------------------

Usage (from this modal/ dir, with the maira_ddatr/ code one level up):
    # 0. stage data first (separate script, runs on cgpool -- see stage_upload.py)
    modal run modal_app.py::run_training --manifest ../train_pairs_ulcx.jsonl
"""

from __future__ import annotations

import os
import modal

# --------------------------------------------------------------------------- #
#  Image
# --------------------------------------------------------------------------- #
# PINNED to Raul's working cgpool venv (pip freeze, 2026-07):
#   accelerate==1.14.0  bitsandbytes==0.49.2  peft==0.19.1
#   torch==2.11.0+cu128  transformers==4.51.3
# torch's +cu128 (CUDA 12.8) build is NOT on PyPI -- it comes from PyTorch's
# cu128 index in a separate pip_install step; everything else is from PyPI.
# If Modal's GPU host driver is too old for CUDA 12.8 (unlikely on A100/H100),
# fall back to the cu124 index + torch==2.11.0 there.
TORCH = "torch==2.11.0"
TORCH_INDEX = "https://download.pytorch.org/whl/cu128"
PY_DEPS = [
    "transformers==4.51.3",
    "accelerate==1.14.0",
    "peft==0.19.1",
    "bitsandbytes==0.49.2",
    "sentencepiece",
    "protobuf",
    "pillow",
    "pandas",
    "huggingface_hub",
]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("wget", "ca-certificates")
    # torch (CUDA 12.8) from the PyTorch index, isolated so pip can't grab a
    # CPU-only 2.11.0 off PyPI instead.
    .pip_install(TORCH, index_url=TORCH_INDEX)
    .pip_install(*PY_DEPS)
    # ship the existing, tested training code (one dir up from this file)
    .add_local_dir(
        os.path.join(os.path.dirname(__file__), "..", "maira_ddatr"),
        remote_path="/root/maira_ddatr",
    )
)

app = modal.App("lrrg-ddatr", image=image)

# Persistent Volumes: images (staged once, reused) and run outputs (checkpoints
# survive across container restarts -- train.py is already resumable).
data_vol = modal.Volume.from_name("mimic-cxr-jpg", create_if_missing=True)
runs_vol = modal.Volume.from_name("lrrg-runs", create_if_missing=True)

DATA_MOUNT = "/data"
RUNS_MOUNT = "/runs"

hf_secret = modal.Secret.from_name("huggingface")        # HF_TOKEN=...

# NOTE: data staging is NOT here -- it's the local stage_upload.py script, which
# pushes the cgpool copy of the images onto the `mimic-cxr-jpg` Volume via the
# Modal SDK (no PhysioNet credentials required). Run it before these entrypoints.


# --------------------------------------------------------------------------- #
#  1. Rewrite a manifest to point at the Volume mount
# --------------------------------------------------------------------------- #
CGPOOL_PREFIX = "/graphics/scratch2/staff/bundeleva/Downloads/MIMIC-CXR-JPG/"


@app.function(volumes={DATA_MOUNT: data_vol})
def rewrite(manifest_text: str) -> str:
    """Return the manifest with cgpool image prefixes swapped for the mount."""
    import json
    mount = DATA_MOUNT.rstrip("/") + "/"
    out_lines, n, rw = [], 0, 0
    for line in manifest_text.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        n += 1
        for k in ("current_image", "prior_image"):
            p = r.get(k)
            if p and p.startswith(CGPOOL_PREFIX):
                r[k] = mount + p[len(CGPOOL_PREFIX):]
                rw += 1
        out_lines.append(json.dumps(r))
    print(f"[rewrite] {rw} paths across {n} records")
    return "\n".join(out_lines) + "\n"


# --------------------------------------------------------------------------- #
#  2. Train  (wraps the EXISTING train.py unchanged)
# --------------------------------------------------------------------------- #
@app.function(
    gpu="A100-80GB",              # or "H100"; ":n" for multi-GPU later
    volumes={DATA_MOUNT: data_vol, RUNS_MOUNT: runs_vol},
    secrets=[hf_secret],
    timeout=24 * 60 * 60,         # long; train.py checkpoints + is resumable
)
def train(
    train_manifest_text: str,
    injection: str = "M1",
    prior_image_mode: str = "strip_to_encoder_only",
    grad_accum: int = 12,
    epochs: int = 1,
    lr: float = 1e-4,
    save_every: int = 500,
    no_grad_checkpointing: bool = True,   # 80GB should fit batch=1 w/o checkpointing
    extra_args: list[str] | None = None,
):
    import subprocess

    # HF auth for gated MAIRA-2 (never export a stale HF_TOKEN elsewhere)
    os.environ.setdefault("HF_HOME", os.path.join(DATA_MOUNT, "hf"))

    # write the (already-rewritten) manifest into the container
    manifest_path = "/root/train_pairs_modal.jsonl"
    with open(manifest_path, "w") as f:
        f.write(train_manifest_text)

    out_dir = os.path.join(RUNS_MOUNT, f"m1_{prior_image_mode}")
    resume = os.path.join(out_dir, "ckpt.pt")

    cmd = [
        "python", "train.py",
        "--train_manifest", manifest_path,
        "--out_dir", out_dir,
        "--injection", injection,
        "--prior_image_mode", prior_image_mode,
        "--grad_accum", str(grad_accum),
        "--epochs", str(epochs),
        "--lr", str(lr),
        "--save_every", str(save_every),
    ]
    if no_grad_checkpointing:
        cmd.append("--no_grad_checkpointing")
    if os.path.exists(resume):
        cmd += ["--resume", resume]
        print(f"[train] resuming from {resume}")
    if extra_args:
        cmd += extra_args

    print("[train] running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd="/root/maira_ddatr", check=True)
    runs_vol.commit()
    print(f"[train] done -> {out_dir}")


# --------------------------------------------------------------------------- #
#  Local orchestration
# --------------------------------------------------------------------------- #
@app.local_entrypoint()
def run_training(manifest: str = "../train_pairs_ulcx.jsonl"):
    """modal run modal_app.py::run_training --manifest ../train_pairs_ulcx.jsonl

    Rewrites the manifest to the Volume mount, then launches training.
    """
    with open(manifest) as f:
        raw = f.read()
    rewritten = rewrite.remote(raw)          # repoint image paths at /data
    train.remote(rewritten)
