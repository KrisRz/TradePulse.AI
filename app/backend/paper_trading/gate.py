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

GATE SPLIT (pre-registered 2026-07-28, 44 days before the earliest evaluation,
on pre-holdout data only — see docs/ANALIZA_KALIBRACJI_2026-07-28.md):

    Gate B (everything above) answers "did it make money". It cannot be
    answered in 8 weeks: the strategy closes 1.69 round trips a year, so
    P(activity rule satisfied within 56 days) is ~1%. Its thresholds are
    UNCHANGED; only the expected horizon moved to 12-18 months.

    Gate A (``--fidelity``) answers "is the machinery honest" — six criteria
    on execution fidelity, all decidable inside the 8-week window. Passing
    Gate A does NOT unlock real money; only Gate B opens M6.

Usage:
    # Gate B — profitability, against prod DynamoDB (needs AWS creds; read-only)
    python -m app.backend.paper_trading.gate --source dynamodb
    # Gate A — execution fidelity (queries Binance + CloudWatch, read-only)
    python -m app.backend.paper_trading.gate --source dynamodb --fidelity
    # either gate against a local paper_state file, no AWS
    python -m app.backend.paper_trading.gate --source local --fidelity --infra none
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
# GATE A — execution fidelity (pre-registered 2026-07-28, plan §3)
#
# Gate B above asks "did the strategy make money". It cannot answer that in an
# 8-week window: EMA20/100 closes 1.69 round trips a year, so P(>= 2 round
# trips AND >= 10 days in market within 56 days) is ~1%
# (docs/ANALIZA_KALIBRACJI_2026-07-28.md). Gate A asks the question the window
# CAN answer: is the machinery honest — is what the bot did live exactly what
# the backtest says it should have done?
#
# Six criteria, all computed from data we already store. Every one must pass;
# a criterion whose evidence is unavailable is SKIPPED and the verdict becomes
# INCOMPLETE, never PASS. Passing Gate A does NOT unlock real money — only
# Gate B opens M6.
# --------------------------------------------------------------------------- #
_TIMEFRAME_DELTA = {
    "1m": pd.Timedelta(minutes=1), "3m": pd.Timedelta(minutes=3),
    "5m": pd.Timedelta(minutes=5), "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30), "1h": pd.Timedelta(hours=1),
    "2h": pd.Timedelta(hours=2), "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
}

# Decision records persist money already rounded to cents (bot.py builds the
# record from ``round(equity, 2)``), so accounting parity is checked at that
# granularity — asking for 1e-6 on a rounded number would fail by construction.
EQUITY_TOLERANCE = 0.01
PRICE_REL_TOLERANCE = 1e-6

# How many violations of one kind to quote in the report before truncating.
_MAX_VIOLATIONS_SHOWN = 10


@dataclass
class FidelityInputs:
    """Everything Gate A needs. ``infra`` is None when AWS was not queried."""
    decisions: list[dict]          # raw decision records, one per processed bar
    state: dict                    # final persisted state (portfolio + last_bar)
    bars: pd.DataFrame             # exchange reference OHLCV, closed bars only
    strategy: Any                  # the Strategy the bot is supposed to run
    timeframe: str = "1d"
    lookback_bars: int = 400       # BotConfig.lookback_bars (feed request size)
    infra: Optional[dict] = None


def _truncate(items: list) -> list:
    if len(items) <= _MAX_VIOLATIONS_SHOWN:
        return items
    return items[:_MAX_VIOLATIONS_SHOWN] + [f"... and {len(items) - _MAX_VIOLATIONS_SHOWN} more"]


def _result(status: str, detail: str, **extra) -> dict:
    return {"status": status, "detail": detail, **extra}


def _sorted_decisions(decisions: list[dict]) -> list[dict]:
    return sorted(decisions, key=lambda d: str(d["bar"]))


