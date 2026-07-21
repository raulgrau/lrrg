#!/usr/bin/env python
"""
Draw an unbiased random sample of cases and render baseline (MAIRA-2 draft)
against the ICL pipeline's output, side by side with the ground-truth report.

Distinct from show_examples.py, which deliberately picks cases by guardrail
outcome (accepted / rejected / no-op) to illustrate mechanics. That selection
is fine for explaining how the pipeline behaves but useless for judging
typical quality, because it is biased by construction. This script samples at
random with a fixed seed, optionally stratified by the manifest's change flag,
so what you read is representative of the population.

"Approach" is ambiguous in this project because three guardrail variants exist,
so it is selectable:

    --variant none      pred = revised_text   (revision applied unconditionally;
                                               this is the honest, uncontaminated
                                               comparison -- see summary.md)
    --variant chexbert  pred = final_text     (as originally run: CheXbert-F1 gate)
    --variant radgraph  pred = final_text from icl_final_radgraph_guardrail.jsonl
                                              (requires --radgraph-jsonl)

Default is `none`, because that is the variant the write-up treats as the real
result; the gated variants are oracles and their outputs cannot be produced at
inference time.

Usage:
    python sample_vs_baseline.py --n 12 --out sample_vs_baseline.md
    python sample_vs_baseline.py --n 20 --stratify --variant radgraph \
        --radgraph-jsonl icl_final_radgraph_guardrail.jsonl
"""
import argparse
import difflib
import json
import random
import textwrap
from pathlib import Path

from config import PATHS
from temporal_utils import is_comparison_sentence, split_sentences


def load_jsonl(path: Path) -> list:
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def word_diff(old: str, new: str) -> str:
    o, n = old.split(), new.split()
    sm = difflib.SequenceMatcher(a=o, b=n)
    parts = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(" ".join(o[i1:i2]))
        elif tag == "delete":
            parts.append(f"[-{' '.join(o[i1:i2])}-]")
        elif tag == "insert":
            parts.append(f"{{+{' '.join(n[j1:j2])}+}}")
        elif tag == "replace":
            parts.append(f"[-{' '.join(o[i1:i2])}-] {{+{' '.join(n[j1:j2])}+}}")
    return " ".join(parts)


def changed_sentences(baseline: str, pred: str):
    b, p = split_sentences(baseline), split_sentences(pred)
    if len(b) == len(p):
        return [
            (i, bs, ps, is_comparison_sentence(bs))
            for i, (bs, ps) in enumerate(zip(b, p))
            if bs.strip() != ps.strip()
        ]
    out = []
    sm = difflib.SequenceMatcher(a=b, b=p)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        bc, pc = " ".join(b[i1:i2]), " ".join(p[j1:j2])
        out.append((i1, bc, pc, is_comparison_sentence(bc)))
    return out


def wrap(text, indent="> "):
    return textwrap.fill(
        text or "(missing)", width=100, initial_indent=indent, subsequent_indent=indent
    )


