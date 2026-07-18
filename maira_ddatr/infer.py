"""
Inference for MAIRA-2 + DDaTR -> score.py-compatible JSON.

Loads a trained checkpoint (the trainable DDaTR/LoRA/projector weights from
train.py), generates Findings for every pair in an eval manifest, and writes a
JSON array of per-study records:

    [{"study_id", "generated", "reference", "has_prior", "change_label"}, ...]

This carries `change_label` and `has_prior` straight through so your existing
score.py can stratify (change vs no-change) without a second join. If your
score.py wants a flat {study_id: findings} dict instead, pass --flat.

Resumable: re-running appends only studies not already in --out_json, so an
interrupted pass (tmux drop) is cheap to finish.

  python infer.py \
    --eval_manifest /path/ulcx_test.jsonl \
    --image_root /graphics/scratch2/.../MIMIC-CXR-JPG \
    --ckpt runs/m1/ckpt.pt --injection M1 \
    --out_json preds/m1_test.json
"""

from __future__ import annotations

import argparse
import json
import os


def _load_done(out_json: str) -> dict:
    if not os.path.exists(out_json):
        return {}
    with open(out_json) as f:
        data = json.load(f)
    if isinstance(data, dict):                       # --flat form
        return {k: {"study_id": k, "generated": v} for k, v in data.items()}
    return {r["study_id"]: r for r in data}


def _dump(records: dict, out_json: str, flat: bool):
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    tmp = out_json + ".tmp"
    if flat:
        payload = {sid: r["generated"] for sid, r in records.items()}
    else:
        payload = list(records.values())
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, out_json)                         # atomic; survives a kill mid-write


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval_manifest", required=True)
    ap.add_argument("--image_root", default="")
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out_json", required=True)
    ap.add_argument("--injection", default="M1")
    ap.add_argument("--prior_image_mode", default="keep_as_tokens",
                    choices=["keep_as_tokens", "strip_to_encoder_only"])
    ap.add_argument("--text_encoder", default="bert-base-uncased")
    ap.add_argument("--lora_r", type=int, default=16)
    ap.add_argument("--max_new_tokens", type=int, default=256)
    ap.add_argument("--num_beams", type=int, default=1)
    ap.add_argument("--flat", action="store_true",
                    help="write {study_id: findings} instead of records")
    ap.add_argument("--save_every", type=int, default=50)
    ap.add_argument("--num_workers", type=int, default=4,
                    help="DataLoader workers (spawn context; safe after CUDA init). "
                         "0 = serial. Use 6-8 when images are on a slow/network FS.")
    args = ap.parse_args()

    import torch
    from torch.utils.data import DataLoader
    from maira2_ddatr_model import build_model, ddatr_generate
    from data import LongitudinalPairDataset, DDaTRCollator
    from train import load_checkpoint

    device = "cuda"
    injection = ([int(x) for x in args.injection.split(",")]
                 if "," in args.injection else args.injection)

    bundle = build_model(
        injection=injection,
        prior_image_mode=args.prior_image_mode,
        text_encoder_name=args.text_encoder,
        lora_r=args.lora_r,
        device=device,
    )
    load_checkpoint(bundle, args.ckpt, strict=False)
    bundle.model.eval()
    bundle.injected.eval()

    ds = LongitudinalPairDataset(args.eval_manifest, image_root=args.image_root,
                                 require_findings=False)
    collate = DDaTRCollator(processor=bundle.processor,
                            text_tokenizer=bundle.text_encoder.tokenizer,
                            is_train=False, pixel_dtype=torch.bfloat16,
                            prior_image_mode=args.prior_image_mode,
                            image_token_index=bundle.spec.image_token_index)
    # spawn context: fork after CUDA init (model already loaded above) can
    # silently deadlock -- workers never come up, loop hangs on batch 0.
    loader_kwargs = dict(batch_size=1, shuffle=False, collate_fn=collate, pin_memory=True)
    if args.num_workers > 0:
        import multiprocessing as mp
        loader_kwargs.update(num_workers=args.num_workers,
                             multiprocessing_context=mp.get_context("spawn"),
                             persistent_workers=True, prefetch_factor=4)
    else:
        loader_kwargs["num_workers"] = 0
    loader = DataLoader(ds, **loader_kwargs)

    records = _load_done(args.out_json)
    print(f"[infer] {len(ds)} studies | {len(records)} already done -> resuming")

    # the collator drops study_id/change_label into the sample; keep manifest refs too
    done_since = 0
    for i, sample in enumerate(loader):
        sid = sample["study_id"]
        if sid in records:
            continue
        text = ddatr_generate(bundle, sample, device=device,
                              max_new_tokens=args.max_new_tokens, num_beams=args.num_beams)
        rec = {"study_id": sid, "generated": text,
               "has_prior": int(sample["has_prior"].item()),
               "change_label": sample.get("change_label")}
        # reference findings (if the eval manifest carries them) for convenience
        ref = ds.records[i]
        from data import _get
        rec["reference"] = _get(ref, "findings")
        records[sid] = rec
        done_since += 1

        if done_since % args.save_every == 0:
            _dump(records, args.out_json, args.flat)
            print(f"  {len(records)}/{len(ds)} written", flush=True)

    _dump(records, args.out_json, args.flat)
    print(f"[done] wrote {len(records)} studies -> {args.out_json}")


if __name__ == "__main__":
    main()