def check_log_completeness(inputs: FidelityInputs) -> dict:
    """1. Exactly one record per closed bar in the window — no gaps, no dupes.

    The exchange bar index is the reference: a gap means the bot silently
    skipped a day (the gate metrics would then be computed on a hole), a
    duplicate means idempotency failed.
    """
    logged = [str(d["bar"]) for d in inputs.decisions]
    counts: dict[str, int] = {}
    for bar in logged:
        counts[bar] = counts.get(bar, 0) + 1
    duplicates = sorted(b for b, n in counts.items() if n > 1)

    idx = pd.DatetimeIndex(pd.to_datetime(sorted(set(logged)), utc=True, format="ISO8601"))
    if len(idx) == 0:
        return _result("FAIL", "decision log is empty")

    ref = inputs.bars.index
    expected = ref[(ref >= idx.min()) & (ref <= idx.max())]
    missing = expected.difference(idx)
    unknown = idx.difference(ref)     # a bar the exchange does not have at all

    problems = []
    if len(missing):
        problems.append(f"{len(missing)} missing bar(s)")
    if duplicates:
        problems.append(f"{len(duplicates)} duplicated bar(s)")
    if len(unknown):
        problems.append(f"{len(unknown)} bar(s) absent from exchange history")

    status = "PASS" if not problems else "FAIL"
    return _result(
        status,
        (f"{len(idx)} records covering {idx.min().date()} → {idx.max().date()}, "
         f"{len(expected)} bars expected" if status == "PASS"
         else "; ".join(problems)),
        records=len(logged),
        distinct_bars=len(idx),
        expected_bars=int(len(expected)),
        missing=_truncate([str(b) for b in missing]),
        duplicates=_truncate(duplicates),
        unknown_bars=_truncate([str(b) for b in unknown]),
    )


def check_signal_parity(inputs: FidelityInputs) -> dict:
    """2. Every live target equals the strategy's target on the same history.

    Reproduces the bot's exact input window: it requests ``lookback_bars``
    klines and drops the still-open one, so it decides on the last
    ``lookback_bars - 1`` closed bars (bot.py). An EMA is recursive, so using a
    different window length here would compare against a different number.
    """
    window = max(inputs.lookback_bars - 1, 1)
    ref = inputs.bars
    mismatches, unverifiable = [], []
    observed_targets: set[int] = set()

    for rec in _sorted_decisions(inputs.decisions):
        bar = pd.Timestamp(str(rec["bar"]))
        if bar not in ref.index:
            unverifiable.append(f"{rec['bar']}: not in exchange history")
            continue
        pos = ref.index.get_loc(bar)
        if pos + 1 < window:
            unverifiable.append(
                f"{rec['bar']}: only {pos + 1} bars of history available, "
                f"need {window} to reproduce the bot's window")
            continue
        history = ref.iloc[pos + 1 - window: pos + 1]
        expected = int(inputs.strategy.target_positions(history).iloc[-1])
        actual = int(rec["target"])
        observed_targets.add(actual)
        if expected != actual:
            mismatches.append(f"{rec['bar']}: live target {actual}, strategy says {expected}")

    checked = len(inputs.decisions) - len(unverifiable)
    if mismatches:
        return _result("FAIL", f"{len(mismatches)} of {checked} targets disagree with the strategy",
                       checked=checked, mismatches=_truncate(mismatches),
                       unverifiable=_truncate(unverifiable))
    if checked == 0:
        return _result("SKIPPED", "no bar had enough reference history to verify",
                       unverifiable=_truncate(unverifiable))

    # Discriminating power. If the window was entirely FLAT, every trend
    # strategy agrees with every other one and a passing parity check is
    # consistent with the bot running something else entirely. The criterion
    # is genuinely met, but reporting it as strong evidence would overstate
    # what a quiet window proves — say so instead of hiding it.
    distinct = len(observed_targets)
    detail = f"{checked} targets reproduce exactly (window {window} bars)"
    if unverifiable:
        detail += f"; {len(unverifiable)} unverifiable (insufficient reference history)"
    if distinct < 2:
        only = next(iter(observed_targets)) if observed_targets else None
        detail += (f" — but every target was {only}, so this cannot distinguish "
                   f"the live strategy from any other that stayed flat")
    return _result("PASS", detail, checked=checked, distinct_targets=distinct,
                   discriminating=distinct >= 2,
                   unverifiable=_truncate(unverifiable))


