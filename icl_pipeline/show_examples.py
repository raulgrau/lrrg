#!/usr/bin/env python
"""
Pull a handful of end-to-end example cases out of icl_final.jsonl and render
them as a readable markdown file: prior report, MAIRA-2 draft, the retrieved
exemplar sentences Qwen actually saw, Qwen's revision, the guardrail's
accept/reject decision (with both F1s), the final text that decision
produced, and the ground-truth reference for comparison.

icl_final.jsonl only stores exemplar_study_ids (not the exemplar sentence
text itself), so exemplar sentences are reconstructed by pulling each
study_id's rows straight out of comparison_corpus.parquet, in the same
head(max_per_report=2)-per-study order retrieve.py used. This is a
reconstruction, not a byte-identical replay -- it will be exactly right as
long as comparison_corpus.parquet hasn't changed since the run, which it
shouldn't have (it's built once, offline, from the train split).

Selects a deliberate mix rather than the first N rows: some accepted
revisions on change=True cases (the pipeline's intended sweet spot), some
guardrail rejections (revision made, but reverted), and one no-op case
(no comparison sentences flagged) for contrast -- so the sample shows the
guardrail actually doing something, not just a run of identical outcomes.

Usage:
    python show_examples.py --out example_cases.md --n-per-category 2
"""
import argparse
import json
import textwrap
from pathlib import Path

import pandas as pd

from config import PATHS


def load_jsonl(path: Path) -> list:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def reconstruct_exemplars(exemplar_study_ids, corpus_df, max_per_report=2):
    """Best-effort reconstruction of the sentence text for each exemplar
    study_id, in the same per-study order retrieve.py's head(max_per_report)
    would have produced. Returns a flat list of (study_id, sentence) in the
    same order as exemplar_study_ids, deduplicating consecutive repeats of
    the same study (retrieve.py emits up to max_per_report consecutive
    entries for one study before moving to the next)."""
    out = []
    seen_count = {}
    for sid in exemplar_study_ids:
        idx = seen_count.get(sid, 0)
        rows = corpus_df[corpus_df["study_id"] == sid].head(max_per_report)
        if idx < len(rows):
            out.append((sid, rows.iloc[idx]["sentence"]))
        else:
            out.append((sid, "(sentence text unavailable -- corpus may have changed)"))
        seen_count[sid] = idx + 1
    return out


def wrap(text, width=100, indent="    "):
    if not text:
        return indent + "(empty)"
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)


def render_case(rec, prior_findings, reference_findings, corpus_df):
    lines = []
    lines.append(f"## {rec['study_id']}  ({'change' if rec.get('change') else 'no-change'} case)")
    lines.append("")
    outcome = "ACCEPTED (revision kept)" if rec["accepted"] else "REJECTED (reverted to draft)"
    if not rec.get("revision_succeeded", True):
        outcome = "NO REVISION (parse failed or nothing to revise -- draft used)"
    lines.append(f"**Guardrail outcome:** {outcome}  ")
    lines.append(f"**draft_f1** = {rec['draft_f1']:.4f}  |  **revised_f1** = {rec['revised_f1']:.4f}")
    lines.append("")

    lines.append("**Prior report (ground truth):**")
    lines.append(wrap(prior_findings))
    lines.append("")

    lines.append("**MAIRA-2 draft:**")
    lines.append(wrap(rec["draft_text"]))
    lines.append("")

    if rec.get("exemplar_study_ids"):
        lines.append("**Retrieved exemplars shown to Qwen:**")
        for sid, sentence in reconstruct_exemplars(rec["exemplar_study_ids"], corpus_df):
            lines.append(f"  - _{sid}_: \"{sentence}\"")
        lines.append("")

    if rec["revised_text"] != rec["draft_text"]:
        lines.append("**Qwen's revision:**")
        lines.append(wrap(rec["revised_text"]))
        lines.append("")

    lines.append("**Final text (what the pipeline actually output):**")
    lines.append(wrap(rec["final_text"]))
    lines.append("")

    lines.append("**Ground-truth reference (current report):**")
    lines.append(wrap(reference_findings))
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-output", default=str(PATHS.final_output_file))
    parser.add_argument("--test-manifest", default=str(PATHS.test_manifest))
    parser.add_argument("--corpus-file", default=str(PATHS.corpus_file))
    parser.add_argument("--n-per-category", type=int, default=2)
    parser.add_argument("--out", default="example_cases.md")
    args = parser.parse_args()

    print(f"loading {args.final_output} ...")
    records = load_jsonl(Path(args.final_output))
    print(f"loaded {len(records)} records")

    print(f"loading {args.test_manifest} ...")
    manifest = load_jsonl(Path(args.test_manifest))
    prior_by_id = {r["current_study_id"]: r["prior_findings"] for r in manifest}
    ref_by_id = {r["current_study_id"]: r["reference_findings"] for r in manifest}

    print(f"loading {args.corpus_file} ...")
    corpus_df = pd.read_parquet(args.corpus_file)

    accepted_change = [
        r for r in records
        if r["accepted"] and r["change"] and r["revised_text"] != r["draft_text"]
    ]
    rejected_change = [
        r for r in records
        if not r["accepted"] and r.get("revision_succeeded") and r["revised_text"] != r["draft_text"] and r["change"]
    ]
    no_op = [r for r in records if r["revised_text"] == r["draft_text"]]

    n = args.n_per_category
    selected = accepted_change[:n] + rejected_change[:n] + no_op[:1]
    print(
        f"selected {len(accepted_change[:n])} accepted-change, {len(rejected_change[:n])} "
        f"rejected-change, {len(no_op[:1])} no-op example(s) "
        f"(pool sizes: {len(accepted_change)} / {len(rejected_change)} / {len(no_op)})"
    )

    out_parts = ["# ICL pipeline: end-to-end example cases", ""]
    for rec in selected:
        study_id = rec["study_id"]
        out_parts.append(
            render_case(
                rec,
                prior_by_id.get(study_id, "(not found in manifest)"),
                ref_by_id.get(study_id, "(not found in manifest)"),
                corpus_df,
            )
        )

    Path(args.out).write_text("\n".join(out_parts))
    print(f"wrote {len(selected)} example cases -> {args.out}")


if __name__ == "__main__":
    main()
