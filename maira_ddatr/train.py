"""
QLoRA training loop for MAIRA-2 + DDaTR.

Trains ONLY: the DDaTR blocks (DFAM/DDAM/LDConv), the prior-text projection,
LoRA on Vicuna q/v, and (by default) the MAIRA-2 projector. Everything else
(RAD-DINO, BERT, Vicuna base in 4-bit) is frozen.

Recipe (matches the plan's 24 GB 3090 budget):
  * batch_size = 1 + gradient accumulation (effective 8-16)
  * 4-bit NF4 Vicuna, bf16 compute, gradient checkpointing
  * AdamW, lr ~1e-4 on adapters, warmup + cosine
  * resumable: checkpoints hold trainable weights + optim/sched/step, and
    `--resume <dir>` continues exactly where it stopped (run under tmux)

Run (M1 first):
  python train.py \
    --train_manifest /path/ulcx_train.jsonl \
    --image_root /graphics/scratch2/.../MIMIC-CXR-JPG \
    --out_dir runs/m1 --injection M1 --grad_accum 12 --epochs 1

Then M2:
  python train.py ... --out_dir runs/m2 --injection M2 --grad_accum 12

Optional auxiliary CheXbert-14 head (the plan's regulariser): NOT wired by
default. To add it once M1 plateaus, expose pooled current features from
DDaTRVisionMerger.forward (return `last[:, 0]` for the current frontal),
attach `nn.Linear(hidden_dim, 14*4)`, and add a BCE/CE term against the
current report's CheXbert-14 labels (carry them through FIELD_MAP).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time


# --------------------------------------------------------------------------- #
#  Checkpoint helpers: save/load ONLY the trainable params (+ optim/sched/step)
# --------------------------------------------------------------------------- #
def _trainable_named_params(bundle):
    """All requires_grad params across the three owning modules, deduped by id."""
    import itertools
    seen, named = set(), {}
    for prefix, mod in (("model", bundle.model),
                        ("injected", bundle.injected),
                        ("text", bundle.text_encoder)):
        for n, p in mod.named_parameters():
            if not p.requires_grad or id(p) in seen:
                continue
            seen.add(id(p))
            named[f"{prefix}.{n}"] = p
    return named


def save_checkpoint(bundle, optim, sched, step, out_dir, meta=None):
    import torch
    os.makedirs(out_dir, exist_ok=True)
    state = {k: v.detach().cpu() for k, v in _trainable_named_params(bundle).items()}
    torch.save(
        {"trainable": state,
         "optim": optim.state_dict() if optim is not None else None,
         "sched": sched.state_dict() if sched is not None else None,
         "step": step,
         "meta": meta or {}},
        os.path.join(out_dir, "ckpt.pt"))
    # also drop a tiny json so you can eyeball progress from the shell
    with open(os.path.join(out_dir, "progress.json"), "w") as f:
        json.dump({"step": step, "meta": meta or {}, "time": time.time()}, f, indent=2)


def load_checkpoint(bundle, ckpt_path, optim=None, sched=None, strict=True):
    import torch
    blob = torch.load(ckpt_path, map_location="cpu")
    named = _trainable_named_params(bundle)
    missing, unexpected = [], []
    for k, v in blob["trainable"].items():
        if k in named:
            with torch.no_grad():
                named[k].copy_(v.to(named[k].device, named[k].dtype))
        else:
            unexpected.append(k)
    for k in named:
        if k not in blob["trainable"]:
            missing.append(k)
    if strict and (missing or unexpected):
        raise RuntimeError(f"checkpoint mismatch: missing={missing[:4]}... "
                           f"unexpected={unexpected[:4]}...")
    if optim is not None and blob.get("optim") is not None:
        optim.load_state_dict(blob["optim"])
    if sched is not None and blob.get("sched") is not None:
        sched.load_state_dict(blob["sched"])
    print(f"[resume] loaded {len(named)} trainable tensors, step={blob.get('step')}")
    return blob.get("step", 0)


# --------------------------------------------------------------------------- #
#  Schedule: linear warmup -> cosine decay
# --------------------------------------------------------------------------- #
def cosine_with_warmup(optimizer, warmup_steps, total_steps, min_ratio=0.05):
    from torch.optim.lr_scheduler import LambdaLR

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        prog = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return min_ratio + (1 - min_ratio) * 0.5 * (1 + math.cos(math.pi * prog))

    return LambdaLR(optimizer, lr_lambda)


# --------------------------------------------------------------------------- #
#  Train
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train_manifest", required=True)
    ap.add_argument("--image_root", default="")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--injection", default="M1", help="M1 | M2 | comma-list e.g. 3,6,9,12")
    ap.add_argument("--prior_image_mode", default="keep_as_tokens",
                    choices=["keep_as_tokens", "strip_to_encoder_only"])
    ap.add_argument("--text_encoder", default="bert-base-uncased")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--max_steps", type=int, default=-1)
    ap.add_argument("--grad_accum", type=int, default=12)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--warmup_steps", type=int, default=200)
    ap.add_argument("--weight_decay", type=float, default=0.0)
    ap.add_argument("--grad_clip", type=float, default=1.0)
    ap.add_argument("--lora_r", type=int, default=16)
    ap.add_argument("--max_target_len", type=int, default=256)
    ap.add_argument("--save_every", type=int, default=500)
    ap.add_argument("--log_every", type=int, default=20)
    ap.add_argument("--require_prior", action="store_true",
                    help="train only on pairs that have a prior (sharpens the signal)")
    ap.add_argument("--resume", default="", help="path to ckpt.pt to continue from")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--profile", action="store_true",
                    help="time data-load/forward/backward/optim separately (adds "
                         "cuda.synchronize() calls -- diagnostic only, some overhead)")
    ap.add_argument("--profile_steps", type=int, default=40,
                    help="micro-steps to profile before printing and clearing (with --profile)")
    ap.add_argument("--no_grad_checkpointing", action="store_true",
                    help="disable gradient checkpointing entirely (faster, more VRAM; "
                         "test this first with --profile to see if it OOMs on your GPU)")
    ap.add_argument("--grad_checkpointing_reentrant", action="store_true",
                    help="use the legacy reentrant checkpoint impl instead of the newer, "
                         "usually-cheaper use_reentrant=False (default off)")
    ap.add_argument("--num_workers", type=int, default=0,
                    help="DataLoader workers (spawn context). 0 = serial (safe on a "
                         "local fast disk); use 6-8 when images are on a slow/network "
                         "filesystem like a Modal Volume to hide data loading behind compute")
    ap.add_argument("--prefetch_factor", type=int, default=4,
                    help="batches prefetched per worker (only used when num_workers>0)")
    args = ap.parse_args()

    import torch
    from torch.utils.data import DataLoader
    from maira2_ddatr_model import build_model, ddatr_step
    from data import LongitudinalPairDataset, DDaTRCollator

    torch.manual_seed(args.seed)
    device = "cuda"

    injection = ([int(x) for x in args.injection.split(",")]
                 if "," in args.injection else args.injection)

    bundle = build_model(
        injection=injection,
        prior_image_mode=args.prior_image_mode,
        text_encoder_name=args.text_encoder,
        lora_r=args.lora_r,
        device=device,
        use_gradient_checkpointing=not args.no_grad_checkpointing,
        grad_checkpointing_reentrant=args.grad_checkpointing_reentrant,
    )

    ds = LongitudinalPairDataset(args.train_manifest, image_root=args.image_root,
                                 require_prior=args.require_prior)
    collate = DDaTRCollator(processor=bundle.processor,
                            text_tokenizer=bundle.text_encoder.tokenizer,
                            is_train=True, max_target_len=args.max_target_len,
                            pixel_dtype=torch.bfloat16,
                            prior_image_mode=args.prior_image_mode,
                            image_token_index=bundle.spec.image_token_index)
    # Data loading is serial and can dominate when images live on a slow/network
    # filesystem (e.g. a Modal Volume: profiling showed data=66% of step time on
    # an A100, starving the GPU). num_workers>0 parallelizes the per-sample JPEG
    # reads + MAIRA-2 preprocessing and prefetches them behind the GPU compute.
    #
    # WHY spawn, not the default fork: model load (a few lines up) already put a
    # CUDA context in this process, and forking a CUDA-initialized process is a
    # classic silent-deadlock (workers never come up, first batch hangs forever).
    # The "spawn" start method sidesteps that -- workers start fresh, re-pickle
    # the dataset + processor, and never inherit the CUDA context. num_workers=0
    # keeps the old safe single-process path (good for a local GPU with fast disk).
    loader_kwargs = dict(batch_size=1, shuffle=True, collate_fn=collate, pin_memory=True)
    if args.num_workers > 0:
        import multiprocessing as mp
        loader_kwargs.update(
            num_workers=args.num_workers,
            multiprocessing_context=mp.get_context("spawn"),
            persistent_workers=True,          # don't re-spawn every epoch
            prefetch_factor=args.prefetch_factor,
        )
    else:
        loader_kwargs["num_workers"] = 0
    loader = DataLoader(ds, **loader_kwargs)

    trainable = list(_trainable_named_params(bundle).values())
    optim = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=args.weight_decay)

    steps_per_epoch = math.ceil(len(loader) / args.grad_accum)
    total_opt_steps = (args.max_steps if args.max_steps > 0
                       else steps_per_epoch * args.epochs)
    sched = cosine_with_warmup(optim, args.warmup_steps, total_opt_steps)

    start_opt_step = 0
    if args.resume:
        start_opt_step = load_checkpoint(bundle, args.resume, optim, sched, strict=False)

    print(f"[train] {len(ds)} pairs | {steps_per_epoch} opt-steps/epoch | "
          f"{total_opt_steps} total opt-steps | accum={args.grad_accum}")

    bundle.model.train()
    bundle.injected.train()
    opt_step = start_opt_step
    micro = 0
    running = 0.0
    optim.zero_grad(set_to_none=True)
    t0 = time.time()

    # --profile: attribute wall time to data-load / forward / backward / optim
    # separately. cuda.synchronize() makes each bucket honest (CUDA calls are
    # async otherwise -- without sync, time just piles up wherever you next
    # block, which is exactly the kind of misleading number that led to
    # optimizing the wrong end last time.
    prof = {"data": 0.0, "fwd": 0.0, "bwd": 0.0, "optim": 0.0}
    prof_n = 0
    data_t0 = time.time()

    for epoch in range(args.epochs):
        for sample in loader:
            if args.profile:
                torch.cuda.synchronize()
                prof["data"] += time.time() - data_t0

                t = time.time()
                loss = ddatr_step(bundle, sample, device=device)
                torch.cuda.synchronize()
                prof["fwd"] += time.time() - t

                t = time.time()
                (loss / args.grad_accum).backward()
                torch.cuda.synchronize()
                prof["bwd"] += time.time() - t
            else:
                loss = ddatr_step(bundle, sample, device=device)
                (loss / args.grad_accum).backward()
            running += loss.item()
            micro += 1
            prof_n += 1

            if micro % args.grad_accum == 0:
                if args.profile:
                    t = time.time()
                torch.nn.utils.clip_grad_norm_(trainable, args.grad_clip)
                optim.step()
                sched.step()
                optim.zero_grad(set_to_none=True)
                if args.profile:
                    torch.cuda.synchronize()
                    prof["optim"] += time.time() - t
                opt_step += 1

                if opt_step % args.log_every == 0:
                    avg = running / (args.grad_accum * args.log_every)
                    rate = (args.grad_accum * args.log_every) / (time.time() - t0)
                    print(f"  step {opt_step}/{total_opt_steps} "
                          f"loss {avg:.4f} lr {sched.get_last_lr()[0]:.2e} "
                          f"{rate:.2f} samp/s", flush=True)
                    running, t0 = 0.0, time.time()

                if opt_step % args.save_every == 0:
                    save_checkpoint(bundle, optim, sched, opt_step, args.out_dir,
                                    meta={"injection": args.injection,
                                          "prior_image_mode": args.prior_image_mode,
                                          "epoch": epoch})
                    print(f"  [ckpt] saved at opt-step {opt_step}", flush=True)

                if args.max_steps > 0 and opt_step >= args.max_steps:
                    save_checkpoint(bundle, optim, sched, opt_step, args.out_dir,
                                    meta={"injection": args.injection, "final": True})
                    print("[done] hit max_steps")
                    return

                # Stop at the planned total. On a RESUMED run, opt_step is
                # restored (e.g. 2500) but the dataloader restarts from the top of
                # the epoch, so without this guard the loop would run a FULL extra
                # epoch of steps (ending ~total+resume) at the LR-schedule floor.
                # opt_step counts cumulative updates, so total_opt_steps updates =
                # one epoch's worth of optimization regardless of restarts.
                if args.max_steps <= 0 and opt_step >= total_opt_steps:
                    save_checkpoint(bundle, optim, sched, opt_step, args.out_dir,
                                    meta={"injection": args.injection, "final": True})
                    print(f"[done] reached total_opt_steps ({total_opt_steps})")
                    return

            if args.profile and prof_n >= args.profile_steps:
                total = sum(prof.values()) or 1e-9
                print(f"  [profile] over {prof_n} micro-steps (s/sample, % of total):")
                for k, v in prof.items():
                    print(f"    {k:6s} {v/prof_n:.3f}s/samp  ({100*v/total:.1f}%)")
                prof = {k: 0.0 for k in prof}
                prof_n = 0

            data_t0 = time.time()

    save_checkpoint(bundle, optim, sched, opt_step, args.out_dir,
                    meta={"injection": args.injection, "final": True})
    print("[done] training complete")


if __name__ == "__main__":
    main()
