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
    # NOTE: GREEN (green_score) is intentionally NOT installed here -- it transitively
    # requires a scipy that only builds on Python 3.12+, incompatible with this 3.11
    # image. Running GREEN needs a separate 3.12 image (deferred to August on the 3090).
    # The green()/run_green entrypoints below stay for that future image.
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
    cpu=8.0,                      # cores for the DataLoader workers (Volume reads
                                  # + MAIRA-2 preprocessing) -- needed to hide the
                                  # network-filesystem data-load latency behind GPU
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
    num_workers: int = 6,                 # parallel prefetch over the Volume
    smoke: bool = False,                  # short profiled run to validate the chain
    extra_args: list[str] | None = None,
):
    import subprocess

    # HF auth for gated MAIRA-2 (never export a stale HF_TOKEN elsewhere)
    os.environ.setdefault("HF_HOME", os.path.join(DATA_MOUNT, "hf"))

    # write the (already-rewritten) manifest into the container
    manifest_path = "/root/train_pairs_modal.jsonl"
    with open(manifest_path, "w") as f:
        f.write(train_manifest_text)

    # smoke: a throwaway ~40-step profiled run to prove image build + Volume
    # mount + MAIRA-2 load + real steps, and print the true per-sample time on
    # this GPU -- before committing to the full ~10-16h epoch. Never checkpoints.
    # include injection in the run name so M1 / M2 / none-baseline checkpoints
    # never overwrite each other on the Volume.
    tag = str(injection).replace(",", "-")
    out_dir = os.path.join(RUNS_MOUNT, "smoke" if smoke else f"{tag}_{prior_image_mode}")
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
        "--save_every", str(1_000_000 if smoke else save_every),
        "--num_workers", str(num_workers),
    ]
    if no_grad_checkpointing:
        cmd.append("--no_grad_checkpointing")
    if smoke:
        cmd += ["--max_steps", "40", "--profile", "--profile_steps", "40", "--log_every", "4"]
    if not smoke and os.path.exists(resume):
        cmd += ["--resume", resume]
        print(f"[train] resuming from {resume}")
    if extra_args:
        cmd += extra_args

    print("[train] running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd="/root/maira_ddatr", check=True)
    runs_vol.commit()
    print(f"[train] done -> {out_dir}")


# --------------------------------------------------------------------------- #
#  3. Infer  (wraps the EXISTING infer.py; generates DDaTR predictions JSON)
# --------------------------------------------------------------------------- #
@app.function(
    gpu="A100-80GB",
    volumes={DATA_MOUNT: data_vol, RUNS_MOUNT: runs_vol},
    secrets=[hf_secret],
    timeout=6 * 60 * 60,          # ~2k pairs of autoregressive decode; resumable
    cpu=8.0,
)
def infer(
    eval_manifest_text: str,
    injection: str = "M1",
    prior_image_mode: str = "strip_to_encoder_only",   # MUST match the trained ckpt
    ckpt_name: str = "ckpt.pt",
    out_name: str = "preds_test.json",
    max_new_tokens: int = 256,
    num_workers: int = 6,
    limit: int = 0,
):
    import subprocess

    os.environ.setdefault("HF_HOME", os.path.join(DATA_MOUNT, "hf"))

    manifest_path = f"/root/eval_{out_name}.jsonl"   # unique per arm (parallel-safe)
    with open(manifest_path, "w") as f:
        f.write(eval_manifest_text)

    # the trained checkpoint lives where train.py wrote it (same tagging scheme)
    tag = str(injection).replace(",", "-")
    run_dir = os.path.join(RUNS_MOUNT, f"{tag}_{prior_image_mode}")
    ckpt = os.path.join(run_dir, ckpt_name)
    if not os.path.exists(ckpt):
        raise FileNotFoundError(
            f"checkpoint not found: {ckpt}\n  (train first, or pass the right "
            f"prior_image_mode / ckpt_name)")
    out_json = os.path.join(run_dir, out_name)

    cmd = [
        "python", "infer.py",
        "--eval_manifest", manifest_path,
        "--ckpt", ckpt,
        "--out_json", out_json,
        "--injection", injection,
        "--prior_image_mode", prior_image_mode,
        "--max_new_tokens", str(max_new_tokens),
        "--num_workers", str(num_workers),
    ]
    if limit:
        cmd += ["--limit", str(limit)]
    print("[infer] running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd="/root/maira_ddatr", check=True)
    runs_vol.commit()
    print(f"[infer] wrote {out_json}  (pull with: modal volume get lrrg-runs "
          f"{out_json.replace(RUNS_MOUNT, '').lstrip('/')} .)")


# --------------------------------------------------------------------------- #
#  4. Baseline  (base MAIRA-2, no DDaTR) -- the comparison point, on a cheap GPU
# --------------------------------------------------------------------------- #
@app.function(
    gpu="L4",                     # 24GB, ~1/3 the price of A100-80GB; 7B bf16 fits
    volumes={DATA_MOUNT: data_vol, RUNS_MOUNT: runs_vol},
    secrets=[hf_secret],
    timeout=8 * 60 * 60,          # L4 is slower per token; resumable, so safe
    cpu=8.0,
)
def baseline(
    eval_manifest_text: str,
    out_name: str = "preds_baseline.json",
    out_subdir: str = "m1_strip_to_encoder_only",
    max_new_tokens: int = 256,
    limit: int = 0,
):
    import subprocess

    os.environ.setdefault("HF_HOME", os.path.join(DATA_MOUNT, "hf"))

    manifest_path = f"/root/eval_{out_name}.jsonl"   # unique per arm (parallel-safe)
    with open(manifest_path, "w") as f:
        f.write(eval_manifest_text)

    out_dir = os.path.join(RUNS_MOUNT, out_subdir)
    os.makedirs(out_dir, exist_ok=True)
    out_json = os.path.join(out_dir, out_name)

    cmd = [
        "python", "baseline_infer.py",
        "--eval_manifest", manifest_path,
        "--out_json", out_json,
        "--max_new_tokens", str(max_new_tokens),
    ]
    if limit:
        cmd += ["--limit", str(limit)]
    print("[baseline] running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd="/root/maira_ddatr", check=True)
    runs_vol.commit()
    print(f"[baseline] wrote {out_json}  (pull with: modal volume get lrrg-runs "
          f"{out_json.replace(RUNS_MOUNT, '').lstrip('/')} .)")


# --------------------------------------------------------------------------- #
#  5. GREEN scoring  (7B generative metric -- GPU-bound, the last credits-buy)
# --------------------------------------------------------------------------- #
@app.function(
    gpu="A100-80GB",              # GREEN is 7B + generates per pair; A100 keeps it moving
    volumes={DATA_MOUNT: data_vol, RUNS_MOUNT: runs_vol},
    secrets=[hf_secret],
    timeout=12 * 60 * 60,         # slow; resumable per-chunk, so safe
    cpu=8.0,
)
def green(pred_rel_paths: list[str], smoke: bool = False):
    """Score each predictions JSON with GREEN, in ONE container (model loaded once).

    pred_rel_paths: paths relative to the lrrg-runs Volume, e.g.
        ["battery/preds_A1_full.json", "m1_strip_to_encoder_only/preds_test.json"]
    Writes green_<name>.json next to each. Sequential on purpose -- one 7B load,
    reused across all files; resumable per chunk so a restart continues.
    """
    import subprocess

    os.environ.setdefault("HF_HOME", os.path.join(DATA_MOUNT, "hf"))
    out_dir = os.path.join(RUNS_MOUNT, "green")
    os.makedirs(out_dir, exist_ok=True)

    for rel in pred_rel_paths:
        src = os.path.join(RUNS_MOUNT, rel)
        if not os.path.exists(src):
            print(f"[green] SKIP missing {src}", flush=True)
            continue
        name = os.path.splitext(os.path.basename(rel))[0]
        out_json = os.path.join(out_dir, f"green_{name}.json")
        cmd = ["python", "green_score.py", "--preds", src, "--out_json", out_json]
        if smoke:
            cmd += ["--limit", "5"]
        print(f"[green] scoring {rel}", flush=True)
        subprocess.run(cmd, cwd="/root/maira_ddatr", check=True)
        runs_vol.commit()
    print(f"[green] done -> /runs/green  (pull: modal volume get lrrg-runs green .)")


# --------------------------------------------------------------------------- #
#  Local orchestration
# --------------------------------------------------------------------------- #
@app.local_entrypoint()
def run_training(manifest: str = "../train_pairs_ulcx.jsonl", smoke: bool = False,
                 injection: str = "M1",
                 prior_image_mode: str = "strip_to_encoder_only",
                 no_grad_checkpointing: bool = True):
    """Rewrite the manifest to the Volume mount, then launch training.

    M1 (done) reference:
        modal run --detach modal_app.py::run_training --injection M1
    M2 (multi-scale, strip mode):
        modal run --detach modal_app.py::run_training --injection M2
    Fine-tuned no-DDaTR baseline (native late fusion -> keep_as_tokens):
        modal run --detach modal_app.py::run_training \\
            --injection none --prior-image-mode keep_as_tokens

    Smoke-test any config first (minutes, prints per-sample time):
        modal run modal_app.py::run_training --smoke --injection M2
    """
    with open(manifest) as f:
        raw = f.read()
    rewritten = rewrite.remote(raw)          # repoint image paths at /data
    train.remote(rewritten, smoke=smoke, injection=injection,
                 prior_image_mode=prior_image_mode,
                 no_grad_checkpointing=no_grad_checkpointing)


@app.local_entrypoint()
def run_inference(manifest: str = "../test_pairs_ulcx.jsonl",
                  injection: str = "M1",
                  prior_image_mode: str = "strip_to_encoder_only",
                  out_name: str = "preds_test.json"):
    """Generate predictions on the test split from a trained checkpoint.

    injection + prior_image_mode MUST match the run you want to evaluate:
        M2:        --injection M2  (out_name preds_m2.json)
        baseline:  --injection none --prior-image-mode keep_as_tokens (out_name preds_ftbaseline.json)
    Writes to the lrrg-runs Volume; pull it to cgpool for scoring.
    """
    with open(manifest) as f:
        raw = f.read()
    rewritten = rewrite.remote(raw)          # repoint image paths at /data
    infer.remote(rewritten, injection=injection, prior_image_mode=prior_image_mode,
                 out_name=out_name)


@app.local_entrypoint()
def run_baseline(manifest: str = "../test_pairs_ulcx.jsonl"):
    """Generate base MAIRA-2 (no DDaTR) predictions on the test split, on an L4.

        modal run modal_app.py::run_baseline

    Writes preds_baseline.json to the lrrg-runs Volume. Then, on cgpool:
        score_single.py --preds preds_test.json --baseline preds_baseline.json
    """
    with open(manifest) as f:
        raw = f.read()
    rewritten = rewrite.remote(raw)          # repoint image paths at /data
    baseline.remote(rewritten)


@app.local_entrypoint()
def run_battery(manifest_dir: str = "../battery_manifests", smoke: bool = False):
    """Counterfactual-prior battery: base MAIRA-2 inference on every arm.

    Smoke first (5 cases/arm -- verifies A2's blank-report path and that all
    substituted images resolve on the Volume, before spending real credits):
        modal run modal_app.py::run_battery --smoke

    Then the full fan-out (all 8 arms, in PARALLEL containers, ~1-1.5h each):
        modal run modal_app.py::run_battery

    Writes preds_A0.json ... preds_A7.json to /runs/battery on the lrrg-runs Volume.
    """
    import glob
    import os as _os

    arms = sorted(glob.glob(_os.path.join(manifest_dir, "A*.jsonl")))
    if not arms:
        raise SystemExit(f"no arm manifests in {manifest_dir} "
                         f"(run make_battery_manifests.py first)")
    limit = 5 if smoke else 0
    print(f"[battery] {len(arms)} arms, {'SMOKE (5/arm)' if smoke else 'full'}")

    calls = []
    for arm_path in arms:
        arm = _os.path.splitext(_os.path.basename(arm_path))[0]     # e.g. A3_wrong_patient
        with open(arm_path) as f:
            rewritten = rewrite.remote(f.read())   # repoint image paths at /data
        # spawn -> all arms run in parallel on separate containers
        calls.append((arm, baseline.spawn(
            rewritten, out_name=f"preds_{arm}.json",
            out_subdir="battery_smoke" if smoke else "battery", limit=limit)))

    print(f"[battery] launched {len(calls)} arms; waiting ...")
    for arm, c in calls:
        c.get()
        print(f"  [done] {arm}")
    print("[battery] all arms complete -> /runs/"
          f"{'battery_smoke' if smoke else 'battery'}  "
          "(pull: modal volume get lrrg-runs battery .)")


@app.local_entrypoint()
def run_battery_ckpt(injection: str = "none",
                     prior_image_mode: str = "keep_as_tokens",
                     manifest_dir: str = "../battery_manifests", smoke: bool = False):
    """Run the SAME counterfactual battery on a TRAINED checkpoint (not base MAIRA-2),
    turning the audit into a multi-model comparison: does fine-tuning / encoder fusion
    change HOW the model uses the prior?

    Fine-tuned no-DDaTR baseline (native late fusion):
        modal run --detach modal_app.py::run_battery_ckpt --injection none --prior-image-mode keep_as_tokens
    DDaTR M2 (multi-scale, strip):
        modal run --detach modal_app.py::run_battery_ckpt --injection M2 --prior-image-mode strip_to_encoder_only

    Writes preds_A*_<arm>.json into the checkpoint's run dir (e.g. none_keep_as_tokens/).
    Smoke first with --smoke (5 cases/arm).
    """
    import glob
    import os as _os

    arms = sorted(glob.glob(_os.path.join(manifest_dir, "A*.jsonl")))
    if not arms:
        raise SystemExit(f"no arm manifests in {manifest_dir}")
    limit = 5 if smoke else 0
    tag = str(injection).replace(",", "-")
    print(f"[battery-ckpt] {len(arms)} arms on {tag}_{prior_image_mode}"
          f"{' (SMOKE)' if smoke else ''}")

    calls = []
    for arm_path in arms:
        arm = _os.path.splitext(_os.path.basename(arm_path))[0]
        with open(arm_path) as f:
            rewritten = rewrite.remote(f.read())
        calls.append((arm, infer.spawn(
            rewritten, injection=injection, prior_image_mode=prior_image_mode,
            out_name=f"battery_{arm}.json", limit=limit)))

    print(f"[battery-ckpt] launched {len(calls)} arms; waiting ...")
    for arm, c in calls:
        c.get()
        print(f"  [done] {arm}")
    print(f"[battery-ckpt] complete -> /runs/{tag}_{prior_image_mode}/battery_A*.json")


# Default GREEN targets: the prediction sets the report's tables actually need --
# battery headline arms + the three DDaTR arms. Extend if credits allow.
GREEN_DEFAULT = [
    "battery/preds_A0_no_prior.json",
    "battery/preds_A1_full.json",
    "battery/preds_A2_image_only.json",
    "battery/preds_A3_wrong_patient.json",
    "battery/preds_A4_img_ok_rep_wrong.json",
    "battery/preds_A5_img_wrong_rep_ok.json",
    "battery/preds_A6_dup_current.json",
    "m1_strip_to_encoder_only/preds_test.json",       # DDaTR M1
    "M2_strip_to_encoder_only/preds_m2.json",         # DDaTR M2
    "none_keep_as_tokens/preds_ftbaseline.json",      # fine-tuned baseline
]


@app.local_entrypoint()
def run_green(smoke: bool = False, files: str = ""):
    """GREEN-score prediction sets already on the Volume (one A100 container).

    Smoke first (5 cases/file -- verifies the GREEN package + model load cheaply):
        modal run modal_app.py::run_green --smoke

    Then the real pass (resumable, ~hours):
        modal run --detach modal_app.py::run_green

    --files "a.json,b.json" overrides the default target list (paths relative to
    the lrrg-runs Volume).
    """
    targets = [f.strip() for f in files.split(",") if f.strip()] or GREEN_DEFAULT
    print(f"[green] {len(targets)} prediction sets{' (SMOKE)' if smoke else ''}")
    green.remote(targets, smoke=smoke)