def check_price_parity(inputs: FidelityInputs) -> dict:
    """3. Every recorded price is the exchange's close for that bar."""
    ref = inputs.bars["close"]
    mismatches, unverifiable = [], []

    for rec in _sorted_decisions(inputs.decisions):
        bar = pd.Timestamp(str(rec["bar"]))
        if bar not in ref.index:
            unverifiable.append(f"{rec['bar']}: not in exchange history")
            continue
        live, actual = float(rec["price"]), float(ref.loc[bar])
        if actual == 0 or abs(live - actual) / abs(actual) > PRICE_REL_TOLERANCE:
            mismatches.append(f"{rec['bar']}: bot {live}, exchange {actual}")

    checked = len(inputs.decisions) - len(unverifiable)
    if mismatches:
        return _result("FAIL", f"{len(mismatches)} of {checked} prices differ from the exchange",
                       checked=checked, mismatches=_truncate(mismatches))
    if checked == 0:
        return _result("SKIPPED", "no bar could be cross-checked against the exchange",
                       unverifiable=_truncate(unverifiable))
    return _result("PASS", f"{checked} prices match the exchange close exactly",
                   checked=checked, unverifiable=_truncate(unverifiable))


def check_no_lookahead(inputs: FidelityInputs) -> dict:
    """4. Nothing was decided before its bar had closed.

    The live analogue of the backtest's next-bar-open rule: a record whose
    ``processed_at`` precedes the bar's close means the bot acted on a bar that
    was still forming, and every metric downstream of it is contaminated.
    """
    delta = _TIMEFRAME_DELTA.get(inputs.timeframe)
    if delta is None:
        return _result("SKIPPED", f"unknown timeframe {inputs.timeframe!r}")

    violations, unverifiable = [], []
    for rec in _sorted_decisions(inputs.decisions):
        stamp = rec.get("processed_at")
        if not stamp:
            unverifiable.append(f"{rec['bar']}: no processed_at")
            continue
        bar_close = pd.Timestamp(str(rec["bar"])) + delta
        processed = pd.Timestamp(str(stamp))
        if processed.tzinfo is None:
            processed = processed.tz_localize("UTC")
        if processed < bar_close:
            violations.append(
                f"{rec['bar']}: processed {processed.isoformat()} "
                f"before bar close {bar_close.isoformat()}")

    checked = len(inputs.decisions) - len(unverifiable)
    if violations:
        return _result("FAIL", f"{len(violations)} record(s) decided on an unclosed bar",
                       checked=checked, violations=_truncate(violations))
    if checked == 0:
        return _result("SKIPPED", "no record carried a processed_at timestamp",
                       unverifiable=_truncate(unverifiable))
    return _result("PASS", f"{checked} records processed strictly after their bar closed",
                   checked=checked, unverifiable=_truncate(unverifiable))