def render(idx, rec, pred_text, prior, reference, rg=None):
    L = []
    L.append(f"## Sample {idx} — study {rec['study_id']} ({'change' if rec.get('change') else 'no-change'})")
    L.append("")

    changed = changed_sentences(rec["draft_text"], pred_text)
    if not changed:
        L.append("**No change** — the pipeline returned the baseline draft unaltered.")
    else:
        L.append(f"**{len(changed)} sentence(s) altered.**")
    if rg is not None:
        d, r = rg["draft_radgraph_f1"], rg["revised_radgraph_f1"]
        verdict = "revision hurt" if r < d else ("revision helped" if r > d else "no effect")
        L.append(f"  RadGraph-F1 {d:.4f} → {r:.4f} ({verdict})")
    L.append("")

    L.append("**Baseline — MAIRA-2 draft**")
    L.append("")
    L.append(wrap(rec["draft_text"]))
    L.append("")
    L.append("**Approach — ICL pipeline output**")
    L.append("")
    L.append(wrap(pred_text))
    L.append("")
    L.append("**Reference — ground-truth current report**")
    L.append("")
    L.append(wrap(reference))
    L.append("")

    if changed:
        L.append("<details><summary>Sentence-level diff</summary>")
        L.append("")
        for i, bs, ps, flagged in changed:
            L.append(f"*sentence {i}* ({'comparison-flagged' if flagged else 'NOT flagged'})")
            L.append("")
            L.append(f"    {word_diff(bs, ps)}")
            L.append("")
        L.append("</details>")
        L.append("")

    L.append("<details><summary>Prior report (input context)</summary>")
    L.append("")
    L.append(wrap(prior))
    L.append("")
    L.append("</details>")
    L.append("")
    L.append("---")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final-output", default=str(PATHS.final_output_file))
    ap.add_argument("--test-manifest", default=str(PATHS.test_manifest))
    ap.add_argument("--radgraph-jsonl", default=None,
                    help="icl_final_radgraph_guardrail.jsonl; enables per-case RadGraph-F1 annotation, "
                         "and is required for --variant radgraph")
    ap.add_argument("--variant", choices=["none", "chexbert", "radgraph"], default="none")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stratify", action="store_true",
                    help="sample change/no-change proportionally to the test split (1578/208) "
                         "instead of uniformly at random")
    ap.add_argument("--only-changed", action="store_true",
                    help="restrict the sample to cases where the pipeline actually altered the draft "
                         "(biases the sample -- use only to inspect revision quality, not typical output)")
    ap.add_argument("--out", default="sample_vs_baseline.md")
    args = ap.parse_args()

    records = load_jsonl(Path(args.final_output))
    manifest = load_jsonl(Path(args.test_manifest))
    prior_by_id = {r["current_study_id"]: r.get("prior_findings") for r in manifest}
    ref_by_id = {r["current_study_id"]: r.get("reference_findings") for r in manifest}

    rg_by_id = {}
    if args.radgraph_jsonl:
        rg_by_id = {r["study_id"]: r for r in load_jsonl(Path(args.radgraph_jsonl))}
    if args.variant == "radgraph" and not rg_by_id:
        ap.error("--variant radgraph requires --radgraph-jsonl")

    def pred_for(rec):
        if args.variant == "none":
            return rec["revised_text"]
        if args.variant == "chexbert":
            return rec["final_text"]
        return rg_by_id[rec["study_id"]]["final_text"]

    pool = [r for r in records if r["study_id"] in ref_by_id]
    if args.variant == "radgraph":
        pool = [r for r in pool if r["study_id"] in rg_by_id]
    if args.only_changed:
        pool = [r for r in pool if r["draft_text"].strip() != pred_for(r).strip()]

    rng = random.Random(args.seed)
    if args.stratify:
        ch = [r for r in pool if r.get("change")]
        nc = [r for r in pool if not r.get("change")]
        frac = len(ch) / len(pool) if pool else 1.0
        n_ch = round(args.n * frac)
        n_nc = args.n - n_ch
        sample = rng.sample(ch, min(n_ch, len(ch))) + rng.sample(nc, min(n_nc, len(nc)))
        rng.shuffle(sample)
    else:
        sample = rng.sample(pool, min(args.n, len(pool)))

    n_altered = sum(1 for r in sample if r["draft_text"].strip() != pred_for(r).strip())
    print(f"pool={len(pool)}  sampled={len(sample)}  variant={args.variant}  seed={args.seed}")
    print(f"{n_altered}/{len(sample)} sampled cases were actually altered by the pipeline")

    header = [
        "# Approach vs. baseline — random sample",
        "",
        f"Variant: **{args.variant}**  ·  n = {len(sample)}  ·  seed = {args.seed}"
        f"{'  ·  stratified by change flag' if args.stratify else '  ·  uniform random'}"
        f"{'  ·  restricted to altered cases' if args.only_changed else ''}",
        "",
        f"Baseline is the raw MAIRA-2 draft. {n_altered} of {len(sample)} sampled cases were altered "
        f"by the pipeline; the remainder passed through unchanged (no comparison sentence was flagged, "
        f"or the guardrail reverted the revision).",
        "",
        "Diff markup: `[-removed-]` `{+added+}`.",
        "",
        "---",
        "",
    ]

    parts = header
    for i, rec in enumerate(sample, start=1):
        parts.append(
            render(
                i, rec, pred_for(rec),
                prior_by_id.get(rec["study_id"]),
                ref_by_id.get(rec["study_id"]),
                rg_by_id.get(rec["study_id"]),
            )
        )

    Path(args.out).write_text("\n".join(parts))
    print(f"wrote {len(sample)} cases -> {args.out}")


if __name__ == "__main__":
    main()
