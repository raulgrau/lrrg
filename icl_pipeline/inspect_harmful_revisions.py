#!/usr/bin/env python
"""
Dump the revisions that hurt RadGraph-F1 the most, as a readable markdown
file with sentence-level diffs, so the failure modes can be characterised by
hand.

This is step (2) in summary.md's Next steps: the unconditional revision makes
reports worse (RadGraph-F1 0.2680 -> 0.2655), and RadGraph-gating rejects
26.5% of revisions as harmful. This script surfaces *what Qwen is actually
doing wrong* in those cases, which is the input to fixing the reviser prompt
(step 3) rather than just filtering its output.

Runs on CPU in seconds -- no GPU, no model loads. All the RadGraph scoring
already happened in reguardrail_radgraph.py; this just joins, ranks, and
renders.

Inputs (joined by study_id):
  icl_final_radgraph_guardrail.jsonl  per-case RadGraph-F1 for draft + revised
                                      (from reguardrail_radgraph.py)
  icl_final.jsonl                     draft_text / revised_text / exemplars
  test_pairs_ulcx.jsonl               prior_findings / reference_findings
  comparison_corpus.parquet           (optional) exemplar sentence text

Key output per case is the SENTENCE-LEVEL DIFF: only sentences that actually
changed are shown, with word-level +/- markup, since revise.py splices
revisions back in per sentence and leaves everything else byte-identical.
Reading whole reports side by side buries the 1-2 sentences that matter.

Usage:
    python inspect_harmful_revisions.py --n 30 --out harmful_revisions.md

    # also dump the biggest *improvements* for contrast, into a second file:
    python inspect_harmful_revisions.py --n 30 --also-best 15 --out harmful_revisions.md
"""
import argparse
import difflib
import json
import re
import textwrap
from collections import Counter
from pathlib import Path

from config import PATHS
from temporal_utils import is_comparison_sentence, split_sentences


def load_jsonl(path: Path) -> list:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def word_diff(old: str, new: str) -> str:
    """Inline word-level diff markup: [-removed-] {+added+}."""
    old_words = old.split()
    new_words = new.split()
    sm = difflib.SequenceMatcher(a=old_words, b=new_words)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(" ".join(old_words[i1:i2]))
        elif tag == "delete":
            out.append(f"[-{' '.join(old_words[i1:i2])}-]")
        elif tag == "insert":
            out.append(f"{{+{' '.join(new_words[j1:j2])}+}}")
        elif tag == "replace":
            out.append(f"[-{' '.join(old_words[i1:i2])}-] {{+{' '.join(new_words[j1:j2])}+}}")
    return " ".join(out)


def sentence_pairs(draft_text: str, revised_text: str):
    """
    Align draft and revised sentences and return only the ones that changed,
    as (index, draft_sentence, revised_sentence, was_flagged_comparison).

    revise.py splices per sentence and preserves count, so a positional zip is
    the correct alignment in the normal case. If counts differ (shouldn't
    happen -- the parser enforces equal length -- but be defensive), fall back
    to difflib alignment so the script degrades rather than crashing.
    """
    d_sents = split_sentences(draft_text)
    r_sents = split_sentences(revised_text)

    if len(d_sents) == len(r_sents):
        pairs = list(enumerate(zip(d_sents, r_sents)))
        return [
            (i, d, r, is_comparison_sentence(d))
            for i, (d, r) in pairs
            if d.strip() != r.strip()
        ]

    changed = []
    sm = difflib.SequenceMatcher(a=d_sents, b=r_sents)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        d_chunk = " ".join(d_sents[i1:i2])
        r_chunk = " ".join(r_sents[j1:j2])
        changed.append((i1, d_chunk, r_chunk, is_comparison_sentence(d_chunk)))
    return changed


# Heuristic failure-mode tags. These are hypotheses to check by reading, not
# ground truth -- they exist to make patterns visible across 30 cases quickly.
_HEDGE_TERMS = [
    "may", "might", "could", "possibly", "probably", "appears", "appear",
    "suggests", "suggestive", "likely", "cannot be excluded", "concerning for",
]
_VAGUE_REFS = ["prior study", "prior examination", "previous study", "previous examination", "prior exam"]


