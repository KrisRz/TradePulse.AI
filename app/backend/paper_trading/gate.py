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
as the formulas require; the annualized Sharpe (bars per year of the channel's
timeframe — 365 on 1d, matching ``backtesting.metrics``) is reported alongside.
The trial-SR variance of rule 4 is a variance of ANNUALIZED Sharpe ratios and is
converted to per-bar units before use (until 2026-09-16 it was applied per bar
unconverted, which put the DSR benchmark at ~21.7 annualized and printed
DSR 0.000 for every achievable record — audit 2026-09-04, MEDIUM-4).

TIGHTENING (pre-registered 2026-09-05, docs/GATE_B_PREREGISTRATION_2026-09-05.md,
binding from the 2026-10-08 evaluation; applied here to every verdict issued
after the earliest evaluation, since it can only withhold a PASS):

5. B5 ``psr_vs_zero >= 0.95`` (undefined PSR = not met).
6. B6 annualized Sharpe >= that of buy & hold WITH costs on the identical bars.
7. B7 ``window_days >= 365``.
   Old gates met but not all of B5-B7 -> ``PROVISIONAL_PASS``, which does NOT
   authorize M6.
8. With a position open on the evaluation date, profit factor and fee drag
   must pass both on closed trades alone and with the open position closed at
   the last price (audit MEDIUM-5): a PASS must not depend on the date chosen.
9. A quantity-backed book (the venue channel) books its BNB commission outside
   equity, so its fee drag is not interpretable and that gate is not met.

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
    # Gate C — cost fidelity of the 4h venue channel (durable fill/reject log)
    python -m app.backend.paper_trading.gate --source dynamodb --cost-fidelity
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
TRIAL_SR_VAR = 0.3             # variance of ANNUALIZED trial Sharpe ratios
PSR_CONFIDENCE = 0.95

# Tightening of 2026-09-05 (B5-B7). May be made stricter before data, never looser.
TIGHTENING_PREREGISTERED = date(2026, 9, 5)
TIGHTENING_BINDING_FROM = date(2026, 10, 8)
MIN_PSR_VS_ZERO = 0.95         # B5
MIN_WINDOW_DAYS = 365          # B7
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
                    trial_sr_var: float = TRIAL_SR_VAR / 365.0) -> float:
    """DSR = PSR evaluated against the expected-max-SR of the trials.

    ``sr_hat`` is per bar, so ``trial_sr_var`` must be too: the default converts
    the annualized assumption for daily bars.
    """
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
    # Close per processed bar, on the same index as ``equity``. Without it the
    # buy & hold comparison (B6) cannot be made and is reported as not met.
    prices: Optional[pd.Series] = None
    fee_rate: float = 0.001
    slippage: float = 0.0002
    timeframe: str = "1d"
    # True for a book driven by venue fills: its commission is booked outside
    # equity (``fees_external``), so its fee drag means nothing yet.
    quantity_backed: bool = False
    # The open position, closed hypothetically at the last price (MEDIUM-5).
    open_trade: Optional[dict] = None


def periods_per_year(timeframe: str) -> float:
    """Bars in a 365-day year for ``timeframe`` (crypto trades around the clock)."""
    delta = _TIMEFRAME_DELTA.get(timeframe)
    if delta is None:
        raise ValueError(f"unknown timeframe {timeframe!r}")
    return pd.Timedelta(days=365) / delta


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


def open_position_as_trade(portfolio: dict, price: float, time: str) -> Optional[dict]:
    """The open position as if it were closed at ``price`` now, costs included.

    A modelled book is closed by its own arithmetic on a copy, so the record is
    exactly what the book would write. A quantity-backed book has no venue here
    to fill against; its exit is priced from the held quantity with the same
    slippage and fee model, which is the honest analogue.
    """
    from ..backtesting.costs import exit_fill_price
    from .portfolio import PaperPortfolio

    if not portfolio or not portfolio.get("side"):
        return None
    if not portfolio.get("quantity_backed"):
        book = PaperPortfolio.from_dict(dict(portfolio, trades=[]))
        book.reconcile(0, float(price), str(time))
        trade = dict(book.trades[-1])
        trade["exit_reason"] = "open_at_evaluation"
        return trade

    side = int(portfolio["side"])
    exit_px = exit_fill_price(float(price), side, float(portfolio.get("slippage", 0.0002)))
    qty = abs(float(portfolio.get("qty", 0.0)))
    proceeds = qty * exit_px
    fee = proceeds * float(portfolio.get("fee_rate", 0.001))
    after = float(portfolio.get("cash", 0.0)) + side * proceeds - fee
    before = float(portfolio.get("equity_before_entry") or 0.0)
    if before <= 0:
        return None
    return {"entry_time": portfolio.get("entry_time"), "exit_time": str(time),
            "side": side, "entry_price": float(portfolio["entry_fill"]),
            "exit_price": exit_px, "net_return": after / before - 1.0,
            "exit_reason": "open_at_evaluation"}


def buy_and_hold_equity(prices: pd.Series, initial_capital: float,
                        fee_rate: float, slippage: float) -> pd.Series:
    """Buy & hold WITH costs on the given bars — the definition B6 binds to.

    One entry at the first bar, one exit at the evaluation (last) bar, both
    through the same fee and slippage helpers the strategy's book uses; in
    between, marked to market like the book. This is the costlier reading for
    buy & hold, i.e. the one more favourable to the bot, as the
    pre-registration requires.
    """
    from ..backtesting.costs import apply_fee, entry_fill_price, exit_fill_price

    p = prices.astype(float).sort_index()
    entry_equity = apply_fee(initial_capital, fee_rate)
    entry_fill = entry_fill_price(float(p.iloc[0]), 1, slippage)
    equity = entry_equity * (p / entry_fill)
    exit_value = apply_fee(
        entry_equity * exit_fill_price(float(p.iloc[-1]), 1, slippage) / entry_fill,
        fee_rate)
    equity.iloc[-1] = exit_value
    return equity


def _annualized_sharpe(equity: pd.Series, ppy: float) -> tuple[Optional[float], pd.Series]:
    rets = equity.pct_change().dropna()
    sd = float(rets.std(ddof=1)) if len(rets) >= 2 else 0.0
    if sd <= 0:
        return None, rets
    return float(rets.mean() / sd) * math.sqrt(ppy), rets


def _drawdown_profile(equity: pd.Series) -> dict:
    """Depth plus duration — a drawdown that lasts is a different risk."""
    if len(equity) == 0:
        return {"max_drawdown": 0.0, "longest_bars": 0, "current_bars": 0}
    underwater = equity < equity.cummax()
    longest = current = 0
    for flag in underwater:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return {"max_drawdown": float((equity / equity.cummax() - 1.0).min()),
            "longest_bars": int(longest), "current_bars": int(current)}


