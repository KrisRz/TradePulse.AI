"""Meta-labeler over EMA20/100 — implementation of the PRE-REGISTERED design.

Executes docs/METALABELER_DESIGN_2026-08-08.md exactly; any deviation is a
bug or a separately-committed design change. Summary of what is fixed there:

- data: data/ml/events_features.csv (128 events, labels = net round-trip
  return after costs);
- features: mvrv_z, funding_cum30, vol_pctl_1y, btc_trend_gap,
  dd_from_1y_high + ONE shared missing-era indicator; own trend_gap et al.
  deliberately excluded (information advantage);
- splits: purged 5-fold on calendar blocks shared by all assets; purge by
  actual [entry, exit] interval overlap, cross-asset; embargo 30 days
  appended to test intervals; fold count drops to 4 if any train set
  falls below 90 events after purging;
- model: Pipeline(median imputer -> scaler -> LogisticRegression L2),
  C chosen by nested purged 3-fold on weighted log-loss over
  {0.01, 0.03, 0.1, 0.3}; sample_weight = |net_return|; no class-balance
  corrections; no CalibratedClassifierCV (curve is inspected only);
- usage: de Prado bet size m = 2*Phi(z)-1, z = (p-.5)/sqrt(p(1-p)),
  squashed to the 0.5x-1.5x attenuation band: size = 1 + 0.5*m;
- verdict (mechanical): attenuated strategy must beat the ungated events on
  per-event Sharpe over pooled OOF predictions AND on >=3 of 5 CPCV paths;
- diagnostics (never selection criteria): top-5 winners' probability ranks
  (any below median = red flag), leave-one-asset-out, calibration curve;
- trial ledger: this run = trial #1 (logit) and #2 (XGBoost benchmark,
  fixed params, expected to lose). Nested C selection counts as one trial.

Usage: PYTHONPATH=. .venv/bin/python scripts/research/metalabeler.py
"""

from __future__ import annotations

import json
import pathlib
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data" / "ml" / "events_features.csv"

FEATURES = ["mvrv_z", "funding_cum30", "vol_pctl_1y",
            "btc_trend_gap", "dd_from_1y_high"]
EMBARGO = pd.Timedelta(days=30)
C_GRID = [0.01, 0.03, 0.1, 0.3]
N_FOLDS = 5
MIN_TRAIN = 90
SEED = 0


# --------------------------------------------------------------------------- #
# Splits
# --------------------------------------------------------------------------- #
def calendar_blocks(df: pd.DataFrame, n: int) -> list[np.ndarray]:
    """Contiguous calendar blocks with ~equal event counts, asset-blind."""
    order = df.sort_values("entry").index.to_numpy()
    return [b for b in np.array_split(order, n) if len(b)]


def purged_train(df: pd.DataFrame, test_idx: np.ndarray) -> np.ndarray:
    """All non-test events whose [entry, exit] does not overlap any test
    event's [entry, exit + EMBARGO], across ALL assets."""
    test = df.loc[test_idx]
    s0 = test["entry"].min()                 # blocks are contiguous, so the
    s1 = test["exit"].max() + EMBARGO        # union interval is exact enough
    rest = df.drop(index=test_idx)
    keep = (rest["exit"] < s0) | (rest["entry"] > s1)
    return rest.index[keep].to_numpy()


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
def logit(c: float):
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(penalty="l2", C=c, solver="lbfgs", max_iter=5000),
    )


def fit_predict(model, df, train_idx, test_idx, X_cols):
    Xtr, Xte = df.loc[train_idx, X_cols], df.loc[test_idx, X_cols]
    w = df.loc[train_idx, "net_return"].abs()
    last = model.steps[-1][0] if hasattr(model, "steps") else None
    if last:
        model.fit(Xtr, df.loc[train_idx, "win"], **{f"{last}__sample_weight": w})
    else:
        model.fit(Xtr, df.loc[train_idx, "win"], sample_weight=w)
    return model.predict_proba(Xte)[:, 1]