def check_accounting_parity(inputs: FidelityInputs) -> dict:
    """5. Replaying the decision log reproduces the equity the bot recorded.

    Feeds the recorded (target, price) pairs through a fresh ``PaperPortfolio``
    — the same class, hence the same shared cost model as the backtest. If the
    replay diverges, the live book drifted from the accounting the gates are
    computed on.
    """
    from .portfolio import PaperPortfolio

    book = inputs.state.get("portfolio", {}) or {}
    portfolio = PaperPortfolio(
        fee_rate=float(book.get("fee_rate", 0.001)),
        slippage=float(book.get("slippage", 0.0002)),
        initial_capital=float(book.get("initial_capital", 10_000.0)),
    )

    drifts = []
    records = _sorted_decisions(inputs.decisions)
    for rec in records:
        price = float(rec["price"])
        portfolio.reconcile(int(rec["target"]), price, str(rec["bar"]))
        replay_equity = round(portfolio.equity(price), 2)
        replay_realized = round(portfolio.realized, 2)
        if abs(replay_equity - float(rec["equity"])) > EQUITY_TOLERANCE:
            drifts.append(f"{rec['bar']}: equity recorded {float(rec['equity'])}, "
                          f"replay {replay_equity}")
        if "realized" in rec and abs(replay_realized - float(rec["realized"])) > EQUITY_TOLERANCE:
            drifts.append(f"{rec['bar']}: realized recorded {float(rec['realized'])}, "
                          f"replay {replay_realized}")

    live_trades = len(book.get("trades", []) or [])
    replay_trades = len(portfolio.trades)
    if live_trades != replay_trades:
        drifts.append(f"closed trades: state has {live_trades}, replay produced {replay_trades}")

    if drifts:
        return _result("FAIL", f"{len(drifts)} accounting divergence(s)",
                       checked=len(records), drifts=_truncate(drifts))
    if not records:
        return _result("SKIPPED", "no records to replay")
    return _result(
        "PASS",
        f"{len(records)} bars replay to the recorded book "
        f"(±${EQUITY_TOLERANCE:.2f}, {replay_trades} closed trades)",
        checked=len(records), replay_trades=replay_trades)


def check_infrastructure(inputs: FidelityInputs) -> dict:
    """6. The scheduler actually ran, nothing landed in the DLQ, no alarm fired.

    Criteria 1-5 prove the records we have are honest; this one proves there
    were no runs whose records never made it at all.
    """
    infra = inputs.infra
    if infra is None:
        return _result("SKIPPED", "AWS not queried (use --infra aws)")

    problems = []
    missing_days = infra.get("days_without_invocation") or []
    if missing_days:
        problems.append(f"{len(missing_days)} day(s) with no Lambda invocation")
    dlq = infra.get("dlq_messages_max")
    if dlq:
        problems.append(f"DLQ held up to {dlq} message(s)")
    fired = infra.get("alarms_fired") or []
    if fired:
        problems.append(f"{len(fired)} alarm transition(s) into ALARM")

    if problems:
        return _result("FAIL", "; ".join(problems),
                       days_without_invocation=_truncate([str(d) for d in missing_days]),
                       dlq_messages_max=dlq, alarms_fired=_truncate(fired))
    return _result(
        "PASS",
        f"{infra.get('days_checked', '?')} day(s) with >=1 invocation, "
        f"DLQ empty, no alarm fired",
        days_checked=infra.get("days_checked"))


FIDELITY_CHECKS = [
    ("log_completeness", check_log_completeness),
    ("signal_parity", check_signal_parity),
    ("price_parity", check_price_parity),
    ("no_lookahead", check_no_lookahead),
    ("accounting_parity", check_accounting_parity),
    ("infrastructure", check_infrastructure),
]