def evaluate(inputs: GateInputs, as_of: date) -> dict:
    """Full pre-registered evaluation. Pure — no I/O, fully testable."""
    eq = inputs.equity.dropna().sort_index()
    window_days = (as_of - WINDOW_START).days
    ppy = periods_per_year(inputs.timeframe)
    report: dict[str, Any] = {
        "as_of": str(as_of),
        "window_start": str(WINDOW_START),
        "window_days": window_days,
        "earliest_eval": str(EARLIEST_EVAL),
        "timeframe": inputs.timeframe,
        "bars": int(len(eq)),
    }

    # -- performance readout (always reported) --------------------------- #
    net_pnl = float(eq.iloc[-1] - inputs.initial_capital) if len(eq) else 0.0
    dd = _drawdown_profile(eq)
    max_dd = dd["max_drawdown"]
    sharpe_ann, rets = _annualized_sharpe(eq, ppy)
    sr_bar = sharpe_ann / math.sqrt(ppy) if sharpe_ann is not None else None

    tstats = _trade_stats(inputs.trades)
    notes = []
    if inputs.quantity_backed:
        tstats["fee_drag"] = None
        notes.append("fees are booked outside equity (fees_external) on this "
                     "quantity-backed book — fee drag is not interpretable and "
                     "net figures exclude the commission")
    days_in_market = tstats["days_in_market_closed"] + inputs.open_position_days
    report["performance"] = {
        "final_equity": float(eq.iloc[-1]) if len(eq) else inputs.initial_capital,
        "net_pnl": net_pnl,
        "max_drawdown": max_dd,
        "sharpe_annualized": sharpe_ann,
        "periods_per_year": ppy,
        "days_in_market": days_in_market,
        **tstats,
    }

    with_open = None
    if inputs.open_trade is not None:
        with_open = _trade_stats(list(inputs.trades) + [inputs.open_trade])
        if inputs.quantity_backed:
            with_open["fee_drag"] = None
        report["performance_incl_open"] = {
            "open_trade_net_return": inputs.open_trade["net_return"],
            "profit_factor": with_open["profit_factor"],
            "fee_drag": with_open["fee_drag"],
            "win_rate": with_open["win_rate"],
        }

    # -- statistical readout ---------------------------------------------- #
    psr0 = None
    if sr_bar is not None and len(rets) >= 3:
        skew = float(rets.skew())
        kurt = float(rets.kurt()) + 3.0            # pandas gives EXCESS kurtosis
        trial_var_bar = TRIAL_SR_VAR / ppy
        sr_star = expected_max_sharpe(N_TRIALS, trial_var_bar)
        psr0 = probabilistic_sharpe(sr_bar, 0.0, len(rets), skew, kurt)
        dsr = deflated_sharpe(sr_bar, len(rets), skew, kurt,
                              trial_sr_var=trial_var_bar)
        mintrl = min_track_record_length(sr_bar, 0.0, skew, kurt)
        # Standard error of the per-bar Sharpe under non-normal iid returns
        # (Mertens), the same variance term PSR uses. Serial correlation is
        # not corrected for, so this interval is if anything too narrow.
        var_term = 1.0 - skew * sr_bar + (kurt - 1.0) / 4.0 * sr_bar ** 2
        se_bar = math.sqrt(var_term / (len(rets) - 1)) if var_term > 0 else float("nan")
        half = 1.959963984540054 * se_bar * math.sqrt(ppy)
        report["statistics"] = {
            "sr_per_bar": sr_bar, "skew": skew, "kurtosis": kurt,
            "psr_vs_zero": psr0,
            "expected_max_sr_of_trials_per_bar": sr_star,
            "expected_max_sr_of_trials_annualized": sr_star * math.sqrt(ppy),
            "dsr": dsr,
            "min_trl_bars_vs_zero": mintrl,
            "min_trl_bars_remaining": max(0.0, mintrl - len(rets))
            if math.isfinite(mintrl) else None,
            "sharpe_annualized_ci95": [sharpe_ann - half, sharpe_ann + half],
            "n_trials_assumed": N_TRIALS,
            "trial_sr_var_annualized_assumed": TRIAL_SR_VAR,
        }
    else:
        report["statistics"] = {
            "note": "no return variance yet (flat window) — PSR/DSR undefined"}

    # -- benchmark and diagnostics (reported, never a threshold by itself) -- #
    bh_sharpe = None
    if inputs.prices is not None and len(inputs.prices.dropna()) >= 2:
        prices = inputs.prices.dropna().sort_index()
        bh = buy_and_hold_equity(prices, inputs.initial_capital,
                                 inputs.fee_rate, inputs.slippage)
        bh_sharpe, _ = _annualized_sharpe(bh, ppy)
        bh_dd = _drawdown_profile(bh)
        strat_return = float(eq.iloc[-1] / inputs.initial_capital - 1.0) if len(eq) else 0.0
        bh_return = float(bh.iloc[-1] / inputs.initial_capital - 1.0)
        report["benchmark"] = {
            "definition": "buy & hold with costs: entry at the first bar, exit at "
                          "the evaluation bar, strategy's own fee and slippage",
            "first_bar": str(prices.index[0]), "last_bar": str(prices.index[-1]),
            "buy_hold_return": bh_return,
            "strategy_return": strat_return,
            "excess_return": strat_return - bh_return,
            "buy_hold_sharpe_annualized": bh_sharpe,
            "buy_hold_max_drawdown": bh_dd["max_drawdown"],
            "buy_hold_longest_drawdown_bars": bh_dd["longest_bars"],
            "drawdown_avoided": max_dd - bh_dd["max_drawdown"],
        }
    report["diagnostics"] = {
        "longest_drawdown_bars": dd["longest_bars"],
        "current_drawdown_bars": dd["current_bars"],
        "bar_hours": _TIMEFRAME_DELTA[inputs.timeframe] / pd.Timedelta(hours=1),
        # The independent evidence is the trades, not the bars: returns inside
        # one trend are strongly serially correlated (Lo 2002).
        "effective_observations_trades": tstats["round_trips"]
        + (1 if inputs.open_trade is not None else 0),
        "position_open": inputs.open_trade is not None,
    }
    if notes:
        report["notes"] = notes

    tightened = {
        "B5 psr_vs_zero>=0.95": psr0 is not None and math.isfinite(psr0)
        and psr0 >= MIN_PSR_VS_ZERO,
        "B6 sharpe>=buy&hold": sharpe_ann is not None and bh_sharpe is not None
        and sharpe_ann >= bh_sharpe,
        "B7 window_days>=365": window_days >= MIN_WINDOW_DAYS,
    }
    report["tightened_gates"] = tightened
    report["tightening"] = {
        "preregistered": str(TIGHTENING_PREREGISTERED),
        "binding_from": str(TIGHTENING_BINDING_FROM),
        "document": "docs/GATE_B_PREREGISTRATION_2026-09-05.md",
    }

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

    def _pf_ok(stats):
        return stats["profit_factor"] is not None and stats["profit_factor"] >= MIN_PROFIT_FACTOR

    def _drag_ok(stats):
        return stats["fee_drag"] is not None and stats["fee_drag"] < MAX_FEE_DRAG

    gates = {
        "max_drawdown<=25%": max_dd >= -MAX_DRAWDOWN_LIMIT,
        "profit_factor>=1.3": _pf_ok(tstats),
        "net_pnl>0": net_pnl > 0.0,
        "fee_drag<20%": _drag_ok(tstats),
    }
    if with_open is not None:
        gates["profit_factor>=1.3 (incl. open)"] = _pf_ok(with_open)
        gates["fee_drag<20% (incl. open)"] = _drag_ok(with_open)
    if inputs.tracking_error is not None:
        gates["tracking_error<10%"] = abs(inputs.tracking_error) < MAX_TRACKING_ERROR
    else:
        report["skipped_gates"] = ["tracking_error<10% (M5.3 input not supplied)"]
    report["gates"] = gates

    failed = [k for k, v in gates.items() if not v]
    missing = [k for k, v in tightened.items() if not v]
    if failed:
        report["verdict"] = "FAIL"
        report["verdict_reason"] = f"failed: {', '.join(failed)}"
    elif missing:
        report["verdict"] = "PROVISIONAL_PASS"
        report["verdict_reason"] = (
            f"the original gates are met, the tightened ones are not "
            f"({', '.join(missing)}) — this does NOT authorize M6")
    else:
        report["verdict"] = "PASS"
        report["verdict_reason"] = "all hard gates met, including B5-B7"
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
    # The venue's own fills (durable log). Required to replay a quantity-backed
    # book: its equity follows the fills, not the slippage model.
    fills: Optional[list[dict]] = None
    window_start: Optional[date] = None   # defaults to the M5 window start


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
        # A risk overlay (F7) may have overridden the strategy; the bot then
        # records the strategy's own target separately, and that is what
        # parity is about. ``target`` is what the book did — criterion 5's job.
        actual = int(rec.get("strategy_target", rec["target"]))
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


