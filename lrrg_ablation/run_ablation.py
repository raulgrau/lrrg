#!/usr/bin/env python3
"""
run_ablation.py  —  Zero-shot prior-conditioning ablation with MAIRA-2.

For each case in subset.jsonl, MAIRA-2 generates the Findings twice:
  * WITHOUT prior : current frontal only (prior_report=None, prior_frontal=None)
  * WITH prior    : same, plus prior_report (+ prior_frontal in image_and_report mode)

Only the prior is toggled. indication is held constant across both arms;
technique=None and comparison="None." are held constant to avoid leaking the
existence of a prior through the current-study sections. This isolates the
prior report/image as the single manipulated variable.

Access: MAIRA-2 is gated but instant-grant — visit
https://huggingface.co/microsoft/maira-2 while logged in, tick the disclaimer,
then `huggingface-cli login` (or set HF_TOKEN) on the box.

Example:
    python run_ablation.py --subset subset.jsonl --out predictions.csv \
        --prior-mode report_only --limit 40
"""

import argparse
import csv
import json
import time
import os 

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

MODEL_ID = "microsoft/maira-2"


def load_image(path):
    # MIMIC JPGs are single-channel; RAD-DINO expects 3 channels.
    return Image.open(path).convert("RGB")


def generate(processor, model, device, rec, use_prior, prior_mode, max_new_tokens):
    prior_report = None
    prior_frontal = None
    if use_prior:
        prior_report = (rec.get("prior_findings") or "").strip() or None
        if prior_mode == "image_and_report" and rec.get("prior_image"):
            prior_frontal = load_image(rec["prior_image"])

    indication = (rec.get("indication") or "").strip() or None

    inputs = processor.format_and_preprocess_reporting_input(
        current_frontal=load_image(rec["current_image"]),
        current_lateral=None,
        prior_frontal=prior_frontal,
        indication=indication,     # held constant across arms
        technique=None,            # held constant
        comparison="None.",        # held constant (neutralised)
        prior_report=prior_report, # <-- the manipulated variable
        return_tensors="pt",
        get_grounding=False,
    ).to(device)

    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, use_cache=True)
    plen = inputs["input_ids"].shape[-1]
    txt = processor.decode(out[0][plen:], skip_special_tokens=True).lstrip()
    return processor.convert_output_to_plaintext_or_grounded_sequence(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", default="subset.jsonl")
    ap.add_argument("--out", default="predictions.csv")
    ap.add_argument("--prior-mode", choices=["report_only", "image_and_report"],
                    default="report_only")
    ap.add_argument("--limit", type=int, default=0, help="0 = all cases")
    ap.add_argument("--max-new-tokens", type=int, default=300)
    ap.add_argument("--overwrite", action="store_true",
                    help="ignore any existing output and start fresh")
    args = ap.parse_args()

    cases = [json.loads(l) for l in open(args.subset) if l.strip()]
    if args.limit:
        cases = cases[: args.limit]

    # ---- resume: skip cases already in the output CSV ----
    done = set()
    header = ["subject_id", "current_study_id", "prior_study_id",
              "reference", "pred_without_prior", "pred_with_prior", "change"]
    if os.path.exists(args.out) and not args.overwrite:
        with open(args.out, newline="") as f:
            for row in csv.DictReader(f):
                done.add(str(row["current_study_id"]))
        print(f"Resuming: {len(done)} cases already done in {args.out}.")
    todo = [c for c in cases if str(c["current_study_id"]) not in done]
    print(f"{len(cases)} total, {len(todo)} to generate.")
    if not todo:
        print("Nothing to do.")
        return

    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading {MODEL_ID} ({dtype}) on {device} ...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, trust_remote_code=True, torch_dtype=dtype
    ).eval().to(device)
    processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)

    fresh = args.overwrite or not os.path.exists(args.out) or os.path.getsize(args.out) == 0
    fout = open(args.out, "w" if fresh else "a", newline="")
    writer = csv.writer(fout)
    if fresh:
        writer.writerow(header)

    t0 = time.time()
    for i, rec in enumerate(todo, 1):
        try:
            wo = generate(processor, model, device, rec, False,
                          args.prior_mode, args.max_new_tokens)
            wi = generate(processor, model, device, rec, True,
                          args.prior_mode, args.max_new_tokens)
        except Exception as e:
            print(f"  [skip {rec.get('current_study_id')}] {e}")
            continue
        writer.writerow([rec["subject_id"], rec["current_study_id"],
                         rec["prior_study_id"], rec["reference_findings"], wo, wi,
                         int(bool(rec.get("change")))])
        fout.flush()
        if i % 25 == 0 or i == len(todo):
            dt = time.time() - t0
            rate = dt / i
            eta = rate * (len(todo) - i)
            print(f"  {i}/{len(todo)}  ({rate:.1f}s/case, elapsed {dt/60:.1f}m, "
                  f"ETA {eta/60:.0f}m)")

    fout.close()
    print(f"Done -> {args.out}")


if __name__ == "__main__":
    main()
