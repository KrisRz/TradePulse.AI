"""M5 gate evaluation — pre-registered thresholds + DSR/MinTRL statistics.

Evaluates the live paper-trading window (decision log + trades) against the
plan §3 gates, with the deflated-Sharpe machinery of Bailey & López de Prado
(SSRN 2460551) as the statistical honesty check: is the observed track record
long enough to distinguish skill from luck, given how many strategy variants
were tried before settling on this one?

PRE-REGISTERED RULES (fixed 2026-07-25, BEFORE the first evaluation — changing
them at evaluation time would be fitting the criteria to the outcome):

1. Earliest evaluation: 2026-09-10 (8 weeks from window start 2026-07-16).
   Before that date the script only reports; it never issues PASS/FAIL.
2. Activity rule: the hard gates are only evaluable with >= 2 closed round
   trips AND >= 10 days spent in a position. A trend-following strategy that
   stayed FLAT through a bear market produced no evidence either way -> the
   verdict is INCONCLUSIVE_EXTEND: keep papering, re-evaluate every 4 weeks.
   (Historically EMA20/100 1d trades ~3.4x/year and is in the market 53% of
   the time, so a quiet 8 weeks is a real possibility, not a failure.)
3. Hard gates (plan §3): max drawdown <= 25%, profit factor >= 1.3,
   net P&L > 0, fee drag < 20% of gross profit, live tracking error < 10%
   (supplied externally when the M5.3 comparison is run; SKIPPED until then).
4. Statistical readout (advisory, not a hard gate): PSR vs SR*=0, DSR
   deflated for N_TRIALS=30 prior strategy variants with trial-SR variance
   0.3 (conservative: M4 tried EMA/RSI/regime variants, 15m/4h/1d timeframes,
   ETH, sizing and ML filters), and MinTRL@95% — "how many more days of track
   record until the Sharpe is statistically defensible".

All Sharpe/skew/kurtosis inputs to PSR/DSR/MinTRL are PER-BAR (non-annualized)
as the formulas require; the annualized Sharpe (365d, matching
``backtesting.metrics``) is reported alongside.

Usage:
    # against prod DynamoDB (needs AWS creds; read-only)
    python -m app.backend.paper_trading.gate --source dynamodb
    # against a local paper_state file
    python -m app.backend.paper_trading.gate --source local
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import pandas as pd

# --------------------------------------------------------------------------- #
# Pre-registered constants — do not edit inside the M5 window (see docstring).
# --------------------------------------------------------------------------- #
WINDOW_START = date(2026, 7, 16)
EARLIEST_EVAL = date(2026, 9, 10)
MIN_ROUND_TRIPS = 2
MIN_DAYS_IN_MARKET = 10
REEVALUATE_EVERY_DAYS = 28
MAX_DRAWDOWN_LIMIT = 0.25
MIN_PROFIT_FACTOR = 1.3
MAX_FEE_DRAG = 0.20
MAX_TRACKING_ERROR = 0.10
N_TRIALS = 30
TRIAL_SR_VAR = 0.3
PSR_CONFIDENCE = 0.95
_EULER_GAMMA = 0.5772156649015329

_SECONDS_PER_YEAR = 365.0 * 24 * 3600   # crypto trades 24/7 (= metrics.py)


# --------------------------------------------------------------------------- #
# Normal distribution without scipy (Lambda-light, no new dependencies).
# --------------------------------------------------------------------------- #
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation, ~1e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if p > p_high:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)


# --------------------------------------------------------------------------- #
# Bailey & López de Prado statistics (per-bar Sharpe units throughout).
# --------------------------------------------------------------------------- #
def probabilistic_sharpe(sr_hat: float, sr_star: float, n_obs: int,
                         skew: float, kurt: float) -> float:
    """P(true SR > sr_star | observed sr_hat over n_obs non-normal returns)."""
    if n_obs < 2:
        return float("nan")
    denom = 1.0 - skew * sr_hat + (kurt - 1.0) / 4.0 * sr_hat ** 2
    if denom <= 0:
        return float("nan")
    z = (sr_hat - sr_star) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    return norm_cdf(z)


def expected_max_sharpe(n_trials: int, trial_sr_var: float) -> float:
    """E[max SR] across n_trials of noise — the bar a survivor must clear."""
    if n_trials <= 1:
        return 0.0
    return math.sqrt(trial_sr_var) * (
        (1.0 - _EULER_GAMMA) * norm_ppf(1.0 - 1.0 / n_trials)
        + _EULER_GAMMA * norm_ppf(1.0 - 1.0 / (n_trials * math.e)))


def deflated_sharpe(sr_hat: float, n_obs: int, skew: float, kurt: float,
                    n_trials: int = N_TRIALS,
                    trial_sr_var: float = TRIAL_SR_VAR) -> float:
    """DSR = PSR evaluated against the expected-max-SR of the trials."""
    return probabilistic_sharpe(
        sr_hat, expected_max_sharpe(n_trials, trial_sr_var), n_obs, skew, kurt)


def min_track_record_length(sr_hat: float, sr_star: float, skew: float,
                            kurt: float,
                            confidence: float = PSR_CONFIDENCE) -> float:
    """Observations needed for PSR(sr_star) >= confidence. inf if sr_hat<=sr_star."""
    if sr_hat <= sr_star:
        return float("inf")
    denom = 1.0 - skew * sr_hat + (kurt - 1.0) / 4.0 * sr_hat ** 2
    if denom <= 0:
        return float("inf")
    return 1.0 + denom * (norm_ppf(confidence) / (sr_hat - sr_star)) ** 2


# --------------------------------------------------------------------------- #
# Gate evaluation
# --------------------------------------------------------------------------- #
@dataclass
class GateInputs:
    equity: pd.Series          # MTM equity per processed bar (UTC index)
    trades: list[dict]         # closed round trips (PaperTrade dicts)
    initial_capital: float
    open_position_days: int    # days currently in an open (unclosed) position
    tracking_error: Optional[float] = None   # M5.3 input, when available


def _trade_stats(trades: list[dict]) -> dict:
    """Profit factor / fee drag from closed trades (metrics.py conventions)."""
    if not trades:
        return {"round_trips": 0, "profit_factor": None, "fee_drag": None,
                "win_rate": None, "days_in_market_closed": 0}
    nets = [t["net_return"] for t in trades]
    # Gross return per trade (after slippage, before fees) reconstructed from
    # fills — same definition as the backtest's gross_return.
    grosses = [t["side"] * (t["exit_price"] / t["entry_price"] - 1.0)
               for t in trades]
    wins = [r for r in nets if r > 0]
    losses = [-r for r in nets if r <= 0]
    pf = (sum(wins) / sum(losses)) if sum(losses) > 0 else float("inf")
    gross_profit = sum(g for g in grosses if g > 0)
    drag = sum(grosses) - sum(nets)          # cost paid, in return terms
    fee_drag = (drag / gross_profit) if gross_profit > 0 else None
    days = 0
    for t in trades:
        held = (pd.Timestamp(t["exit_time"]) - pd.Timestamp(t["entry_time"]))
        days += max(held.days, 0)
    return {"round_trips": len(trades), "profit_factor": pf,
            "fee_drag": fee_drag, "win_rate": len(wins) / len(nets),
            "days_in_market_closed": days}


def evaluate(inputs: GateInputs, as_of: date) -> dict:
    """Full pre-registered evaluation. Pure — no I/O, fully testable."""
    eq = inputs.equity.dropna().sort_index()
    window_days = (as_of - WINDOW_START).days
    report: dict[str, Any] = {
        "as_of": str(as_of),
        "window_start": str(WINDOW_START),
        "window_days": window_days,
        "earliest_eval": str(EARLIEST_EVAL),
        "bars": int(len(eq)),
    }

    # -- performance readout (always reported) --------------------------- #
    rets = eq.pct_change().dropna()
    net_pnl = float(eq.iloc[-1] - inputs.initial_capital) if len(eq) else 0.0
    running_max = eq.cummax()
    max_dd = float((eq / running_max - 1.0).min()) if len(eq) else 0.0
    sd = float(rets.std(ddof=1)) if len(rets) >= 2 else 0.0
    sr_bar = float(rets.mean() / sd) if sd > 0 else None
    sharpe_ann = sr_bar * math.sqrt(365.0) if sr_bar is not None else None

    tstats = _trade_stats(inputs.trades)
    days_in_market = tstats["days_in_market_closed"] + inputs.open_position_days
    report["performance"] = {
        "final_equity": float(eq.iloc[-1]) if len(eq) else inputs.initial_capital,
        "net_pnl": net_pnl,
        "max_drawdown": max_dd,
        "sharpe_annualized": sharpe_ann,
        "days_in_market": days_in_market,
        **tstats,
    }

    # -- statistical readout (advisory) ----------------------------------- #
    if sr_bar is not None and len(rets) >= 3:
        skew = float(rets.skew())
        kurt = float(rets.kurt()) + 3.0            # pandas gives EXCESS kurtosis
        sr_star = expected_max_sharpe(N_TRIALS, TRIAL_SR_VAR)
        psr0 = probabilistic_sharpe(sr_bar, 0.0, len(rets), skew, kurt)
        dsr = deflated_sharpe(sr_bar, len(rets), skew, kurt)
        mintrl = min_track_record_length(sr_bar, 0.0, skew, kurt)
        report["statistics"] = {
            "sr_per_bar": sr_bar, "skew": skew, "kurtosis": kurt,
            "psr_vs_zero": psr0, "expected_max_sr_of_trials": sr_star,
            "dsr": dsr,
            "min_trl_days_vs_zero": mintrl,
            "min_trl_days_remaining": max(0.0, mintrl - len(rets))
            if math.isfinite(mintrl) else None,
            "n_trials_assumed": N_TRIALS, "trial_sr_var_assumed": TRIAL_SR_VAR,
        }
    else:
        report["statistics"] = {
            "note": "no return variance yet (flat window) — PSR/DSR undefined"}

    # -- verdict (pre-registered precedence) ------------------------------ #
    if as_of < EARLIEST_EVAL:
        report["verdict"] = "WINDOW_RUNNING"
        report["verdict_reason"] = (
            f"earliest evaluation {EARLIEST_EVAL} — report only, "
            f"{(EARLIEST_EVAL - as_of).days} days to go")
        return report

    if tstats["round_trips"] < MIN_ROUND_TRIPS or days_in_market < MIN_DAYS_IN_MARKET:
        report["verdict"] = "INCONCLUSIVE_EXTEND"
        report["verdict_reason"] = (
            f"activity rule not met (round_trips {tstats['round_trips']} < "
            f"{MIN_ROUND_TRIPS} or days_in_market {days_in_market} < "
            f"{MIN_DAYS_IN_MARKET}) — no evidence either way; keep papering, "
            f"re-evaluate in {REEVALUATE_EVERY_DAYS} days")
        return report

    gates = {
        "max_drawdown<=25%": max_dd >= -MAX_DRAWDOWN_LIMIT,
        "profit_factor>=1.3": tstats["profit_factor"] is not None
        and tstats["profit_factor"] >= MIN_PROFIT_FACTOR,
        "net_pnl>0": net_pnl > 0.0,
        "fee_drag<20%": tstats["fee_drag"] is not None
        and tstats["fee_drag"] < MAX_FEE_DRAG,
    }
    if inputs.tracking_error is not None:
        gates["tracking_error<10%"] = abs(inputs.tracking_error) < MAX_TRACKING_ERROR
    else:
        report["skipped_gates"] = ["tracking_error<10% (M5.3 input not supplied)"]
    report["gates"] = gates
    report["verdict"] = "PASS" if all(gates.values()) else "FAIL"
    failed = [k for k, v in gates.items() if not v]
    report["verdict_reason"] = ("all hard gates met" if not failed
                                else f"failed: {', '.join(failed)}")
    return report


# --------------------------------------------------------------------------- #
# Data loading (decision log + state -> GateInputs)
# --------------------------------------------------------------------------- #
def _inputs_from_records(decisions: list[dict], state: dict) -> GateInputs:
    if not decisions:
        raise RuntimeError("Decision log is empty — nothing to evaluate")
    df = pd.DataFrame(decisions)
    idx = pd.to_datetime(df["bar"], utc=True, format="ISO8601")
    equity = pd.Series(df["equity"].astype(float).values, index=idx).sort_index()
    portfolio = state.get("portfolio", {})
    trades = portfolio.get("trades", [])
    open_days = 0
    if portfolio.get("side", 0) != 0 and portfolio.get("entry_time"):
        open_days = max(
            (equity.index[-1] - pd.Timestamp(portfolio["entry_time"])).days, 0)
    return GateInputs(
        equity=equity, trades=trades,
        initial_capital=float(portfolio.get("initial_capital", 10_000.0)),
        open_position_days=open_days,
    )


def load_dynamodb(table_name: str, partition_key: str) -> GateInputs:
    """Read-only pull of the full decision log + state from DynamoDB."""
    import boto3
    from boto3.dynamodb.conditions import Key

    from .state_store import DynamoDBStateStore

    table = boto3.resource("dynamodb").Table(table_name)
    items: list[dict] = []
    kwargs: dict[str, Any] = {"KeyConditionExpression":
                              Key("pk").eq(partition_key)
                              & Key("sk").begins_with("decision#")}
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    decisions = [DynamoDBStateStore._from_ddb(i) for i in items]

    state_resp = table.get_item(Key={"pk": partition_key, "sk": "state"},
                                ConsistentRead=True)
    if "Item" not in state_resp:
        raise RuntimeError(f"No state item for {partition_key} in {table_name}")
    state = DynamoDBStateStore._from_ddb(state_resp["Item"]["state"])
    return _inputs_from_records(decisions, state)


def load_local(state_path: str) -> GateInputs:
    from .state_store import LocalJsonStateStore

    store = LocalJsonStateStore(state_path)
    state = store.load()
    if state is None:
        raise RuntimeError(f"No local state at {state_path}")
    decisions = []
    if store.decisions_path.exists():
        for line in store.decisions_path.read_text().splitlines():
            try:
                decisions.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return _inputs_from_records(decisions, state)


def _print_report(report: dict) -> None:
    print(f"=== M5 GATE REPORT — as of {report['as_of']} "
          f"(day {report['window_days']} of window) ===")
    perf = report["performance"]
    print(f"bars: {report['bars']}  equity: ${perf['final_equity']:,.2f}  "
          f"net P&L: ${perf['net_pnl']:,.2f}  maxDD: {perf['max_drawdown']*100:.2f}%")
    sr = perf["sharpe_annualized"]
    print(f"sharpe(ann): {sr:.2f}" if sr is not None else "sharpe(ann): n/a (no variance)")
    print(f"round trips: {perf['round_trips']}  days in market: {perf['days_in_market']}  "
          f"PF: {perf['profit_factor']}  fee drag: {perf['fee_drag']}")
    stats = report["statistics"]
    if "dsr" in stats:
        rem = stats["min_trl_days_remaining"]
        print(f"PSR(>0): {stats['psr_vs_zero']:.3f}  DSR(N={stats['n_trials_assumed']}): "
              f"{stats['dsr']:.3f}  MinTRL: {stats['min_trl_days_vs_zero']:.0f} bars"
              + (f" ({rem:.0f} more needed)" if rem is not None else ""))
    else:
        print(f"statistics: {stats['note']}")
    for g in report.get("skipped_gates", []):
        print(f"skipped: {g}")
    if "gates" in report:
        for name, ok in report["gates"].items():
            print(f"  gate {name}: {'PASS' if ok else 'FAIL'}")
    print(f"VERDICT: {report['verdict']} — {report['verdict_reason']}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Evaluate the M5 paper window gates.")
    p.add_argument("--source", choices=["dynamodb", "local"], default="dynamodb")
    p.add_argument("--table", default=os.environ.get("PAPER_STATE_TABLE",
                                                     "tradepulse_paper_bot"))
    p.add_argument("--pk", default="BTCUSDT_1d")
    p.add_argument("--state", default="paper_state/BTCUSDT_1d.json")
    p.add_argument("--tracking-error", type=float, default=None,
                   help="live-vs-paper P&L deviation fraction (M5.3), when known")
    p.add_argument("--as-of", default=None, help="ISO date (default: today UTC)")
    p.add_argument("--json", action="store_true", help="print raw JSON")
    args = p.parse_args(argv)

    inputs = (load_dynamodb(args.table, args.pk) if args.source == "dynamodb"
              else load_local(args.state))
    if args.tracking_error is not None:
        inputs.tracking_error = args.tracking_error
    as_of = (date.fromisoformat(args.as_of) if args.as_of
             else pd.Timestamp.now(tz="UTC").date())
    report = evaluate(inputs, as_of)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_report(report)


if __name__ == "__main__":
    main()
