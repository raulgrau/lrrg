"""
baseline_infer.py -- base MAIRA-2 predictions (NO DDaTR) on the test split, with
the prior supplied via MAIRA-2's NATIVE late fusion (prior frontal + prior report
in the prompt). Output is the SAME JSON schema as infer.py, so it drops straight
into score_single.py --baseline for the paired DDaTR-vs-baseline comparison.

The comparison this enables
---------------------------
DDaTR-M1 (strip mode): prior REPORT in the prompt + fed to DFAM; prior IMAGE
    reaches the model ONLY through the encoder fusion (not the LLM tokens).
baseline (here):       prior report AND prior image both in the prompt (native
    late fusion); no DDaTR.
So the manipulated variable is HOW the prior image informs generation --
encoder-level difference-aware fusion vs the LLM's own late fusion. Everything
else (context fields, prior report availability) is held identical because both
paths load items through the SAME LongitudinalPairDataset / FIELD_MAP.

Runs on a modest GPU (7B bf16 ~14GB); no QLoRA/bitsandbytes needed.

    python baseline_infer.py --eval_manifest test.jsonl --out_json base.json
"""

from __future__ import annotations

import argparse
import json
import os


def _load_done(out_json: str) -> dict:
    if not os.path.exists(out_json):
        return {}
    data = json.load(open(out_json))
    if isinstance(data, dict):
        return {k: {"study_id": k, "generated": v} for k, v in data.items()}
    return {str(r["study_id"]): r for r in data}


def _dump(records: dict, out_json: str):
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    tmp = out_json + ".tmp"
    json.dump(list(records.values()), open(tmp, "w"), indent=2)
    os.replace(tmp, out_json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval_manifest", required=True)
    ap.add_argument("--image_root", default="")
    ap.add_argument("--out_json", required=True)
    ap.add_argument("--model_id", default="microsoft/maira-2")
    ap.add_argument("--max_new_tokens", type=int, default=256)
    ap.add_argument("--save_every", type=int, default=50)
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor
    # reuse the EXACT dataset + field mapping the DDaTR eval uses, so context
    # (indication/technique/comparison, prior report, change_label) is identical
    from data import LongitudinalPairDataset, _get

    device = "cuda"
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(f"[baseline] loading {args.model_id} ({dtype}) ...", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id, trust_remote_code=True, torch_dtype=dtype).eval().to(device)
    processor = AutoProcessor.from_pretrained(args.model_id, trust_remote_code=True)

    ds = LongitudinalPairDataset(args.eval_manifest, image_root=args.image_root,
                                 require_findings=False)
    records = _load_done(args.out_json)
    print(f"[baseline] {len(ds)} studies | {len(records)} already done -> resuming", flush=True)

    done_since = 0
    for i in range(len(ds)):
        item = ds[i]
        sid = str(item["study_id"])
        if sid in records:
            continue

        # prior via native late fusion: pass prior_frontal + prior_report to the
        # processor (image_and_report mode). Held identical to the DDaTR eval's
        # context fields.
        inputs = processor.format_and_preprocess_reporting_input(
            current_frontal=item["current_frontal"],
            current_lateral=None,
            prior_frontal=item["prior_frontal"],       # native late fusion of the prior image
            indication=item.get("indication"),
            technique=item.get("technique"),
            comparison=item.get("comparison"),
            prior_report=item.get("prior_report"),
            return_tensors="pt",
            get_grounding=False,
        ).to(device)

        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, use_cache=True)
        plen = inputs["input_ids"].shape[-1]
        txt = processor.decode(out[0][plen:], skip_special_tokens=True).lstrip()
        txt = processor.convert_output_to_plaintext_or_grounded_sequence(txt)

        records[sid] = {
            "study_id": sid,
            "generated": txt,
            "has_prior": int(bool(item["has_prior"])),
            "change_label": _get(ds.records[i], "change_label"),
            "reference": _get(ds.records[i], "findings"),
        }
        done_since += 1
        if done_since % args.save_every == 0:
            _dump(records, args.out_json)
            print(f"  {len(records)}/{len(ds)} written", flush=True)

    _dump(records, args.out_json)
    print(f"[done] wrote {len(records)} studies -> {args.out_json}")


if __name__ == "__main__":
    main()