def evaluate_fidelity(inputs: FidelityInputs, as_of: date) -> dict:
    """Gate A verdict. Pure — no I/O, fully testable.

    PASS only when all six criteria pass. Any FAIL -> FAIL. Otherwise, if any
    criterion lacked evidence -> INCOMPLETE (never silently PASS on a gap).
    """
    criteria = {name: check(inputs) for name, check in FIDELITY_CHECKS}
    statuses = [c["status"] for c in criteria.values()]

    if "FAIL" in statuses:
        verdict = "FAIL"
        failed = [n for n, c in criteria.items() if c["status"] == "FAIL"]
        reason = f"execution is not faithful: {', '.join(failed)}"
    elif "SKIPPED" in statuses:
        verdict = "INCOMPLETE"
        skipped = [n for n, c in criteria.items() if c["status"] == "SKIPPED"]
        reason = f"evidence missing for: {', '.join(skipped)}"
    else:
        verdict = "PASS"
        reason = "live execution reproduces the backtest exactly"

    # A PASS earned in a fully FLAT window is weaker than it looks — surface
    # that at verdict level so a reader of the summary line cannot miss it.
    caveats = []
    parity = criteria.get("signal_parity", {})
    if parity.get("status") == "PASS" and parity.get("discriminating") is False:
        caveats.append(
            "signal parity has low discriminating power: the window never left "
            "target 0, so it cannot distinguish EMA20/100 from any other "
            "strategy that also stayed flat")

    return {
        "gate": "A — execution fidelity",
        "as_of": str(as_of),
        "window_start": str(WINDOW_START),
        "window_days": (as_of - WINDOW_START).days,
        "criteria": criteria,
        "verdict": verdict,
        "verdict_reason": reason + (f" (with caveats: {len(caveats)})" if caveats else ""),
        "caveats": caveats,
        "note": ("Gate A does not unlock real money — only Gate B "
                 "(profitability) opens M6."),
    }


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


def load_records_dynamodb(table_name: str, partition_key: str) -> tuple[list[dict], dict]:
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
    return decisions, state


def load_records_local(state_path: str) -> tuple[list[dict], dict]:
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
    return decisions, state


def load_dynamodb(table_name: str, partition_key: str) -> GateInputs:
    return _inputs_from_records(*load_records_dynamodb(table_name, partition_key))


def load_local(state_path: str) -> GateInputs:
    return _inputs_from_records(*load_records_local(state_path))


def load_infra_aws(function_name: str, dlq_queue_name: str, alarm_names: list[str],
                   start: date, end: date, region: Optional[str] = None) -> dict:
    """Criterion 6 evidence from CloudWatch — read-only.

    Invocations are summed per UTC day: the scheduler fires once daily, so any
    day with a zero sum is a run whose decision record could never exist.
    """
    import boto3

    cw = boto3.client("cloudwatch", region_name=region) if region else boto3.client("cloudwatch")
    start_dt = pd.Timestamp(start, tz="UTC").to_pydatetime()
    end_dt = (pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).to_pydatetime()

    invocations = cw.get_metric_statistics(
        Namespace="AWS/Lambda", MetricName="Invocations",
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        StartTime=start_dt, EndTime=end_dt, Period=86_400, Statistics=["Sum"])
    seen = {pd.Timestamp(p["Timestamp"]).tz_convert("UTC").date()
            for p in invocations["Datapoints"] if p["Sum"] >= 1}
    # The final day is only complete after the 00:10 UTC run, so exclude it.
    expected_days = pd.date_range(start, end, freq="D", inclusive="left")
    missing = [d.date() for d in expected_days if d.date() not in seen]

    dlq = cw.get_metric_statistics(
        Namespace="AWS/SQS", MetricName="ApproximateNumberOfMessagesVisible",
        Dimensions=[{"Name": "QueueName", "Value": dlq_queue_name}],
        StartTime=start_dt, EndTime=end_dt, Period=86_400, Statistics=["Maximum"])
    dlq_max = max((p["Maximum"] for p in dlq["Datapoints"]), default=0.0)

    fired = []
    for alarm in alarm_names:
        history = cw.describe_alarm_history(
            AlarmName=alarm, HistoryItemType="StateUpdate",
            StartDate=start_dt, EndDate=end_dt, MaxRecords=100)
        for item in history.get("AlarmHistoryItems", []):
            if '"newState":{"stateValue":"ALARM"' in item.get("HistoryData", "").replace(" ", ""):
                fired.append(f"{alarm} @ {item['Timestamp']}")

    return {
        "days_checked": len(expected_days),
        "days_without_invocation": missing,
        "dlq_messages_max": dlq_max,
        "alarms_fired": fired,
    }


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


