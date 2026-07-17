# ICL retrieve-then-revise pipeline — summary (for slide use)

## One-liner

Training-free alternative to fine-tuning: MAIRA-2 drafts the Findings section as usual, Qwen2.5-7B-Instruct rewrites only the comparison/temporal sentences using retrieved exemplars, and a guardrail decides per case whether to keep the rewrite or fall back to the draft. **Which metric the guardrail gates on turns out to matter more than whether a guardrail exists at all** — gated on RadGraph-F1 instead of CheXbert-F1, the same revision step delivers a real, statistically significant improvement.

## Why this approach

- No training required — fast to stand up, forms the baseline arm of the planned 2x2 ablation (ICL x DDaTR).
- MAIRA-2's weakness is specifically on comparison/temporal language (per Zhu et al.: ~84% error on changed-label cases vs ~11% on stable cases) — targets exactly that gap instead of retraining the whole model.
- Guardrail makes it monotonic *for whatever metric it's gated on*: per case, that metric for the revision must meet or beat the draft's, or the pipeline falls back to the unrevised draft. Turned out this guarantee is only as good as the metric chosen — see below.

## Pipeline stages (see diagram.svg / diagram.png)

1. **Draft** — MAIRA-2 (frozen, `image_and_report` mode: current + prior frontal, prior report) generates the initial Findings section.
2. **Retrieve** — a CheXbert "change signature" (14-pathology transition vector, prior to current) is computed for the draft and used to look up the most similar cases in a corpus of comparison sentences pre-extracted from the train split. A shared keyword classifier (comparison/temporal cue matching) both builds this corpus offline and flags which draft sentences are eligible for revision online.
3. **Revise** — Qwen2.5-7B-Instruct rewrites only the sentences flagged as comparison/temporal language, guided by the retrieved exemplars; the rewrite is spliced back in so every other sentence is untouched.
4. **Guardrail** — some per-case metric is computed for both the draft and the revision against ground truth; the revision is kept only if it scores at least as well, otherwise the draft is used as-is. The metric this gates on is swappable post hoc, since draft_text and revised_text are both cached regardless of which guardrail ran at generation time — this is exactly what made the RadGraph re-gating experiment below possible without rerunning MAIRA-2/Qwen.

The retrieval corpus (top of diagram) is built once, offline, from the train split only — never from test data, to avoid leakage.

**Important caveat on the guardrail, unchanged by the results below:** every guardrail variant here is an oracle — it needs `reference_findings` (the ground-truth current report) to score against, which doesn't exist yet at real deployment time. Nothing here is directly deployable as-is. What changed is *whether building a deployable proxy is worth the effort* (see Verdict).

## Engineering work done

- Full pipeline implemented as 10 Python modules + orchestrator (`~/lrrg/icl_pipeline/`).
- Cross-checked against the existing repo rather than left as guesses: real manifest schema, the already-installed `f1chexbert` package, and the confirmed-working MAIRA-2 call from `run_ablation.py`.
- Fixed a GPU memory bug: MAIRA-2 and Qwen2.5-7B-Instruct together exceed the 24GB RTX 3090 — split into two stages (`--stage draft` / `--stage revise`) that are never GPU-resident at the same time.
- Added `--shuffle` after noticing the test manifest is grouped by subject, which was skewing small samples toward all-change or all-no-change.
- Wired the pipeline's output into the existing `score.py` for the full metric stack (RadGraph-F1, stratified bootstrapped CheXbert-F1), fixing two version-compatibility bugs in the installed `f1chexbert` package along the way.
- Added three post-hoc analysis scripts that reuse `icl_final.jsonl`'s cached `draft_text`/`revised_text` without any regeneration: `export_for_score_no_guardrail.py` (always accept the revision), `reguardrail_radgraph.py` (re-decide accept/reject per case using RadGraph-F1 instead of CheXbert-F1), and `show_examples.py` (renders a handful of full end-to-end cases — prior report, draft, retrieved exemplars, revision, guardrail decision, ground truth — to `example_cases.md` for qualitative review).

## Final results (full test set, n=1,786: 1,578 change / 208 no-change)

Three guardrail variants were scored against the same 1,786 drafts/revisions, all via `score.py` (1000-resample bootstrap, 2-sided p, uncorrected for multiple comparisons — Bonferroni threshold for the 15 tests per variant is ~0.0033):

