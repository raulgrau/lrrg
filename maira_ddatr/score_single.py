#!/usr/bin/env python3
"""
score_single.py -- score a SINGLE-model predictions JSON (as written by infer.py),
stratified by change vs no-change, with two modes:

  1. one model  (--preds only):
        per-stratum POINT estimates for BLEU-4, ROUGE-L, METEOR, RadGraph-F1,
        CheXbert-F1, each with a bootstrap 95% CI on the absolute value.

  2. two models (--preds vs --baseline):
        the DDaTR-vs-baseline DELTA per stratum with a paired bootstrap 95% CI
        and 2-sided p-value -- the same statistics as lrrg_ablation/score.py, but
        comparing two prediction FILES instead of with/without-prior columns.
        The two files are aligned by study_id (inner join).

Predictions JSON: a list of records
    [{"study_id","generated","reference","has_prior","change_label"}, ...]
or the --flat {study_id: findings} form (then pass --refs for references).

Run in venv_score on cgpool (CheXbert/RadGraph live there):
    python score_single.py --preds preds_test.json
    python score_single.py --preds ddatr_m1.json --baseline base_maira2.json
"""

import argparse
import csv
import json

import numpy as np
import nltk
from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu
from nltk.translate.meteor_score import meteor_score
from rouge_score import rouge_scorer

for pkg in ("wordnet", "omw-1.4"):
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

SM = SmoothingFunction().method1
W4 = (0.25, 0.25, 0.25, 0.25)
ROUGE = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
RNG = np.random.default_rng(0)


def tok(s):
    return (s or "").lower().split()