class _RecordedFills:
    """An executor that answers with the venue's recorded fills, bar by bar.

    Replaying a quantity-backed book through the slippage model compares it with
    accounting it never used: the venue channel's equity follows real fills and
    books its BNB commission outside equity, so a modelled replay disagrees on
    every bar by exactly that commission (audit E2E 2026-09-04, E1). Feeding the
    recorded fills back through the same ``PaperPortfolio`` asks the right
    question — does the stored book equal its own fills?
    """

    def __init__(self, fills: list[dict]):
        self._queue: dict[tuple[str, int], list[dict]] = {}
        for rec in sorted(fills, key=lambda f: str(f.get("recorded_at", ""))):
            key = (str(rec["bar"]), int(rec["side"]))
            self._queue.setdefault(key, []).append(rec)
        self.missing: list[str] = []

    def execute(self, order):
        from .execution import Fill

        queue = self._queue.get((str(order.time), int(order.side)))
        if not queue:
            self.missing.append(f"{order.time}: {'BUY' if order.side > 0 else 'SELL'} "
                                f"traded in the book but has no fill record")
            raise LookupError(order.time)
        rec = queue.pop(0)
        return Fill(price=float(rec["actual_price"]), side=order.side, time=order.time,
                    qty=float(rec["qty"]), fee_paid=float(rec.get("fee_paid") or 0.0),
                    fee_asset=rec.get("fee_asset") or None,
                    order_id=str(rec.get("order_id") or "") or None, raw=rec,
                    base_asset=rec.get("base_asset") or None)

    def unused(self) -> list[str]:
        return [f"{bar}: {'BUY' if side > 0 else 'SELL'} fill {r.get('order_id')} "
                f"never reached the book" for (bar, side), recs in self._queue.items()
                for r in recs]


def check_accounting_parity(inputs: FidelityInputs) -> dict:
    """5. Replaying the decision log reproduces the equity the bot recorded.

    Feeds the recorded (target, price) pairs through a fresh ``PaperPortfolio``
    — the same class, hence the same shared cost model as the backtest. If the
    replay diverges, the live book drifted from the accounting the gates are
    computed on.

    A quantity-backed book (the venue channel) is replayed through its own
    recorded fills instead of the slippage model; a traded bar without a fill
    record, or a fill the book never took, is a divergence in its own right.
    """
    from .portfolio import PaperPortfolio

    book = inputs.state.get("portfolio", {}) or {}
    portfolio = PaperPortfolio(
        fee_rate=float(book.get("fee_rate", 0.001)),
        slippage=float(book.get("slippage", 0.0002)),
        initial_capital=float(book.get("initial_capital", 10_000.0)),
    )
    replayer = None
    mode = "modelled"
    if book.get("quantity_backed"):
        if inputs.fills is None:
            return _result("SKIPPED", "quantity-backed book, but no fill log was "
                                      "supplied to replay it against")
        replayer = _RecordedFills(inputs.fills)
        portfolio.set_executor(replayer)
        mode = "recorded fills"

    drifts = []
    records = _sorted_decisions(inputs.decisions)
    for rec in records:
        price = float(rec["price"])
        try:
            portfolio.reconcile(int(rec["target"]), price, str(rec["bar"]))
        except LookupError:
            break
        replay_equity = round(portfolio.equity(price), 2)
        replay_realized = round(portfolio.realized, 2)
        if abs(replay_equity - float(rec["equity"])) > EQUITY_TOLERANCE:
            drifts.append(f"{rec['bar']}: equity recorded {float(rec['equity'])}, "
                          f"replay {replay_equity}")
        if "realized" in rec and abs(replay_realized - float(rec["realized"])) > EQUITY_TOLERANCE:
            drifts.append(f"{rec['bar']}: realized recorded {float(rec['realized'])}, "
                          f"replay {replay_realized}")

    if replayer is not None:
        drifts.extend(replayer.missing)
        drifts.extend(replayer.unused())

    live_trades = len(book.get("trades", []) or [])
    replay_trades = len(portfolio.trades)
    if live_trades != replay_trades:
        drifts.append(f"closed trades: state has {live_trades}, replay produced {replay_trades}")

    if drifts:
        return _result("FAIL", f"{len(drifts)} accounting divergence(s) ({mode} replay)",
                       checked=len(records), mode=mode, drifts=_truncate(drifts))
    if not records:
        return _result("SKIPPED", "no records to replay")
    return _result(
        "PASS",
        f"{len(records)} bars replay to the recorded book "
        f"(±${EQUITY_TOLERANCE:.2f}, {replay_trades} closed trades, {mode})",
        checked=len(records), replay_trades=replay_trades, mode=mode)


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
        problems.append(f"{len(missing_days)} {infra.get('period_label', 'day')}(s) "
                        f"with no Lambda invocation")
    dlq = infra.get("dlq_messages_max")
    if dlq:
        problems.append(f"DLQ held up to {dlq} message(s)")
    fired = infra.get("alarms_fired") or []
    if fired:
        problems.append(f"{len(fired)} alarm transition(s) into ALARM")
    errors = infra.get("function_errors")
    if errors:
        problems.append(f"{errors:.0f} function error(s)")
    halted = {k: v for k, v in (infra.get("halts") or {}).items() if v}
    if halted:
        problems.append(f"kill switch halted {sum(halted.values()):.0f} time(s)")

    if problems:
        return _result("FAIL", "; ".join(problems),
                       days_without_invocation=_truncate([str(d) for d in missing_days]),
                       dlq_messages_max=dlq, alarms_fired=_truncate(fired))
    detail = (f"{infra.get('days_checked', '?')} {infra.get('period_label', 'day')}(s) "
              f"with >=1 invocation, DLQ empty, no alarm fired")
    if "function_errors" in infra:
        detail += ", 0 function errors"
    if infra.get("halts"):
        detail += ", 0 kill-switch halts"
    if infra.get("alarm_history_complete") is False:
        detail += (f" (alarm history only from {infra['alarm_history_from']} — "
                   f"CloudWatch keeps {ALARM_HISTORY_DAYS} days; errors and halts "
                   f"are read from metrics over the whole window)")
    return _result("PASS", detail, days_checked=infra.get("days_checked"),
                   throttles=infra.get("throttles"),
                   alarm_history_from=infra.get("alarm_history_from"))