def tag_failure_modes(d_sent: str, r_sent: str) -> list:
    tags = []
    d_low, r_low = d_sent.lower(), r_sent.lower()

    d_hedges = sum(d_low.count(t) for t in _HEDGE_TERMS)
    r_hedges = sum(r_low.count(t) for t in _HEDGE_TERMS)
    if r_hedges > d_hedges:
        tags.append("added-hedging")

    d_words, r_words = len(d_sent.split()), len(r_sent.split())
    if r_words > d_words * 1.25:
        tags.append("verbose")
    elif r_words < d_words * 0.75:
        tags.append("truncated")

    d_vague = sum(d_low.count(t) for t in _VAGUE_REFS)
    r_vague = sum(r_low.count(t) for t in _VAGUE_REFS)
    if r_vague > d_vague:
        tags.append("added-vague-prior-ref")

    # laterality / anatomical qualifiers dropped
    for term in ["right", "left", "bilateral", "upper", "lower", "middle", "basilar", "apical"]:
        if d_low.count(term) > r_low.count(term):
            tags.append(f"dropped-qualifier:{term}")

    # numbers / measurements dropped
    d_nums = set(re.findall(r"\d+\.?\d*", d_sent))
    r_nums = set(re.findall(r"\d+\.?\d*", r_sent))
    if d_nums - r_nums:
        tags.append("dropped-measurement")

    # negation flips
    for neg in ["no ", "not ", "without ", "absent"]:
        if (neg in d_low) != (neg in r_low):
            tags.append("negation-changed")
            break

    return tags


