# ICL Retrieve-then-Revise Pipeline — Design Spec

## Goal

Improve MAIRA-2's Findings section on comparison/temporal content without any training, by drafting with MAIRA-2 and revising only the comparison sentences with Qwen2.5-7B-Instruct, guided by retrieved exemplars. Must never regress CheXbert-F1 relative to the raw MAIRA-2 draft.

## Pipeline stages

**1. Draft.** Run MAIRA-2 in `image_and_report` mode (current frontal + prior frontal + prior report) to produce a draft Findings section for each test case. Cases missing prior image or prior report are excluded from the prior-conditioned arm (per MAIRA-2's silent-drop behavior already documented).

**2. Retrieval corpus (train/val split only, never test).**
- Source: ULCX train/val reports (patient-disjoint from the test split).
- Extract candidate comparison sentences via a temporal-keyword filter (e.g. *compared to, since the prior, unchanged, improved, worsened, new since, resolved, redemonstrat-, interval, again seen, no longer seen, stable*). Keep sentence + its source report ID.
- Compute CheXbert-14 labels for each corpus report and its own prior report; the **change signature** is the per-label transition vector (positive/negative/uncertain/no-mention → positive/negative/uncertain/no-mention), i.e. a 14-dim categorical delta.
- Optional: embed prior/current image pair with RAD-DINO, take the difference vector, index in FAISS for visual-similarity retrieval.
- Store as `{sentence, report_id, change_signature, image_diff_embedding?}` in a flat corpus file (parquet/jsonl).

**3. Query-side signature at inference.** We don't have the ground-truth current report at test time, so:
- Prior CheXbert labels: computed from the *prior report* (given, ground truth).
- Current CheXbert labels: computed from the *MAIRA-2 draft itself* (proxy for current state).
- Change signature = transition vector between the two, same encoding as corpus.

**4. Retrieve top-k exemplars.** Rank corpus entries by similarity to the query change signature (Hamming/cosine over the 14-dim transition vector); if image-diff FAISS index is enabled, blend as a weighted rerank (e.g. `score = α·signature_sim + (1-α)·image_sim`, start α=0.7 and tune). k likely 3–5.

**5. Anonymize exemplars.** MIMIC reports are already de-identified (`___` placeholders), but strip any residual accession numbers, dates, or study-specific identifiers from retrieved sentences before they reach the prompt — replace with generic placeholders.

**6. Sentence-level split of the draft.** Reuse the same temporal-keyword classifier from step 2 to split the MAIRA-2 draft into comparison sentences vs. everything else. Only comparison sentences are candidates for revision.

**7. Revise with Qwen2.5-7B-Instruct.** Prompt contains: the full draft (for context), the isolated comparison sentence(s) to revise, and the k anonymized exemplars as style/pattern references. Instruction: rewrite only the given comparison sentence(s) to better reflect standard temporal-reporting phrasing and the retrieved patterns; do not introduce new findings; do not touch non-comparison sentences; return the same number of sentences in the same order.

**8. Surgical splice.** Replace only the classified comparison sentences in the original draft with Qwen's revised versions, preserving all other sentences byte-identical. This bounds the blast radius of any LLM error to the comparison sentences only.

**9. Guardrail (CheXbert-F1 floor).** Compute CheXbert-F1 for both the original draft and the spliced/revised report against ground truth. If revised F1 < draft F1, reject the revision and fall back to the unrevised draft for that case. This makes the pipeline monotonic — never worse than plain MAIRA-2, per-case.

## File layout (as implemented)

| File | Responsibility |
|---|---|
| `build_retrieval_corpus.py` | Step 2: extract comparison sentences from train (+ val) reports, compute CheXbert-14 signatures, optional image-diff FAISS build. |
| `retrieve.py` | Steps 3–4: compute query signature from draft+prior, rank/retrieve top-k, optional image blend. |
| `revise.py` | Steps 5–8: anonymize, classify draft sentences, build Qwen prompt, call model, splice. |
| `guardrail.py` | Step 9: dual CheXbert-F1 scoring, accept/reject decision, change-stratified reject-rate tracking. |
| `run_icl_pipeline.py` | Orchestrator: per-case draft → retrieve → revise → guardrail → write output. Resumable, ETA every 25 cases, runs inside `tmux`. |

## Open parameters to decide before coding

- k (number of exemplars): start 3–5, tune on a held-out slice.
- α (signature vs. image-diff weight): start 0.7, sweep if image index is built.
- Temporal-keyword list: needs a first pass + manual review against a sample of ULCX reports to check precision/recall of the sentence classifier itself (this classifier is used in three places — corpus build, query signature via draft, and splice targeting — so its errors compound).
- Guardrail floor: strict per-case floor (this doc's default) vs. a looser aggregate floor (revised-corpus mean ≥ draft-corpus mean). Strict is safer and simpler to reason about; recommend starting there.
- Reject-rate tracking: log how often the guardrail falls back, per case and in aggregate — a high reject rate signals the revision step isn't adding value and is itself a useful ablation result.

## Evaluation

- Primary: CheXbert-F1, stratified by change vs. no-change cases (per Zhu et al., ~84% error on changed-label cases vs. ~11% stable — this is the gap ICL targets).
- Secondary: RadGraph-F1, Temporal-F1/TEM, GREEN.
- Tertiary (known misleading, still report): BLEU-4, ROUGE-L, METEOR.
- Report reject rate (guardrail fallbacks) and hallucinated-comparison rate as pipeline-specific diagnostics.
- Fits into the planned 2×2 ablation (ICL × DDaTR) — ICL alone forms the fast, training-free baseline arm.

## Explicitly out of scope for this pipeline

- No fine-tuning of MAIRA-2 or Qwen.
- No modification to non-comparison sentences.
- No use of the test split for corpus construction (leakage).