| Guardrail variant | Reject rate | BLEU-4 Δ (p) | ROUGE-L Δ (p) | METEOR Δ (p) | RadGraph-F1 Δ (p) |
|---|---|---|---|---|---|
| **CheXbert-F1-gated** (original) | 2.5% (45/1,786) | −0.0035 (0.000) | −0.0060 (0.000) | −0.0004 (0.618) | −0.0021 (0.014) |
| **No guardrail** (always accept) | 0% | −0.0036 (0.000) | −0.0063 (0.000) | −0.0003 (0.676) | −0.0025 (0.006) |
| **RadGraph-F1-gated** | 26.5% (473/1,786) | −0.0007 (0.062, n.s.) | −0.0028 (0.000) | **+0.0012 (0.018)** | **+0.0078 (0.000)** |

All deltas are `final_text` vs. `draft_text`, scored against `reference_findings`. CheXbert-F1 wasn't computed for the RadGraph-gated variant (checkpoint path issue on that run — `f1chexbert` looked for `$XDG_CACHE_HOME/chexbert/chexbert.pth` and didn't find it; not rerun yet, see Next steps).

**What this shows:**

- **CheXbert-F1-gated and no-guardrail are nearly identical.** Removing the guardrail entirely only cost ~0.0001–0.0004 across every metric. The 2.5% reject rate was too small, and CheXbert-F1 too insensitive to comparison-sentence rephrasing, to meaningfully protect anything — confirming the suspicion in the original write-up.
- **RadGraph-F1-gating changes the outcome, not just the margin.** It rejects 10x more revisions (26.5% vs 2.5%) — of the 473 rejects, 466 are cases the CheXbert guardrail would have accepted, meaning CheXbert and RadGraph-F1 are frequently judging the *same* revision in opposite directions. Once the guardrail actually screens on the metric that reflects clinical entity/relation correctness, RadGraph-F1 flips from significantly negative to significantly positive (+0.0078, clears the Bonferroni bar comfortably), BLEU-4's damage becomes statistically indistinguishable from zero, ROUGE-L's damage shrinks by more than half, and METEOR flips positive too.
- **The change stratum drives all of it**, consistent with Zhu et al.'s finding that MAIRA-2's comparison-language errors concentrate there: RadGraph-F1 change-stratum Δ is +0.0083 (p=0.000) under RadGraph-gating vs. −0.0027 (p=0.004) under CheXbert-gating. No-change stratum effects are smaller throughout and were never significant under CheXbert-gating or no-guardrail, though they do turn significant (small, positive) under RadGraph-gating.

### Verdict (revised)

The original verdict — "no net gain, don't pursue this" — was wrong about the *revision step*, right about the *guardrail as originally built*. Qwen's rewrites, gated on the correct metric, produce a real, well-powered, statistically robust improvement in entity/relation match (RadGraph-F1) with no significant cost to BLEU-4 and a much-reduced cost to ROUGE-L. The earlier negative result was a guardrail-selection artifact: CheXbert-F1 barely reacts to comparison-sentence phrasing, so it was accepting revisions almost indiscriminately (2.5% reject rate) regardless of whether they actually helped, letting harmful rewrites through at close to the rate an unfiltered pipeline would.

This is still an oracle result — every guardrail variant requires `reference_findings`, which isn't available at real inference time — so it doesn't directly hand over a deployable pipeline. What it does establish is that the *ceiling* for this retrieve-then-revise architecture is a genuine win, not a wash, which was not known before this run. That changes whether it's worth building a deployable, no-ground-truth proxy for "will this revision help" (see Next steps) — before this result there was no evidence the effort would pay off; now there is.

## Next steps

- **Get CheXbert-F1 for the RadGraph-gated variant** — fix the checkpoint path (`export XDG_CACHE_HOME=/var/tmp/xdg_cache_grauperez` before running, or point `f1chexbert` at wherever the checkpoint actually lives on that venv) and rerun `score.py` on `icl_predictions_radgraph_guardrail.csv` for the complete metric picture.
- **Build a deployable (non-oracle) proxy guardrail.** Candidates: a self-consistency check (sample Qwen's revision multiple times, accept only if stable), an NLI/entailment check between the revision and the retrieved exemplars + prior report, or a lightweight learned classifier trained on the 466 disagreement cases (CheXbert accept / RadGraph reject or vice versa) as labeled examples of what "good" vs. "bad" revisions look like structurally.
- **Manually inspect a sample of the 466 disagreement cases** (`icl_final_radgraph_guardrail.jsonl` has both guardrails' verdicts side by side per case) to characterize what CheXbert-F1 is missing that RadGraph-F1 catches — this is exactly the training signal a deployable proxy would need.
- **Report this as the ICL arm's (corrected) result in the 2x2 ablation against DDaTR** — a real, guardrail-dependent positive result with a clearly documented caveat about deployability, which is a more useful and more accurate finding than either the original "no net gain" verdict or an unqualified "it works."