FIDELITY_CHECKS = [
    ("log_completeness", check_log_completeness),
    ("signal_parity", check_signal_parity),
    ("price_parity", check_price_parity),
    ("no_lookahead", check_no_lookahead),
    ("accounting_parity", check_accounting_parity),
    ("infrastructure", check_infrastructure),
]


# --------------------------------------------------------------------------- #
# GATE C — cost fidelity (pre-registered 2026-08-06,
# docs/VENUE_4H_CHANNEL_2026-08-06.md §2)
#
# The 4h venue channel exists to measure what execution actually costs when a
# strategy (not a heartbeat) drives real orders: Gate A proves the machinery is
# honest, Gate B whether the strategy earns, Gate C whether the COST MODEL the
# backtest assumes matches the venue. A FAIL on C1/C2 means the backtest is too
# optimistic and Gate B's thresholds must be recomputed at the higher cost
# before real money is allowed.
#
# Thresholds are pre-registered; do not edit after seeing results. The gate is
# decidable at >= GATE_C_MIN_FILLS real fills (~10 months at ~12 round trips a
# year); before that the evaluator reports but never issues PASS/FAIL.
# --------------------------------------------------------------------------- #
GATE_C_MIN_FILLS = 20
GATE_C_MAX_MEDIAN_EXEC_SLIPPAGE = 0.0002   # C1 — the book's model assumption
GATE_C_MAX_P90_EXEC_SLIPPAGE = 0.0005      # C2
GATE_C_MAX_REJECTION_RATE = 0.02           # C3 — share of all submissions


@dataclass
class CostFidelityInputs:
    """Everything Gate C needs, straight from the durable fill/reject log."""
    fills: list[dict]              # fill# records (Reconciliation + context)
    rejections: list[dict]         # reject# records
    decisions: list[dict]          # decision log, for fill-log completeness


def _exec_slippages(fills: list[dict]) -> tuple[list[float], list[str]]:
    """Signed execution slippage per fill; fills without a mark are unusable."""
    values, unverifiable = [], []
    for f in fills:
        s = f.get("execution_slippage")
        if s is None:
            unverifiable.append(f"{f.get('bar')}/{f.get('order_id')}: "
                                f"no mark_at_order — slippage not separable from drift")
        else:
            values.append(float(s))
    return values, unverifiable


def check_fill_log_completeness(inputs: CostFidelityInputs) -> dict:
    """C0. Every trade in the decision log left a fill record.

    Not one of the six pre-registered criteria, but the precondition for all of
    them: a fill whose evidence was lost would silently shrink the sample the
    medians are computed on. Extra fills without a decision record are fine —
    a kill-switch flatten trades outside the decision path by design.
    """
    if not inputs.decisions:
        return _result("SKIPPED", "no decision log supplied")
    fill_bars = {str(f.get("bar")) for f in inputs.fills}
    missing = [str(d["bar"]) for d in _sorted_decisions(inputs.decisions)
               if d.get("action") and str(d["bar"]) not in fill_bars]
    traded = sum(1 for d in inputs.decisions if d.get("action"))
    if missing:
        return _result("FAIL",
                       f"{len(missing)} traded bar(s) have no fill record",
                       traded_bars=traded, missing=_truncate(missing))
    return _result("PASS",
                   f"all {traded} traded bar(s) have fill evidence "
                   f"({len(inputs.fills)} fill records total)",
                   traded_bars=traded, fills=len(inputs.fills))


def check_median_exec_slippage(inputs: CostFidelityInputs) -> dict:
    """C1. Median execution slippage within the model's assumption."""
    values, unverifiable = _exec_slippages(inputs.fills)
    if not values:
        return _result("SKIPPED", "no fill carries a separable execution slippage",
                       unverifiable=_truncate(unverifiable))
    med = float(pd.Series(values).median())
    ok = med <= GATE_C_MAX_MEDIAN_EXEC_SLIPPAGE
    return _result(
        "PASS" if ok else "FAIL",
        f"median execution slippage {med * 100:.4f}% over {len(values)} fill(s) "
        f"(threshold {GATE_C_MAX_MEDIAN_EXEC_SLIPPAGE * 100:.2f}%)",
        median=med, n=len(values), unverifiable=_truncate(unverifiable))


def check_p90_exec_slippage(inputs: CostFidelityInputs) -> dict:
    """C2. Tail (p90) execution slippage bounded."""
    values, unverifiable = _exec_slippages(inputs.fills)
    if not values:
        return _result("SKIPPED", "no fill carries a separable execution slippage",
                       unverifiable=_truncate(unverifiable))
    p90 = float(pd.Series(values).quantile(0.9))
    ok = p90 <= GATE_C_MAX_P90_EXEC_SLIPPAGE
    return _result(
        "PASS" if ok else "FAIL",
        f"p90 execution slippage {p90 * 100:.4f}% over {len(values)} fill(s) "
        f"(threshold {GATE_C_MAX_P90_EXEC_SLIPPAGE * 100:.2f}%)",
        p90=p90, n=len(values), unverifiable=_truncate(unverifiable))


