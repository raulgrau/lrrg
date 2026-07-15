# ICL retrieve-then-revise pipeline — summary (for slide use)

## One-liner

Training-free alternative to fine-tuning: MAIRA-2 drafts the Findings section as usual, Qwen2.5-7B-Instruct rewrites only the comparison/temporal sentences using retrieved exemplars, and a CheXbert-F1 guardrail guarantees the result is never worse than the raw draft.

## Why this approach

- No training required — fast to stand up, forms the baseline arm of the planned 2x2 ablation (ICL x DDaTR).
- MAIRA-2's weakness is specifically on comparison/temporal language (per Zhu et al.: ~84% error on changed-label cases vs ~11% on stable cases) — targets exactly that gap instead of retraining the whole model.
- Guardrail makes it monotonic: per case, CheXbert-F1 of the revision must meet or beat the draft's, or the pipeline falls back to the unrevised draft.

## Pipeline stages (see diagram.svg / diagram.png)

1. **Draft** — MAIRA-2 (frozen, `image_and_report` mode: current + prior frontal, prior report) generates the initial Findings section.
2. **Retrieve** — a CheXbert "change signature" (14-pathology transition vector, prior to current) is computed for the draft and used to look up the most similar cases in a corpus of comparison sentences pre-extracted from the train split.
3. **Revise** — Qwen2.5-7B-Instruct rewrites only the sentences flagged as comparison/temporal language, guided by the retrieved exemplars; the rewrite is spliced back in so every other sentence is untouched.
4. **Guardrail** — CheXbert-F1 is computed for both the draft and the revision against ground truth; the revision is kept only if it scores at least as well, otherwise the draft is used as-is.

The retrieval corpus (top of diagram) is built once, offline, from the train split only — never from test data, to avoid leakage.

## Engineering work done

- Full pipeline implemented as 10 Python modules + orchestrator (`~/lrrg/icl_pipeline/`).
- Cross-checked against the existing repo rather than left as guesses: real manifest schema, the already-installed `f1chexbert` package, and the confirmed-working MAIRA-2 call from `run_ablation.py`.
- Fixed a GPU memory bug: MAIRA-2 and Qwen2.5-7B-Instruct together exceed the 24GB RTX 3090 — split into two stages (`--stage draft` / `--stage revise`) that are never GPU-resident at the same time.
- Added `--shuffle` after noticing the test manifest is grouped by subject, which was skewing small samples toward all-change or all-no-change.
- Wired the pipeline's output into the existing `score.py` for the full metric stack (RadGraph-F1, stratified bootstrapped CheXbert-F1), fixing two version-compatibility bugs in the installed `f1chexbert` package along the way.

## Final results (full test set, n=1,786: 1,578 change / 208 no-change)

Guardrail behavior at scale: reject rate 2.5% (45/1,786) — the vast majority of revisions were accepted. Pipeline's own per-case CheXbert-F1 (guardrail metric) rose from 0.5084 (draft) to 0.5135 (final) — guaranteed non-decreasing by construction, since that is literally the guardrail's accept condition. Not independent evidence of quality; see verdict below.

Independent evaluation via `score.py` (1000-resample bootstrap, 2-sided p, uncorrected for multiple comparisons across 15 tests):

| Metric | Overall Δ | Significant? | `change` stratum Δ | Significant? |
|---|---|---|---|---|
| BLEU-4 | -0.0035 | **yes**, p=0.000 | -0.0039 | **yes**, p=0.000 |
| ROUGE-L | -0.0060 | **yes**, p=0.000 | -0.0066 | **yes**, p=0.000 |
| METEOR | -0.0004 | no, p=0.618 | -0.0009 | no, p=0.266 |
| RadGraph-F1 | -0.0021 | yes (uncorrected), p=0.014 | -0.0023 | yes (uncorrected), p=0.012 |
| CheXbert-F1 (micro, point est.) | +0.0040 | guardrail-guaranteed, not a test | +0.0045 | guardrail-guaranteed, not a test |

**This reverses the n=70 preview.** At small sample, RadGraph-F1 trended positive (+0.0059, p=0.144) — a promising-looking but statistically empty signal. At full power it is significantly *negative* instead. BLEU-4/ROUGE-L being significantly worse was already visible at n=70 and holds up.

**Multiple-comparisons note:** 15 bootstrap tests run here without correction. Bonferroni threshold would be ~0.0033. BLEU-4 and ROUGE-L (p=0.000 throughout) clearly clear that bar; RadGraph-F1 (p=0.012-0.014) does not — so call it a soft, not robust, negative signal, but a real reversal from the earlier hopeful read regardless.

### Verdict

At full scale, this ICL revision step does not demonstrate a benefit on the metric that matters most (RadGraph-F1 — entities/relations vs. reference) and measurably, robustly hurts surface overlap (BLEU-4, ROUGE-L). The CheXbert-F1 "improvement" is a guardrail artifact (the guardrail's own accept rule), not independent evidence. This is a legitimate negative result for the report, and it points at a concrete fix: **the guardrail filters on CheXbert-F1, which barely reacts to comparison-sentence rephrasing, so it lets through revisions that RadGraph-F1 would have rejected.**

## Next steps

- Consider swapping (or adding) RadGraph-F1 as the guardrail's accept criterion instead of/alongside CheXbert-F1, since CheXbert-F1 is proving to be a weak filter for this specific intervention.
- Manually inspect a sample of cases where RadGraph-F1 dropped after revision to see what Qwen's rewrite is doing structurally (e.g. added phrases that dilute entity/relation extraction).
- Try a more conservative reviser prompt (minimal-edit constraint) to test whether a smaller footprint reduces the RadGraph regression while still normalizing phrasing.
- Report this as the ICL arm's result in the 2x2 ablation against DDaTR — a documented, well-powered negative result is a valid and useful outcome, not a dead end.