def _is_change(v):
    """Normalize a change_label (bool/int/str/None) to True/False/None."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "change", "yes")


def _load_records(path):
    """Return {study_id: {'generated','reference','change'}} from a preds JSON."""
    data = json.load(open(path))
    out = {}
    if isinstance(data, dict):                       # --flat form: {sid: findings}
        for sid, gen in data.items():
            out[str(sid)] = {"generated": gen, "reference": None, "change": None}
        return out
    for r in data:
        sid = str(r["study_id"])
        out[sid] = {"generated": r.get("generated", ""),
                    "reference": r.get("reference"),
                    "change": _is_change(r.get("change_label"))}
    return out


# --------------------------------------------------------------------------- #
#  per-case metric vectors (fast to bootstrap)
# --------------------------------------------------------------------------- #
def surface_vectors(refs, hyps):
    n = len(refs)
    rl = np.array([ROUGE.score(refs[i], hyps[i])["rougeL"].fmeasure for i in range(n)])

    def _met(a, b):
        try:
            return meteor_score([tok(a)], tok(b))
        except Exception:
            return 0.0
    mt = np.array([_met(refs[i], hyps[i]) for i in range(n)])
    return rl, mt


def bleu_on(idx, refs_tok, hyps_tok):
    rr = [[refs_tok[i]] for i in idx]
    return corpus_bleu(rr, [hyps_tok[i] for i in idx], weights=W4, smoothing_function=SM)


def boot_abs(metric_of_idx, idx, B):
    """Point estimate + bootstrap 95% CI for a single-model absolute metric."""
    idx = np.asarray(idx)
    if len(idx) == 0:
        return float("nan"), float("nan"), float("nan")
    pt = metric_of_idx(idx)
    vals = np.empty(B)
    n = len(idx)
    for b in range(B):
        vals[b] = metric_of_idx(idx[RNG.integers(0, n, n)])
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return pt, lo, hi


def boot_delta(metric_of_idx_a, metric_of_idx_b, idx, B):
    """Paired bootstrap of (b - a): point deltas + CI + 2-sided p."""
    idx = np.asarray(idx)
    if len(idx) == 0:
        return (float("nan"),) * 6
    a0, b0 = metric_of_idx_a(idx), metric_of_idx_b(idx)
    n = len(idx)
    deltas = np.empty(B)
    for b in range(B):
        s = idx[RNG.integers(0, n, n)]
        deltas[b] = metric_of_idx_b(s) - metric_of_idx_a(s)
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    p = min(1.0, 2.0 * min((deltas <= 0).mean(), (deltas >= 0).mean()))
    return a0, b0, b0 - a0, lo, hi, p


def strata_of(changes):
    n = len(changes)
    strata = [("overall", np.arange(n))]
    have = np.array([c is not None for c in changes])
    if have.any():
        chg = np.array([c is True for c in changes])
        strata.append(("change", np.where(chg & have)[0]))
        strata.append(("no-change", np.where(~chg & have)[0]))
    return strata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True, help="DDaTR predictions JSON")
    ap.add_argument("--baseline", default="", help="optional 2nd model JSON to compare against")
    ap.add_argument("--refs", default="", help="CSV/JSON of study_id->reference (only if --flat preds)")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--out-json", default="results_single.json")
    args = ap.parse_args()
    B = args.bootstrap

    preds = _load_records(args.preds)

    # optional external references (for --flat preds that lack them)
    ext_ref = {}
    if args.refs:
        if args.refs.endswith(".json"):
            ext_ref = {str(k): v for k, v in json.load(open(args.refs)).items()}
        else:
            for row in csv.DictReader(open(args.refs)):
                ext_ref[str(row["study_id"])] = row.get("reference", "")

    if args.baseline:
        base = _load_records(args.baseline)
        ids = [s for s in preds if s in base]        # inner join on study_id
        ids.sort()
        print(f"Comparing on {len(ids)} shared studies "
              f"(preds {len(preds)}, baseline {len(base)}).")
        refs = [preds[s]["reference"] or ext_ref.get(s, "") for s in ids]
        hyp_ddatr = [preds[s]["generated"] for s in ids]
        hyp_base = [base[s]["generated"] for s in ids]
        changes = [preds[s]["change"] for s in ids]
    else:
        ids = sorted(preds)
        refs = [preds[s]["reference"] or ext_ref.get(s, "") for s in ids]
        hyp_ddatr = [preds[s]["generated"] for s in ids]
        hyp_base = None
        changes = [preds[s]["change"] for s in ids]

    if any(not r for r in refs):
        miss = sum(1 for r in refs if not r)
        print(f"WARNING: {miss}/{len(refs)} studies have no reference "
              f"(pass --refs, or check the manifest carried 'findings').")

    strata = strata_of(changes)
    n_chg = sum(1 for c in changes if c is True)
    n_noc = sum(1 for c in changes if c is False)
    print(f"Loaded {len(ids)} studies.  change={n_chg}  no-change={n_noc}\n")

    results = {"n": len(ids), "n_change": n_chg, "n_nochange": n_noc,
               "bootstrap": B, "paired": bool(args.baseline), "metrics": {}}

    # ---- surface metric vectors ----
    refs_tok = [tok(r) for r in refs]
    dd_tok = [tok(h) for h in hyp_ddatr]
    rl_dd, mt_dd = surface_vectors(refs, hyp_ddatr)
    metric_defs = [
        ("ROUGE-L", lambda idx, a=rl_dd: float(a[idx].mean())),
        ("METEOR", lambda idx, a=mt_dd: float(a[idx].mean())),
        ("BLEU-4", lambda idx: bleu_on(idx, refs_tok, dd_tok)),
    ]
    base_metric_defs = None
    if hyp_base is not None:
        bs_tok = [tok(h) for h in hyp_base]
        rl_bs, mt_bs = surface_vectors(refs, hyp_base)
        base_metric_defs = {
            "ROUGE-L": lambda idx, a=rl_bs: float(a[idx].mean()),
            "METEOR": lambda idx, a=mt_bs: float(a[idx].mean()),
            "BLEU-4": lambda idx: bleu_on(idx, refs_tok, bs_tok),
        }

    # ---- RadGraph-F1 (per-case -> bootstrappable) ----
    try:
        from radgraph import F1RadGraph
        print("Scoring RadGraph-F1 (partial) ...")
        f1rg = F1RadGraph(reward_level="partial")
        _, rg_dd, _, _ = f1rg(hyps=hyp_ddatr, refs=refs)
        rg_dd = np.array(rg_dd, float)
        metric_defs.append(("RadGraph-F1", lambda idx, a=rg_dd: float(a[idx].mean())))
        if hyp_base is not None:
            _, rg_bs, _, _ = f1rg(hyps=hyp_base, refs=refs)
            rg_bs = np.array(rg_bs, float)
            base_metric_defs["RadGraph-F1"] = lambda idx, a=rg_bs: float(a[idx].mean())
    except Exception as e:
        print(f"(RadGraph skipped: {e})")

    # ---- report surface + RadGraph ----
    hdr = "=== DDaTR vs BASELINE (delta = DDaTR - baseline) ===" if hyp_base is not None \
          else "=== DDaTR single-model (point estimate + 95% CI) ==="
    print("\n" + hdr)
    print(f"Bootstrap: {B} resamples.\n")
    for name, fn in metric_defs:
        print(name)
        results["metrics"][name] = {}
        for sname, sidx in strata:
            if hyp_base is not None:
                a0, b0, d, lo, hi, p = boot_delta(base_metric_defs[name], fn, sidx, B)
                sig = "*" if (not np.isnan(p) and p < 0.05) else " "
                print(f"  {sname:10s} n={len(sidx):5d}   base {a0:.4f}   ddatr {b0:.4f}   "
                      f"Δ {d:+.4f} {sig}  95% CI [{lo:+.4f},{hi:+.4f}]  p={p:.3f}")
                results["metrics"][name][sname] = dict(n=int(len(sidx)), base=a0, ddatr=b0,
                                                       delta=d, ci_lo=lo, ci_hi=hi, p=p)
            else:
                pt, lo, hi = boot_abs(fn, sidx, B)
                print(f"  {sname:10s} n={len(sidx):5d}   {pt:.4f}   95% CI [{lo:.4f},{hi:.4f}]")
                results["metrics"][name][sname] = dict(n=int(len(sidx)), value=pt, ci_lo=lo, ci_hi=hi)
        print()

    # ---- CheXbert-F1 (per-stratum point estimates; package-native) ----
    try:
        from f1chexbert import F1CheXbert
        print("Scoring CheXbert-F1 ...")
        cb = F1CheXbert()

        def cb_f1(hyps, idx):
            r = [refs[i] for i in idx]
            _, _, crp, _ = cb(hyps=[hyps[i] for i in idx], refs=r)
            return crp
        for lvl in ("micro avg", "macro avg"):
            label = f"CheXbert-F1 {lvl.split()[0]}"
            print(label)
            results["metrics"][label] = {}
            for sname, sidx in strata:
                dd = cb_f1(hyp_ddatr, sidx)[lvl]["f1-score"]
                if hyp_base is not None:
                    bs = cb_f1(hyp_base, sidx)[lvl]["f1-score"]
                    print(f"  {sname:10s} n={len(sidx):5d}   base {bs:.4f}   ddatr {dd:.4f}   "
                          f"Δ {dd-bs:+.4f}")
                    results["metrics"][label][sname] = dict(n=int(len(sidx)), base=bs,
                                                            ddatr=dd, delta=dd - bs)
                else:
                    print(f"  {sname:10s} n={len(sidx):5d}   {dd:.4f}")
                    results["metrics"][label][sname] = dict(n=int(len(sidx)), value=dd)
            print()
    except Exception as e:
        print(f"(CheXbert-F1 skipped: {e})")

    json.dump(results, open(args.out_json, "w"), indent=2, default=float)
    print(f"Wrote {args.out_json}")
    print("Note: '*' marks bootstrap p<0.05 (delta mode). CheXbert rows are point "
          "estimates. The headline is the CHANGE stratum: DDaTR should help there.")


if __name__ == "__main__":
    main()