def check_rejection_rate(inputs: CostFidelityInputs) -> dict:
    """C3. Venue rejections as a share of all order submissions."""
    attempts = len(inputs.fills) + len(inputs.rejections)
    if attempts == 0:
        return _result("SKIPPED", "no order was ever submitted")
    rate = len(inputs.rejections) / attempts
    ok = rate <= GATE_C_MAX_REJECTION_RATE
    detail = (f"{len(inputs.rejections)} rejection(s) in {attempts} submission(s) "
              f"= {rate * 100:.2f}% (threshold {GATE_C_MAX_REJECTION_RATE * 100:.0f}%)")
    reasons = _truncate([f"{r.get('time')}: [{r.get('code')}] {r.get('message')}"
                         for r in inputs.rejections])
    return _result("PASS" if ok else "FAIL", detail,
                   rate=rate, attempts=attempts, rejections=reasons)


def check_partial_fills(inputs: CostFidelityInputs) -> dict:
    """C4. No partial fill may leave a position unclosed."""
    partials, unverifiable = [], []
    for f in inputs.fills:
        label = f"{f.get('bar')}/{f.get('order_id')}"
        status = str(f.get("status", ""))
        if status and status != "FILLED":
            partials.append(f"{label}: venue status {status}")
            continue
        requested, executed = f.get("requested_qty"), f.get("qty")
        step = f.get("step_size")
        if requested is None or step is None:
            unverifiable.append(f"{label}: requested quantity not recorded")
        elif float(requested) - float(executed or 0.0) > float(step):
            partials.append(f"{label}: requested {requested}, executed {executed}")
    if partials:
        return _result("FAIL", f"{len(partials)} fill(s) executed short of their order",
                       partials=_truncate(partials), unverifiable=_truncate(unverifiable))
    if not inputs.fills:
        return _result("SKIPPED", "no fills to check")
    detail = f"{len(inputs.fills)} fill(s) fully executed"
    if unverifiable:
        detail += f"; {len(unverifiable)} without a recorded requested quantity"
    return _result("PASS", detail, checked=len(inputs.fills),
                   unverifiable=_truncate(unverifiable))


def check_book_venue_divergence(inputs: CostFidelityInputs) -> dict:
    """C5. The book and the venue balance move together, within one stepSize.

    Two independent tests per fill: (a) the venue's free-balance change across
    the invocation equals the executed quantity net of any base-asset
    commission; (b) the impossible state — the book holding more than the
    account owns — never occurs (the exit leg could not fill).
    """
    divergences, unverifiable = [], []
    checked = 0
    for f in inputs.fills:
        label = f"{f.get('bar')}/{f.get('order_id')}"
        step = f.get("step_size")
        before, after = f.get("venue_free_base_before"), f.get("venue_free_base_after")
        if step is None or before is None or after is None:
            unverifiable.append(f"{label}: balance snapshot not recorded")
            continue
        if not f.get("venue_delta_attributable", True):
            unverifiable.append(f"{label}: multiple fills in one run — "
                                f"balance delta not attributable")
            continue
        step = float(step)
        side, qty = int(f.get("side", 0)), float(f.get("qty", 0.0))
        base_fee = (float(f.get("fee_paid", 0.0))
                    if str(f.get("fee_asset", "")).upper() == str(f.get("base_asset", "")).upper()
                    else 0.0)
        expected_delta = side * qty - (base_fee if side == 1 else 0.0)
        actual_delta = float(after) - float(before)
        checked += 1
        if abs(actual_delta - expected_delta) > step:
            divergences.append(
                f"{label}: venue balance moved {actual_delta:+.8f}, "
                f"fill implies {expected_delta:+.8f}")
        book_after = f.get("book_qty_after")
        if book_after is not None and float(book_after) > float(after) + step:
            divergences.append(
                f"{label}: book holds {book_after} but venue only has {after} free")
    if divergences:
        return _result("FAIL", f"{len(divergences)} book<->venue divergence(s) > 1 stepSize",
                       divergences=_truncate(divergences),
                       unverifiable=_truncate(unverifiable))
    if checked == 0:
        return _result("SKIPPED", "no fill carried a verifiable balance snapshot",
                       unverifiable=_truncate(unverifiable))
    detail = f"{checked} fill(s) reconcile with the venue balance within 1 stepSize"
    if unverifiable:
        detail += f"; {len(unverifiable)} unverifiable"
    return _result("PASS", detail, checked=checked,
                   unverifiable=_truncate(unverifiable))


def check_decision_drift(inputs: CostFidelityInputs) -> dict:
    """C6. Median decision->order drift — REPORTED, no threshold (pre-registered).

    Drift is market movement during the scheduler's delay, not execution
    quality, and the backtest does not model it at all. It is surfaced so a
    systematically adverse value becomes its own discovery; it never gates.
    """
    values = [float(f["drift"]) for f in inputs.fills if f.get("drift") is not None]
    if not values:
        return _result("SKIPPED", "no fill carries a drift measurement")
    med = float(pd.Series(values).median())
    return _result(
        "PASS",
        f"median decision->order drift {med * 100:.4f}% over {len(values)} fill(s) "
        f"— reported only, no threshold (pre-registered)",
        median=med, n=len(values), gating=False)


COST_FIDELITY_CHECKS = [
    ("fill_log_completeness", check_fill_log_completeness),
    ("c1_median_exec_slippage", check_median_exec_slippage),
    ("c2_p90_exec_slippage", check_p90_exec_slippage),
    ("c3_rejection_rate", check_rejection_rate),
    ("c4_partial_fills", check_partial_fills),
    ("c5_book_venue_divergence", check_book_venue_divergence),
    ("c6_decision_drift", check_decision_drift),
]