def pick_c(df: pd.DataFrame, train_idx: np.ndarray, X_cols) -> float:
    """Nested purged 3-fold on weighted log-loss (counts as ONE trial)."""
    sub = df.loc[train_idx]
    losses = {c: [] for c in C_GRID}
    for inner_test in calendar_blocks(sub, 3):
        inner_train = purged_train(sub, inner_test)
        if len(inner_train) < 30 or sub.loc[inner_test, "win"].nunique() < 2:
            continue
        for c in C_GRID:
            p = fit_predict(logit(c), sub, inner_train, inner_test, X_cols)
            losses[c].append(log_loss(
                sub.loc[inner_test, "win"], p, labels=[False, True],
                sample_weight=sub.loc[inner_test, "net_return"].abs()))
    means = {c: np.mean(v) for c, v in losses.items() if v}
    return min(means, key=means.get) if means else 0.1


# --------------------------------------------------------------------------- #
# Sizing and scoring
# --------------------------------------------------------------------------- #
def size_from_p(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    z = (p - 0.5) / np.sqrt(p * (1 - p))
    return 1.0 + 0.5 * (2.0 * norm.cdf(z) - 1.0)      # 0.5x .. 1.5x


def sharpe_ev(r: pd.Series) -> float:
    return float(r.mean() / r.std()) if r.std() > 0 else 0.0


# --------------------------------------------------------------------------- #
def run_outer(df, model_name, X_cols):
    """Purged K-fold OOF probabilities. Returns (probs, chosen Cs)."""
    blocks = calendar_blocks(df, N_FOLDS)
    trains = [purged_train(df, b) for b in blocks]
    if min(len(t) for t in trains) < MIN_TRAIN:
        blocks = calendar_blocks(df, N_FOLDS - 1)
        trains = [purged_train(df, b) for b in blocks]
        print(f"  [fold guard] train<{MIN_TRAIN} -> using {len(blocks)} folds")
    probs = pd.Series(np.nan, index=df.index)
    cs = []
    for test_idx, train_idx in zip(blocks, trains):
        if model_name == "logit":
            c = pick_c(df, train_idx, X_cols)
            cs.append(c)
            model = logit(c)
        else:
            import xgboost as xgb
            model = xgb.XGBClassifier(
                max_depth=2, min_child_weight=5, learning_rate=0.1,
                n_estimators=200, subsample=0.8, colsample_bytree=0.8,
                reg_lambda=5.0, random_state=SEED, eval_metric="logloss")
        probs.loc[test_idx] = fit_predict(model, df, train_idx, test_idx, X_cols)
        print(f"  fold test={len(test_idx)} train={len(train_idx)}"
              f" purged={len(df) - len(test_idx) - len(train_idx)}"
              + (f" C={cs[-1]}" if model_name == "logit" else ""))
    return probs, cs


def evaluate(df, probs, label):
    got = probs.notna()
    ev = df.loc[got].sort_values("entry")
    p = probs.loc[ev.index].to_numpy()
    plain = ev["net_return"]
    gated = plain * size_from_p(p)
    rng = np.random.default_rng(SEED)
    diffs = []
    for _ in range(2000):
        i = rng.integers(0, len(ev), len(ev))
        diffs.append(sharpe_ev(gated.iloc[i]) - sharpe_ev(plain.iloc[i]))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    print(f"\n  [{label}] events scored: {got.sum()}/{len(df)}")
    print(f"  per-event Sharpe : plain {sharpe_ev(plain):+.3f}"
          f"  attenuated {sharpe_ev(gated):+.3f}"
          f"  diff {sharpe_ev(gated) - sharpe_ev(plain):+.3f}"
          f"  [95% CI {lo:+.3f} .. {hi:+.3f}]")
    print(f"  sum net return   : plain {plain.sum():+.3f}"
          f"  attenuated {gated.sum():+.3f}")
    return sharpe_ev(gated) - sharpe_ev(plain)


def top5_diagnostic(df, probs):
    got = df.loc[probs.notna()].copy()
    got["p"] = probs.loc[got.index]
    got["p_rank"] = got["p"].rank(pct=True)
    top5 = got.nlargest(5, "net_return")
    print("\n  top-5 winners' probability ranks (red flag if any < 0.50):")
    flagged = 0
    for _, r in top5.iterrows():
        flag = " <-- RED FLAG" if r["p_rank"] < 0.5 else ""
        flagged += r["p_rank"] < 0.5
        print(f"    {r['asset']:<9} {str(r['entry'])[:10]}"
              f" ret={r['net_return']:+.2f} p={r['p']:.3f}"
              f" rank={r['p_rank']:.2f}{flag}")
    return int(flagged)


def loao(df, X_cols, c):
    print("\n  leave-one-asset-out (diagnostic, C fixed at outer median):")
    rows = []
    for asset in df["asset"].unique():
        test_idx = df.index[df["asset"] == asset].to_numpy()
        train_idx = df.index[df["asset"] != asset].to_numpy()
        p = fit_predict(logit(c), df, train_idx, test_idx, X_cols)
        plain = df.loc[test_idx, "net_return"]
        gated = plain * size_from_p(p)
        d = sharpe_ev(gated) - sharpe_ev(plain)
        rows.append(d)
        print(f"    {asset:<9} n={len(test_idx):>3}  Sharpe diff {d:+.3f}")
    print(f"    better in {sum(1 for d in rows if d > 0)}/{len(rows)} assets")


def cpcv(df, X_cols, c):
    """CPCV(6,2): 15 splits, 5 paths; C fixed (no nested — one trial)."""
    groups = calendar_blocks(df, 6)
    gid = {i: g for i, g in enumerate(groups)}
    paths = [pd.Series(np.nan, index=df.index) for _ in range(5)]
    seen = {i: 0 for i in gid}
    for combo in combinations(range(6), 2):
        test_idx = np.concatenate([gid[i] for i in combo])
        # purge against each test group's own contiguous span
        train_idx = df.drop(index=test_idx).index.to_numpy()
        for i in combo:
            sub = df.loc[np.concatenate([train_idx, gid[i]])]
            train_idx = purged_train(sub, gid[i])
        for i in combo:
            p = fit_predict(logit(c), df, train_idx, gid[i], X_cols)
            paths[seen[i]].loc[gid[i]] = p
            seen[i] += 1
    print("\n  CPCV(6,2) — 5 paths, Sharpe diff attenuated vs plain:")
    wins = 0
    for k, pr in enumerate(paths):
        got = pr.notna()
        plain = df.loc[got, "net_return"]
        gated = plain * size_from_p(pr.loc[got].to_numpy())
        d = sharpe_ev(gated) - sharpe_ev(plain)
        wins += d > 0
        print(f"    path {k + 1}: {d:+.3f} ({got.sum()} events)")
    print(f"    attenuated wins on {wins}/5 paths")
    return wins


def main() -> int:
    df = pd.read_csv(EVENTS)
    for col in ("entry", "exit"):
        df[col] = pd.to_datetime(df[col], utc=True, format="mixed")
    df["missing_era"] = df[FEATURES].isna().any(axis=1).astype(float)
    X_cols = FEATURES + ["missing_era"]
    print(f"events: {len(df)}  features: {X_cols}")
    print(f"design: docs/METALABELER_DESIGN_2026-08-08.md (pre-registered)")

    print(f"\nTRIAL #1 — logit L2, purged {N_FOLDS}-fold, embargo 30d")
    probs, cs = run_outer(df, "logit", X_cols)
    diff = evaluate(df, probs, "logit OOF")
    flagged = top5_diagnostic(df, probs)
    c_med = float(np.median(cs)) if cs else 0.1
    loao(df, X_cols, c_med)
    path_wins = cpcv(df, X_cols, c_med)

    print(f"\nTRIAL #2 — XGBoost benchmark (fixed params, native NaN)")
    probs_x, _ = run_outer(df, "xgb", X_cols)
    diff_x = evaluate(df, probs_x, "xgb OOF")

    verdict = {
        "pooled OOF: attenuated Sharpe > plain": bool(diff > 0),
        "CPCV: attenuated wins >=3/5 paths": bool(path_wins >= 3),
    }
    accepted = all(verdict.values())
    print(f"\n{'=' * 74}\nVERDICT (mechanical, rule from the design doc)")
    for k, ok in verdict.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {k}")
    print(f"  top-5 red flags: {flagged} (diagnostic, not a criterion)")
    print(f"\n  meta-labeler: {'ACCEPT -> M4 harness next' if accepted else 'REJECT -> keep plain EMA20/100'}")

    out = ROOT / "docs" / "metalabeler_result.json"
    out.write_text(json.dumps({
        "trial_1_logit": {"sharpe_diff": diff, "chosen_C": cs,
                          "cpcv_path_wins": path_wins,
                          "top5_red_flags": flagged},
        "trial_2_xgb": {"sharpe_diff": diff_x},
        "verdict": verdict, "accepted": accepted,
    }, indent=2, default=str))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
