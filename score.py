#!/usr/bin/env python3
"""
score.py  —  Stratified with-vs-without-prior scoring with significance tests.

Reports each metric OVERALL and split by change / no-change (does the GT mention
interval change?). Surface metrics (BLEU-4, ROUGE-L, METEOR) and RadGraph-F1 get
paired bootstrap 95% CIs + a 2-sided bootstrap p-value (resampling cases). CheXbert-F1
is reported as a per-stratum point estimate (stable at large n).

Run in a SEPARATE venv from inference. Scoring the full ~2k split takes a few
minutes (BLEU bootstrap + CheXbert/RadGraph model passes).
"""

import argparse, csv, json
import numpy as np
import nltk
from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu
from nltk.translate.meteor_score import meteor_score
from rouge_score import rouge_scorer

for pkg in ("wordnet", "omw-1.4"):
    try: nltk.download(pkg, quiet=True)
    except Exception: pass

SM = SmoothingFunction().method1
W4 = (0.25, 0.25, 0.25, 0.25)
ROUGE = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
RNG = np.random.default_rng(0)


def tok(s): return s.lower().split()


def boot(eval_pair, idx, B):
    """eval_pair(idx)->(score_without, score_with). Returns w0,w1,delta,lo,hi,p."""
    idx = np.asarray(idx)
    if len(idx) == 0:
        return (float("nan"),) * 6
    w0, w1 = eval_pair(idx)
    n = len(idx)
    deltas = np.empty(B)
    for b in range(B):
        s = idx[RNG.integers(0, n, n)]
        a, c = eval_pair(s)
        deltas[b] = c - a
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    p = min(1.0, 2.0 * min((deltas <= 0).mean(), (deltas >= 0).mean()))
    return w0, w1, w1 - w0, lo, hi, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", default="predictions.csv")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--out-json", default="results_stratified.json")
    args = ap.parse_args()
    B = args.bootstrap

    rows = list(csv.DictReader(open(args.preds)))
    refs = [r["reference"] for r in rows]
    wo = [r["pred_without_prior"] for r in rows]
    wi = [r["pred_with_prior"] for r in rows]
    n = len(rows)
    has_change = "change" in rows[0]
    change = np.array([str(r.get("change", "1")) in ("1", "True", "true") for r in rows])
    print(f"Loaded {n} cases.  change={int(change.sum())}  no-change={int((~change).sum())}"
          + ("" if has_change else "   (no 'change' column -> overall only)"))

    # ---- per-case precompute (fast to bootstrap) ----
    refs_tok = [tok(r) for r in refs]; wo_tok = [tok(x) for x in wo]; wi_tok = [tok(x) for x in wi]
    rl_wo = np.array([ROUGE.score(refs[i], wo[i])["rougeL"].fmeasure for i in range(n)])
    rl_wi = np.array([ROUGE.score(refs[i], wi[i])["rougeL"].fmeasure for i in range(n)])
    def _met(a, b):
        try: return meteor_score([tok(a)], tok(b))
        except Exception: return 0.0
    mt_wo = np.array([_met(refs[i], wo[i]) for i in range(n)])
    mt_wi = np.array([_met(refs[i], wi[i]) for i in range(n)])

    def mean_pair(a0, a1): return lambda idx: (float(a0[idx].mean()), float(a1[idx].mean()))
    def bleu_pair(idx):
        rr = [[refs_tok[i]] for i in idx]
        return (corpus_bleu(rr, [wo_tok[i] for i in idx], weights=W4, smoothing_function=SM),
                corpus_bleu(rr, [wi_tok[i] for i in idx], weights=W4, smoothing_function=SM))

    metrics = [
        ("BLEU-4", bleu_pair, True),
        ("ROUGE-L", mean_pair(rl_wo, rl_wi), True),
        ("METEOR", mean_pair(mt_wo, mt_wi), True),
    ]

    # ---- RadGraph-F1 (optional, per-case -> bootstrappable) ----
    try:
        from radgraph import F1RadGraph
        print("Scoring RadGraph-F1 (partial) ...")
        f1rg = F1RadGraph(reward_level="partial")
        _, rg_wo, _, _ = f1rg(hyps=wo, refs=refs)
        _, rg_wi, _, _ = f1rg(hyps=wi, refs=refs)
        rg_wo = np.array(rg_wo, float); rg_wi = np.array(rg_wi, float)
        metrics.append(("RadGraph-F1", mean_pair(rg_wo, rg_wi), True))
    except Exception as e:
        print(f"(RadGraph skipped: {e})")

    strata = [("overall", np.arange(n))]
    if has_change:
        strata += [("change", np.where(change)[0]), ("no-change", np.where(~change)[0])]

    print(f"\n=== STRATIFIED ABLATION  (with - without prior) ===")
    print(f"Bootstrap: {B} paired resamples; p = 2-sided (fraction of resampled \u0394 crossing 0).\n")
    results = {"n": n, "n_change": int(change.sum()), "n_nochange": int((~change).sum()),
               "bootstrap": B, "metrics": {}}
    for name, ev, avail in metrics:
        print(name)
        results["metrics"][name] = {}
        for sname, sidx in strata:
            w0, w1, d, lo, hi, p = boot(ev, sidx, B)
            sig = "*" if (not np.isnan(p) and p < 0.05) else " "
            print(f"  {sname:10s} n={len(sidx):5d}   w/o {w0:.4f}   with {w1:.4f}   "
                  f"\u0394 {d:+.4f} {sig}  95% CI [{lo:+.4f}, {hi:+.4f}]  p={p:.3f}")
            results["metrics"][name][sname] = dict(n=int(len(sidx)), without=w0, with_=w1,
                                                   delta=d, ci_lo=lo, ci_hi=hi, p=p)
        print()

    # ---- CheXbert-F1: per-stratum point estimates (package-native, batched) ----
    try:
        from f1chexbert import F1CheXbert
        print("Scoring CheXbert-F1 (point estimates per stratum) ...")
        cb = F1CheXbert()
        def cb_f1(idx):
            r = [refs[i] for i in idx]
            _, _, crp_wo, _ = cb(hyps=[wo[i] for i in idx], refs=r)
            _, _, crp_wi, _ = cb(hyps=[wi[i] for i in idx], refs=r)
            return crp_wo, crp_wi
        for lvl in ("micro avg", "macro avg"):
            label = f"CheXbert-F1 {lvl.split()[0]} (point)"
            print(label)
            results["metrics"][label] = {}
            for sname, sidx in strata:
                crp_wo, crp_wi = cb_f1(sidx)
                a = crp_wo[lvl]["f1-score"]; c = crp_wi[lvl]["f1-score"]
                print(f"  {sname:10s} n={len(sidx):5d}   w/o {a:.4f}   with {c:.4f}   \u0394 {c-a:+.4f}")
                results["metrics"][label][sname] = dict(n=int(len(sidx)), without=a, with_=c, delta=c - a)
            print()
    except Exception as e:
        print(f"(CheXbert-F1 skipped: {e})")

    json.dump(results, open(args.out_json, "w"), indent=2, default=float)
    print(f"Wrote {args.out_json}")
    print("Note: '*' marks bootstrap p<0.05. CheXbert rows are point estimates "
          "(stable at large n; CIs would need per-case label vectors).")


if __name__ == "__main__":
    main()