def _print_fidelity_report(report: dict) -> None:
    print(f"=== M5 GATE A — EXECUTION FIDELITY — as of {report['as_of']} "
          f"(day {report['window_days']} of window) ===")
    mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIPPED": "SKIP"}
    for name, res in report["criteria"].items():
        print(f"  [{mark[res['status']]}] {name}: {res['detail']}")
        for key in ("missing", "duplicates", "unknown_bars", "mismatches",
                    "violations", "drifts", "days_without_invocation", "alarms_fired"):
            for item in res.get(key) or []:
                print(f"         - {item}")
    print(f"VERDICT: {report['verdict']} — {report['verdict_reason']}")
    for caveat in report.get("caveats", []):
        print(f"CAVEAT: {caveat}")
    print(f"NOTE: {report['note']}")


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

    g = p.add_argument_group("Gate A — execution fidelity")
    g.add_argument("--fidelity", action="store_true",
                   help="run Gate A (execution fidelity) instead of Gate B")
    g.add_argument("--infra", choices=["aws", "none"], default="aws",
                   help="criterion 6 evidence source (default: aws)")
    g.add_argument("--symbol", default="BTCUSDT")
    g.add_argument("--timeframe", default="1d")
    g.add_argument("--fast", type=int, default=20, help="live EMA fast period")
    g.add_argument("--slow", type=int, default=100, help="live EMA slow period")
    g.add_argument("--lookback-bars", type=int, default=400,
                   help="BotConfig.lookback_bars the live bot uses")
    g.add_argument("--function", default="tradepulse-paper-bot")
    g.add_argument("--dlq", default="tradepulse-paper-bot-scheduler-dlq")
    g.add_argument("--region", default=os.environ.get("AWS_REGION", "eu-west-2"))
    args = p.parse_args(argv)

    as_of = (date.fromisoformat(args.as_of) if args.as_of
             else pd.Timestamp.now(tz="UTC").date())

    if args.fidelity:
        report = run_fidelity(args, as_of)
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            _print_fidelity_report(report)
        return

    inputs = (load_dynamodb(args.table, args.pk) if args.source == "dynamodb"
              else load_local(args.state))
    if args.tracking_error is not None:
        inputs.tracking_error = args.tracking_error
    report = evaluate(inputs, as_of)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_report(report)


def run_fidelity(args, as_of: date) -> dict:
    """Wire the CLI arguments into Gate A: records + reference bars + infra."""
    from ..backtesting.strategies import EmaCrossover
    from .feed import fetch_klines

    decisions, state = (load_records_dynamodb(args.table, args.pk)
                        if args.source == "dynamodb"
                        else load_records_local(args.state))

    # Enough reference history to rebuild the bot's decision window for the
    # oldest record: its lookback plus the bars processed since. 1000 is the
    # Binance per-request maximum.
    needed = min(args.lookback_bars + len(decisions) + 5, 1000)
    bars = fetch_klines(args.symbol, args.timeframe, limit=needed)

    infra = None
    if args.infra == "aws":
        try:
            infra = load_infra_aws(
                function_name=args.function, dlq_queue_name=args.dlq,
                alarm_names=[f"{args.function}-errors",
                             f"{args.function}-no-invocation",
                             f"{args.function}-scheduler-dlq"],
                start=WINDOW_START, end=as_of, region=args.region)
        except Exception as exc:                      # noqa: BLE001 — reported, not fatal
            infra = None
            print(f"warning: AWS infrastructure check unavailable ({exc}) "
                  f"— criterion 6 will be SKIPPED")

    inputs = FidelityInputs(
        decisions=decisions, state=state, bars=bars,
        strategy=EmaCrossover(fast=args.fast, slow=args.slow, allow_short=False),
        timeframe=args.timeframe, lookback_bars=args.lookback_bars, infra=infra,
    )
    return evaluate_fidelity(inputs, as_of)


if __name__ == "__main__":
    main()
