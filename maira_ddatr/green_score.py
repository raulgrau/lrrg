#!/usr/bin/env python3
"""
green_score.py -- GREEN (Generative Radiology Report Evaluation) scoring of a
predictions JSON (as written by infer.py / baseline_infer.py). GREEN is itself a
~7B model that reads (reference, generated) and emits a clinically-grounded score
in [0,1] plus an error analysis, so this needs a GPU.

Writes green_<name>.json with the per-case scores and the mean by stratum
(overall / change / no-change), matching how score_single.py stratifies.

Resumable: scores in chunks and re-loads completed chunks from a progress sidecar,
so a killed container continues rather than restarting the (slow) 7B pass.

    python green_score.py --preds preds_A1_full.json --out_json green_A1_full.json

NOTE (confirm on first run): the GREEN package API and model id have drifted across
releases. This uses the StanfordAIMI green_score package; if the constructor/call
signature differs in your install, the smoke run (--limit 5) surfaces it cheaply.
"""

from __future__ import annotations

import argparse
import json
import os


def _load_preds(path):
    data = json.load(open(path))
    if isinstance(data, dict):                       # --flat {sid: text}
        return [{"study_id": k, "generated": v, "reference": None, "change_label": None}
                for k, v in data.items()]
    return data


def _is_change(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "change", "yes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True)
    ap.add_argument("--out_json", required=True)
    ap.add_argument("--model_id", default="StanfordAIMI/GREEN-radllama2-7b")
    ap.add_argument("--batch_size", type=int, default=8)
    ap.add_argument("--chunk", type=int, default=200, help="cases per resumable chunk")
    ap.add_argument("--limit", type=int, default=0, help="cap cases (0 = all); smoke test")
    args = ap.parse_args()

    recs = _load_preds(args.preds)
    if args.limit:
        recs = recs[: args.limit]
    # only score cases that have a reference to compare against
    recs = [r for r in recs if (r.get("reference") or "").strip()]
    n = len(recs)
    print(f"[green] {n} cases with references from {args.preds}", flush=True)

    from green_score import GREEN
    green = GREEN(args.model_id, do_sample=False, batch_size=args.batch_size,
                  return_0_if_no_green_score=True)

    # resumable sidecar: {study_id: green_score}
    prog_path = args.out_json + ".progress.json"
    done = {}
    if os.path.exists(prog_path):
        done = json.load(open(prog_path))
        print(f"[green] resuming: {len(done)} cases already scored", flush=True)

    for lo in range(0, n, args.chunk):
        chunk = [r for r in recs[lo: lo + args.chunk] if str(r["study_id"]) not in done]
        if not chunk:
            continue
        refs = [r["reference"] for r in chunk]
        hyps = [r.get("generated") or "" for r in chunk]
        # GREEN returns (mean, std, per_case_scores, summary, df)
        _, _, scores, _, _ = green(refs=refs, hyps=hyps)
        for r, s in zip(chunk, scores):
            done[str(r["study_id"])] = float(s)
        json.dump(done, open(prog_path, "w"))
        print(f"[green] {min(lo + args.chunk, n)}/{n} scored", flush=True)

    # aggregate by stratum
    import statistics as st
    by = {"overall": [], "change": [], "no-change": []}
    for r in recs:
        s = done.get(str(r["study_id"]))
        if s is None:
            continue
        by["overall"].append(s)
        c = _is_change(r.get("change_label"))
        if c is True:
            by["change"].append(s)
        elif c is False:
            by["no-change"].append(s)

    out = {"preds": os.path.basename(args.preds), "model_id": args.model_id,
           "n": len(by["overall"]),
           "green": {k: (st.mean(v) if v else None) for k, v in by.items()},
           "n_by_stratum": {k: len(v) for k, v in by.items()},
           "per_case": done}
    json.dump(out, open(args.out_json, "w"), indent=2)
    g = out["green"]
    print(f"[green] done -> {args.out_json}")
    print(f"[green] mean GREEN  overall={g['overall']}  change={g['change']}  "
          f"no-change={g['no-change']}")


if __name__ == "__main__":
    main()