def evaluate_cost_fidelity(inputs: CostFidelityInputs, as_of: date) -> dict:
    """Gate C verdict. Pure — no I/O, fully testable.

    Below GATE_C_MIN_FILLS the verdict is COLLECTING — the gate is not
    decidable and no PASS/FAIL is issued (pre-registered), though criteria
    currently failing are named so a broken pipe is visible at fill 3, not
    fill 20. At or above the minimum: any FAIL -> FAIL, any missing evidence
    -> INCOMPLETE, otherwise PASS.
    """
    criteria = {name: check(inputs) for name, check in COST_FIDELITY_CHECKS}
    n_fills = len(inputs.fills)
    failed = [n for n, c in criteria.items() if c["status"] == "FAIL"]
    skipped = [n for n, c in criteria.items() if c["status"] == "SKIPPED"]

    if n_fills < GATE_C_MIN_FILLS:
        verdict = "COLLECTING"
        reason = (f"{n_fills}/{GATE_C_MIN_FILLS} fills — gate not decidable yet"
                  + (f"; criteria currently failing: {', '.join(failed)}" if failed else ""))
    elif failed:
        verdict = "FAIL"
        reason = f"cost model does not match the venue: {', '.join(failed)}"
    elif skipped:
        verdict = "INCOMPLETE"
        reason = f"evidence missing for: {', '.join(skipped)}"
    else:
        verdict = "PASS"
        reason = "venue execution costs match the model the backtest assumes"

    return {
        "gate": "C — cost fidelity (4h venue channel)",
        "as_of": str(as_of),
        "fills": n_fills,
        "rejections": len(inputs.rejections),
        "min_fills": GATE_C_MIN_FILLS,
        "criteria": criteria,
        "verdict": verdict,
        "verdict_reason": reason,
        "note": ("A FAIL on C1/C2 means the backtest's cost model is too "
                 "optimistic — Gate B thresholds must be recomputed at the "
                 "measured cost before real money."),
    }


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

    start = inputs.window_start or WINDOW_START
    return {
        "gate": "A — execution fidelity",
        "as_of": str(as_of),
        "timeframe": inputs.timeframe,
        "window_start": str(start),
        "window_days": (as_of - start).days,
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
    prices = (pd.Series(df["price"].astype(float).values, index=idx).sort_index()
              if "price" in df else None)
    portfolio = state.get("portfolio", {})
    trades = portfolio.get("trades", [])
    open_days = 0
    open_trade = None
    if portfolio.get("side", 0) != 0 and portfolio.get("entry_time"):
        open_days = max(
            (equity.index[-1] - pd.Timestamp(portfolio["entry_time"])).days, 0)
        if prices is not None:
            open_trade = open_position_as_trade(portfolio, float(prices.iloc[-1]),
                                                str(prices.index[-1]))
    timeframe = str(state.get("timeframe")
                    or (df["timeframe"].iloc[-1] if "timeframe" in df else "1d"))
    return GateInputs(
        equity=equity, trades=trades,
        initial_capital=float(portfolio.get("initial_capital", 10_000.0)),
        open_position_days=open_days,
        prices=prices,
        fee_rate=float(portfolio.get("fee_rate", 0.001)),
        slippage=float(portfolio.get("slippage", 0.0002)),
        timeframe=timeframe,
        quantity_backed=bool(portfolio.get("quantity_backed")),
        open_trade=open_trade,
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


def load_cost_records_dynamodb(table_name: str,
                               partition_key: str) -> tuple[list[dict], list[dict]]:
    """Read-only pull of the durable fill/reject log from DynamoDB."""
    import boto3
    from boto3.dynamodb.conditions import Key

    from .state_store import DynamoDBStateStore

    table = boto3.resource("dynamodb").Table(table_name)

    def _query(prefix: str) -> list[dict]:
        items: list[dict] = []
        kwargs: dict[str, Any] = {"KeyConditionExpression":
                                  Key("pk").eq(partition_key)
                                  & Key("sk").begins_with(prefix)}
        while True:
            resp = table.query(**kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        cleaned = []
        for item in items:
            rec = DynamoDBStateStore._from_ddb(item)
            rec.pop("pk", None), rec.pop("sk", None)
            cleaned.append(rec)
        return cleaned

    return _query("fill#"), _query("reject#")


def load_cost_records_local(state_path: str) -> tuple[list[dict], list[dict]]:
    from .state_store import LocalJsonStateStore

    store = LocalJsonStateStore(state_path)

    def _read(path) -> list[dict]:
        records = []
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    return _read(store.fills_path), _read(store.rejections_path)


def load_dynamodb(table_name: str, partition_key: str) -> GateInputs:
    return _inputs_from_records(*load_records_dynamodb(table_name, partition_key))


def load_local(state_path: str) -> GateInputs:
    return _inputs_from_records(*load_records_local(state_path))


def _utc(moment) -> pd.Timestamp:
    ts = pd.Timestamp(moment)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


#: CloudWatch keeps alarm history for 30 days ("CloudWatch preserves alarm history
#: for 30 days", CloudWatch User Guide, Using alarms). Measured 2026-09-16: the
#: 2026-08-07 transitions the E2E audit read on 09-04 are no longer returned.
ALARM_HISTORY_DAYS = 30


def _metric_sum(cw, namespace: str, metric: str, dimensions: list[dict],
                start: pd.Timestamp, end: pd.Timestamp) -> float:
    """Sum of a metric over [start, end), daily buckets, chunked under the cap."""
    total = 0.0
    cursor = start
    chunk = pd.Timedelta(days=1_440)
    while cursor < end:
        chunk_end = min(cursor + chunk, end)
        resp = cw.get_metric_statistics(
            Namespace=namespace, MetricName=metric, Dimensions=dimensions,
            StartTime=cursor.to_pydatetime(), EndTime=chunk_end.to_pydatetime(),
            Period=86_400, Statistics=["Sum"])
        total += sum(p["Sum"] for p in resp["Datapoints"])
        cursor = chunk_end
    return total


def load_infra_aws(function_name: str, dlq_queue_name: str, alarm_names: list[str],
                   start, end, region: Optional[str] = None,
                   period: pd.Timedelta = pd.Timedelta(days=1),
                   extra_metrics: tuple = (),
                   now: Optional[pd.Timestamp] = None) -> dict:
    """Criterion 6 evidence from CloudWatch — read-only.

    Invocations are summed per scheduling period (a UTC day for the daily bot,
    four hours for the venue channel): the scheduler fires once per period, so
    a period with a zero sum is a run whose decision record could never exist.
    Sub-daily periods are built from hourly datapoints, which CloudWatch keeps
    for 455 days and which do not depend on how it aligns longer buckets.
    """
    import boto3

    cw = boto3.client("cloudwatch", region_name=region) if region else boto3.client("cloudwatch")
    start_ts = _utc(start)
    end_ts = _utc(end)
    start_dt = start_ts.to_pydatetime()
    end_dt = (end_ts + pd.Timedelta(days=1)).to_pydatetime()
    daily = period >= pd.Timedelta(days=1)
    query_period = 86_400 if daily else 3_600
    chunk = pd.Timedelta(seconds=query_period * 1_440)   # CloudWatch's datapoint cap

    stamps = []
    cursor = start_ts
    while cursor < _utc(end_dt):
        chunk_end = min(cursor + chunk, _utc(end_dt))
        invocations = cw.get_metric_statistics(
            Namespace="AWS/Lambda", MetricName="Invocations",
            Dimensions=[{"Name": "FunctionName", "Value": function_name}],
            StartTime=cursor.to_pydatetime(), EndTime=chunk_end.to_pydatetime(),
            Period=query_period, Statistics=["Sum"])
        stamps.extend(_utc(p["Timestamp"]) for p in invocations["Datapoints"]
                      if p["Sum"] >= 1)
        cursor = chunk_end
    seen = {stamp.floor(period) for stamp in stamps}
    # The final period is only complete after its run, so the evaluation day
    # itself is excluded.
    expected = pd.date_range(start_ts.floor(period), end_ts, freq=period, inclusive="left")
    missing = [(p.date() if daily else p) for p in expected if p not in seen]

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

    # Alarm history only reaches back ALARM_HISTORY_DAYS. What the alarms watch
    # is kept far longer as metrics, so the whole window is judged on those, and
    # the alarm history is a second opinion over the part it still covers.
    window_end = _utc(end_dt)
    fn = [{"Name": "FunctionName", "Value": function_name}]
    function_errors = _metric_sum(cw, "AWS/Lambda", "Errors", fn, start_ts, window_end)
    throttles = _metric_sum(cw, "AWS/Lambda", "Throttles", fn, start_ts, window_end)
    halts = {f"{ns}/{name}": _metric_sum(cw, ns, name, [], start_ts, window_end)
             for ns, name in extra_metrics}
    now_ts = _utc(now) if now is not None else pd.Timestamp.now(tz="UTC")
    history_from = max(start_ts, now_ts - pd.Timedelta(days=ALARM_HISTORY_DAYS))

    return {
        "days_checked": len(expected),
        "period_label": "day" if daily else f"{int(period / pd.Timedelta(hours=1))}h period",
        "function_errors": function_errors,
        "throttles": throttles,
        "halts": halts,
        "alarm_history_from": str(history_from),
        "alarm_history_complete": history_from <= start_ts,
        "days_without_invocation": missing,
        "dlq_messages_max": dlq_max,
        "alarms_fired": fired,
    }


def _fmt(value, spec: str) -> str:
    return "n/a" if value is None else format(value, spec)


def _print_report(report: dict) -> None:
    print(f"=== M5 GATE REPORT — as of {report['as_of']} "
          f"(day {report['window_days']} of window, {report['timeframe']} bars) ===")
    perf = report["performance"]
    print(f"bars: {report['bars']}  equity: ${perf['final_equity']:,.2f}  "
          f"net P&L: ${perf['net_pnl']:,.2f}  maxDD: {perf['max_drawdown']*100:.2f}%")
    sr = perf["sharpe_annualized"]
    print(f"sharpe(ann): {sr:.2f}" if sr is not None else "sharpe(ann): n/a (no variance)")
    print(f"round trips: {perf['round_trips']}  days in market: {perf['days_in_market']}  "
          f"PF: {_fmt(perf['profit_factor'], '.3f')}  fee drag: {_fmt(perf['fee_drag'], '.4f')}")
    incl = report.get("performance_incl_open")
    if incl:
        print(f"incl. open position (closed at last price, net "
              f"{incl['open_trade_net_return']*100:+.2f}%): PF {_fmt(incl['profit_factor'], '.3f')}"
              f"  fee drag {_fmt(incl['fee_drag'], '.4f')}")
    stats = report["statistics"]
    if "dsr" in stats:
        rem = stats["min_trl_bars_remaining"]
        lo, hi = stats["sharpe_annualized_ci95"]
        print(f"PSR(>0): {stats['psr_vs_zero']:.3f}  DSR(N={stats['n_trials_assumed']}, "
              f"bar to clear {stats['expected_max_sr_of_trials_annualized']:.2f} ann.): "
              f"{stats['dsr']:.3f}  MinTRL: {stats['min_trl_bars_vs_zero']:.0f} bars"
              + (f" ({rem:.0f} more needed)" if rem is not None else ""))
        print(f"sharpe(ann) 95% CI: [{lo:.2f}, {hi:.2f}]")
    else:
        print(f"statistics: {stats['note']}")
    bench = report.get("benchmark")
    if bench:
        print(f"buy&hold (with costs): return {bench['buy_hold_return']*100:+.2f}% vs "
              f"strategy {bench['strategy_return']*100:+.2f}%  "
              f"sharpe {_fmt(bench['buy_hold_sharpe_annualized'], '.2f')}  "
              f"maxDD {bench['buy_hold_max_drawdown']*100:.2f}%")
    diag = report["diagnostics"]
    print(f"longest drawdown: {diag['longest_drawdown_bars']} bars "
          f"(current {diag['current_drawdown_bars']})  "
          f"effective observations: {diag['effective_observations_trades']} trade(s)")
    for note in report.get("notes", []):
        print(f"note: {note}")
    for g in report.get("skipped_gates", []):
        print(f"skipped: {g}")
    if "gates" in report:
        for name, ok in report["gates"].items():
            print(f"  gate {name}: {'PASS' if ok else 'FAIL'}")
    for name, ok in report["tightened_gates"].items():
        print(f"  tightened {name}: {'met' if ok else 'NOT met'}")
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


def _print_cost_fidelity_report(report: dict) -> None:
    print(f"=== GATE C — COST FIDELITY (4h venue channel) — as of {report['as_of']} ===")
    print(f"fills: {report['fills']}/{report['min_fills']} needed  "
          f"rejections: {report['rejections']}")
    mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIPPED": "SKIP"}
    for name, res in report["criteria"].items():
        print(f"  [{mark[res['status']]}] {name}: {res['detail']}")
        for key in ("missing", "partials", "divergences", "rejections", "unverifiable"):
            for item in res.get(key) or []:
                print(f"         - {item}")
    print(f"VERDICT: {report['verdict']} — {report['verdict_reason']}")
    print(f"NOTE: {report['note']}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Evaluate the M5 paper window gates.")
    p.add_argument("--source", choices=["dynamodb", "local"], default="dynamodb")
    p.add_argument("--table", default=os.environ.get("PAPER_STATE_TABLE",
                                                     "tradepulse_paper_bot"))
    p.add_argument("--pk", default=None,
                   help="partition key (default BTCUSDT_1d; BTCUSDT_4h "
                        "with --cost-fidelity)")
    p.add_argument("--state", default=None,
                   help="local state path (default paper_state/<pk>.json)")
    p.add_argument("--tracking-error", type=float, default=None,
                   help="live-vs-paper P&L deviation fraction (M5.3), when known")
    p.add_argument("--as-of", default=None, help="ISO date (default: today UTC)")
    p.add_argument("--json", action="store_true", help="print raw JSON")

    g = p.add_argument_group("Gate A — execution fidelity")
    g.add_argument("--fidelity", action="store_true",
                   help="run Gate A (execution fidelity) instead of Gate B; "
                        "--pk BTCUSDT_4h checks the venue channel")
    g.add_argument("--infra", choices=["aws", "none"], default="aws",
                   help="criterion 6 evidence source (default: aws)")
    g.add_argument("--symbol", default="BTCUSDT")
    g.add_argument("--timeframe", default=None,
                   help="default: the channel's (from --pk)")
    g.add_argument("--fast", type=int, default=20, help="live EMA fast period")
    g.add_argument("--slow", type=int, default=100, help="live EMA slow period")
    g.add_argument("--lookback-bars", type=int, default=400,
                   help="BotConfig.lookback_bars the live bot uses")
    g.add_argument("--function", default=None, help="default: the channel's Lambda")
    g.add_argument("--dlq", default=None, help="default: the channel's scheduler DLQ")
    g.add_argument("--since", default=None,
                   help="ISO date/time from which criterion 6 (infrastructure) is "
                        "checked (default: the M5 window for 1d, the channel's "
                        "first run otherwise)")
    g.add_argument("--region", default=os.environ.get("AWS_REGION", "eu-west-2"))

    c = p.add_argument_group("Gate C — cost fidelity (4h venue channel)")
    c.add_argument("--cost-fidelity", action="store_true",
                   help="run Gate C over the durable fill/reject log")
    args = p.parse_args(argv)

    if args.pk is None:
        args.pk = "BTCUSDT_4h" if args.cost_fidelity else "BTCUSDT_1d"
    channel = CHANNELS.get(args.pk, {})
    args.timeframe = args.timeframe or channel.get("timeframe") or "1d"
    args.function = args.function or channel.get("function") or "tradepulse-paper-bot"
    args.dlq = args.dlq or channel.get("dlq") or "tradepulse-paper-bot-scheduler-dlq"
    args.alarms = channel.get("alarms") or [f"{args.function}-errors",
                                            f"{args.function}-no-invocation",
                                            f"{args.function}-scheduler-dlq"]
    if args.state is None:
        args.state = f"paper_state/{args.pk}.json"

    as_of = (date.fromisoformat(args.as_of) if args.as_of
             else pd.Timestamp.now(tz="UTC").date())

    if args.cost_fidelity:
        fills, rejections = (load_cost_records_dynamodb(args.table, args.pk)
                             if args.source == "dynamodb"
                             else load_cost_records_local(args.state))
        try:
            decisions, _ = (load_records_dynamodb(args.table, args.pk)
                            if args.source == "dynamodb"
                            else load_records_local(args.state))
        except RuntimeError:
            decisions = []   # no state item yet — completeness check is SKIPPED
        report = evaluate_cost_fidelity(
            CostFidelityInputs(fills=fills, rejections=rejections,
                               decisions=decisions), as_of)
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            _print_cost_fidelity_report(report)
        return

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


#: Where each channel's evidence lives. Keyed by the state partition key.
CHANNELS = {
    "BTCUSDT_1d": {
        "timeframe": "1d",
        "function": "tradepulse-paper-bot",
        "dlq": "tradepulse-paper-bot-scheduler-dlq",
        "alarms": ["tradepulse-paper-bot-errors",
                   "tradepulse-paper-bot-no-invocation",
                   "tradepulse-paper-bot-scheduler-dlq"],
        "window_start": WINDOW_START,
    },
    "BTCUSDT_4h": {
        "timeframe": "4h",
        "function": "tradepulse-venue-4h",
        "dlq": "tradepulse-venue-4h-scheduler-dlq",
        "alarms": ["tradepulse-venue-4h-errors",
                   "tradepulse-venue-4h-no-invocation",
                   "tradepulse-venue-4h-dlq",
                   "tradepulse-venue-4h-killswitch"],
        "extra_metrics": (("TradePulse/venue-4h", "KillSwitchHalts"),),
        # No pre-registered window: the channel is checked from its first run.
        "window_start": None,
    },
}


def fetch_reference_bars(symbol: str, timeframe: str, needed: int) -> pd.DataFrame:
    """The last ``needed`` closed bars, paging past Binance's 1000-bar limit.

    The newest page comes from the bot's own feed, so the still-open bar is
    dropped exactly as the bot drops it. Older pages hold closed bars only.
    """
    import requests

    from .feed import _BASE, _INTERVAL, _OHLCV, fetch_klines

    bars = fetch_klines(symbol, timeframe, limit=min(needed + 1, 1000))
    pages = [bars]
    have = len(bars)
    while have < needed:
        end_ms = int(pages[0].index[0].timestamp() * 1000) - 1
        resp = requests.get(_BASE, params={"symbol": symbol,
                                           "interval": _INTERVAL[timeframe],
                                           "endTime": end_ms,
                                           "limit": min(needed - have, 1000)},
                            timeout=10.0)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        older = pd.DataFrame([r[:6] for r in rows],
                             columns=["open_time", *_OHLCV])
        older.index = pd.to_datetime(older.pop("open_time"), unit="ms", utc=True)
        older = older.astype(float)
        older.index.name = "time"
        pages.insert(0, older)
        have += len(older)
    return pd.concat(pages).sort_index()


def run_fidelity(args, as_of: date) -> dict:
    """Wire the CLI arguments into Gate A: records + reference bars + infra."""
    from ..backtesting.strategies import EmaCrossover

    decisions, state = (load_records_dynamodb(args.table, args.pk)
                        if args.source == "dynamodb"
                        else load_records_local(args.state))
    if not decisions:
        raise RuntimeError(f"no decision records for {args.pk}")

    fills = None
    if (state.get("portfolio") or {}).get("quantity_backed"):
        fills, _rejections = (load_cost_records_dynamodb(args.table, args.pk)
                              if args.source == "dynamodb"
                              else load_cost_records_local(args.state))

    # ``--since`` narrows only criterion 6. The replay always starts from the
    # first record: a book cannot be rebuilt from the middle of its history.
    ordered = _sorted_decisions(decisions)
    channel_start = CHANNELS.get(args.pk, {}).get("window_start")
    first_run = _utc(str(ordered[0].get("processed_at") or ordered[0]["bar"]))
    infra_start = (_utc(args.since) if args.since
                   else _utc(channel_start) if channel_start else first_run)
    window_start = infra_start.date()

    # Enough reference history to rebuild the bot's decision window for the
    # oldest record: its lookback plus the bars processed since.
    needed = args.lookback_bars + len(decisions) + 5
    bars = fetch_reference_bars(args.symbol, args.timeframe, needed)

    infra = None
    if args.infra == "aws":
        try:
            infra = load_infra_aws(
                function_name=args.function, dlq_queue_name=args.dlq,
                alarm_names=args.alarms, start=infra_start, end=as_of,
                region=args.region, period=_TIMEFRAME_DELTA[args.timeframe],
                extra_metrics=CHANNELS.get(args.pk, {}).get("extra_metrics", ()))
        except Exception as exc:                      # noqa: BLE001 — reported, not fatal
            infra = None
            print(f"warning: AWS infrastructure check unavailable ({exc}) "
                  f"— criterion 6 will be SKIPPED")

    inputs = FidelityInputs(
        decisions=ordered, state=state, bars=bars,
        strategy=EmaCrossover(fast=args.fast, slow=args.slow, allow_short=False),
        timeframe=args.timeframe, lookback_bars=args.lookback_bars, infra=infra,
        fills=fills, window_start=window_start,
    )
    return evaluate_fidelity(inputs, as_of)


if __name__ == "__main__":
    main()