def render_case(rec, final_rec, prior, reference, corpus_df, rank, delta):
    lines = []
    direction = "HARMFUL" if delta > 0 else "HELPFUL"
    lines.append(f"## #{rank} — study {rec['study_id']} ({'change' if rec.get('change') else 'no-change'})")
    lines.append("")
    lines.append(
        f"**RadGraph-F1: {rec['draft_radgraph_f1']:.4f} (draft) → "
        f"{rec['revised_radgraph_f1']:.4f} (revised)  |  Δ {-delta:+.4f}  [{direction}]**  "
    )
    ch = "accept" if rec["accepted_chexbert_guardrail"] else "reject"
    rg = "accept" if rec["accepted_radgraph_guardrail"] else "reject"
    flag = "  ← guardrails disagree" if rec["guardrails_disagree"] else ""
    lines.append(f"CheXbert guardrail: **{ch}**  |  RadGraph guardrail: **{rg}**{flag}")
    lines.append("")

    changed = sentence_pairs(final_rec["draft_text"], final_rec["revised_text"])
    if not changed:
        lines.append("_No sentence-level change detected (revision was a no-op)._")
        lines.append("")
    else:
        lines.append(f"### Changed sentences ({len(changed)})")
        lines.append("")
        for idx, d_sent, r_sent, was_flagged in changed:
            tags = tag_failure_modes(d_sent, r_sent)
            tag_str = f"  `{' '.join(tags)}`" if tags else ""
            flagged_str = "comparison-flagged" if was_flagged else "**NOT comparison-flagged**"
            lines.append(f"**sentence {idx}** ({flagged_str}){tag_str}")
            lines.append("")
            lines.append(f"- draft:   {d_sent}")
            lines.append(f"- revised: {r_sent}")
            lines.append(f"- diff:    {word_diff(d_sent, r_sent)}")
            lines.append("")

    if final_rec.get("exemplar_study_ids") and corpus_df is not None:
        lines.append("<details><summary>Retrieved exemplars shown to Qwen</summary>")
        lines.append("")
        seen = {}
        for sid in final_rec["exemplar_study_ids"]:
            i = seen.get(sid, 0)
            rows = corpus_df[corpus_df["study_id"] == sid].head(2)
            sent = rows.iloc[i]["sentence"] if i < len(rows) else "(unavailable)"
            seen[sid] = i + 1
            lines.append(f"- _{sid}_: \"{sent}\"")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("<details><summary>Full texts (prior / draft / revised / reference)</summary>")
    lines.append("")
    for label, text in (
        ("PRIOR (ground truth)", prior),
        ("DRAFT (MAIRA-2)", final_rec["draft_text"]),
        ("REVISED (Qwen)", final_rec["revised_text"]),
        ("REFERENCE (ground truth current)", reference),
    ):
        lines.append(f"**{label}**")
        lines.append("")
        lines.append(textwrap.fill(text or "(missing)", width=100, initial_indent="> ", subsequent_indent="> "))
        lines.append("")
    lines.append("</details>")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--radgraph-jsonl", default="icl_final_radgraph_guardrail.jsonl")
    parser.add_argument("--final-output", default=str(PATHS.final_output_file))
    parser.add_argument("--test-manifest", default=str(PATHS.test_manifest))
    parser.add_argument("--corpus-file", default=str(PATHS.corpus_file))
    parser.add_argument("--n", type=int, default=30, help="how many worst-regression cases to dump")
    parser.add_argument("--also-best", type=int, default=0, help="also dump this many biggest improvements, for contrast")
    parser.add_argument("--out", default="harmful_revisions.md")
    parser.add_argument(
        "--tag-stats", action="store_true",
        help="compute failure-mode tag rates across ALL hurt/helped/neutral cases, not just the "
             "worst N. Needed to tell whether a tag actually predicts harm or is just how Qwen "
             "writes generally -- a tag equally common in helped cases explains nothing.",
    )
    args = parser.parse_args()

    print(f"loading {args.radgraph_jsonl} ...")
    rg_records = load_jsonl(Path(args.radgraph_jsonl))
    print(f"loading {args.final_output} ...")
    final_by_id = {r["study_id"]: r for r in load_jsonl(Path(args.final_output))}
    print(f"loading {args.test_manifest} ...")
    manifest = load_jsonl(Path(args.test_manifest))
    prior_by_id = {r["current_study_id"]: r.get("prior_findings") for r in manifest}
    ref_by_id = {r["current_study_id"]: r.get("reference_findings") for r in manifest}

    corpus_df = None
    try:
        import pandas as pd

        print(f"loading {args.corpus_file} ...")
        corpus_df = pd.read_parquet(args.corpus_file)
    except Exception as e:
        print(f"(exemplar text unavailable, continuing without: {e})")

    # Only cases where a real revision happened; a no-op can't teach us anything.
    candidates = []
    for rec in rg_records:
        fr = final_by_id.get(rec["study_id"])
        if fr is None:
            continue
        if fr["draft_text"].strip() == fr["revised_text"].strip():
            continue
        drop = rec["draft_radgraph_f1"] - rec["revised_radgraph_f1"]  # >0 means revision hurt
        candidates.append((drop, rec, fr))

    candidates.sort(key=lambda t: t[0], reverse=True)
    worst = candidates[: args.n]
    best = candidates[-args.also_best :][::-1] if args.also_best else []

    n_hurt = sum(1 for d, _, _ in candidates if d > 0)
    n_helped = sum(1 for d, _, _ in candidates if d < 0)
    n_flat = sum(1 for d, _, _ in candidates if d == 0)
    print(
        f"\n{len(candidates)} cases with a real (non-no-op) revision: "
        f"{n_hurt} hurt RadGraph-F1, {n_helped} helped, {n_flat} unchanged"
    )

    if args.tag_stats:
        print("\ncomputing tag rates across all populations ...")
        pops = {
            "hurt": [c for c in candidates if c[0] > 0],
            "helped": [c for c in candidates if c[0] < 0],
            "neutral": [c for c in candidates if c[0] == 0],
        }
        pop_tags = {}
        pop_lenratio = {}
        for name, pop in pops.items():
            counts = Counter()
            n_cases_with_tag = Counter()
            ratios = []
            for _, _, fr in pop:
                case_tags = set()
                for _, d_sent, r_sent, _ in sentence_pairs(fr["draft_text"], fr["revised_text"]):
                    for t in tag_failure_modes(d_sent, r_sent):
                        base = t.split(":")[0]
                        counts[base] += 1
                        case_tags.add(base)
                    dw, rw = len(d_sent.split()), len(r_sent.split())
                    if dw:
                        ratios.append(rw / dw)
                for t in case_tags:
                    n_cases_with_tag[t] += 1
            pop_tags[name] = (n_cases_with_tag, len(pop))
            pop_lenratio[name] = sum(ratios) / len(ratios) if ratios else float("nan")

        all_tags = sorted({t for c, _ in pop_tags.values() for t in c})
        print("\n=== tag prevalence: share of cases in each population showing the tag ===")
        header = f"{'tag':28s} " + "".join(f"{k+' (n='+str(pop_tags[k][1])+')':>20s}" for k in pops)
        print(header)
        for t in all_tags:
            row = f"{t:28s} "
            for k in pops:
                counts, n = pop_tags[k]
                row += f"{(counts[t]/n if n else 0):>19.1%} "
            print(row)
        print(f"\n{'mean revised/draft word ratio':28s} " + "".join(f"{pop_lenratio[k]:>19.3f} " for k in pops))
        print(
            "\nRead this as: a tag only explains the regression if its rate is materially HIGHER "
            "in 'hurt' than in 'helped'. Equal rates mean it is just how Qwen writes."
        )

    # Aggregate failure-mode tally across the worst N -- the actual deliverable
    # for characterising what's going wrong.
    tally = Counter()
    not_flagged = 0
    total_changed = 0
    for _, _, fr in worst:
        for _, d_sent, r_sent, was_flagged in sentence_pairs(fr["draft_text"], fr["revised_text"]):
            total_changed += 1
            if not was_flagged:
                not_flagged += 1
            for t in tag_failure_modes(d_sent, r_sent):
                tally[t] += 1

    parts = [
        "# Harmful revisions — RadGraph-F1 regressions",
        "",
        f"Worst {len(worst)} of {len(candidates)} real revisions, ranked by RadGraph-F1 drop "
        f"(draft − revised). Across the whole set: **{n_hurt} hurt, {n_helped} helped, {n_flat} flat**.",
        "",
        "Diff markup: `[-removed-]` `{+added+}`. Failure-mode tags are heuristic hypotheses "
        "to check by reading, not ground truth.",
        "",
        "## Failure-mode tally (worst cases only)",
        "",
        f"- changed sentences examined: **{total_changed}**",
        f"- changed but NOT comparison-flagged: **{not_flagged}** "
        f"(these should be zero — revise.py only rewrites flagged sentences, so any nonzero "
        f"count means the splice or the classifier is misbehaving)",
        "",
    ]
    for tag, count in tally.most_common():
        parts.append(f"- `{tag}`: {count}")
    parts.append("")
    parts.append("---")
    parts.append("")

    for rank, (drop, rec, fr) in enumerate(worst, start=1):
        parts.append(
            render_case(
                rec, fr, prior_by_id.get(rec["study_id"]), ref_by_id.get(rec["study_id"]),
                corpus_df, rank, drop,
            )
        )

    if best:
        parts.append("# Biggest improvements (for contrast)")
        parts.append("")
        for rank, (drop, rec, fr) in enumerate(best, start=1):
            parts.append(
                render_case(
                    rec, fr, prior_by_id.get(rec["study_id"]), ref_by_id.get(rec["study_id"]),
                    corpus_df, rank, drop,
                )
            )

    Path(args.out).write_text("\n".join(parts))
    print(f"wrote {len(worst)} worst" + (f" + {len(best)} best" if best else "") + f" -> {args.out}")
    if tally:
        print("\ntop failure-mode tags:")
        for tag, count in tally.most_common(8):
            print(f"  {tag}: {count}")


if __name__ == "__main__":
    main()
