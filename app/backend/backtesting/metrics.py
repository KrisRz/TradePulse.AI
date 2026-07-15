"""Performance metrics computed from a BacktestResult."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .engine import BacktestResult

_SECONDS_PER_YEAR = 365.0 * 24 * 3600


@dataclass
class Metrics:
    strategy: str
    timeframe: str
    start: str
    end: str
    bars: int
    trades: int
    total_return: float       # fraction, e.g. 0.42 = +42%
    cagr: float
    sharpe: float
    max_drawdown: float       # negative fraction, e.g. -0.23
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    expectancy: float         # mean net return per trade
    avg_bars_held: float
    exposure: float           # fraction of bars holding a position
    total_fees_return_drag: float  # gross_return_sum - net_return_sum
    buy_hold_return: float
    final_equity: float

    def as_dict(self) -> dict:
        return asdict(self)


def _periods_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 3:
        return 0.0
    # Unit-safe: total_seconds() ignores the index's datetime64 resolution
    # (ns/us/ms), unlike a raw int64 view which silently changes scale.
    diffs = pd.Series(index).diff().dropna().dt.total_seconds()
    dt = float(diffs.median())  # median bar length in seconds
    if dt <= 0:
        return 0.0
    return _SECONDS_PER_YEAR / dt


def _max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min()) if len(drawdown) else 0.0


def _sharpe(equity: pd.Series, ppy: float) -> float:
    rets = equity.pct_change().dropna()
    if len(rets) < 2:
        return 0.0
    sd = rets.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(rets.mean() / sd * np.sqrt(ppy))


def compute_metrics(result: BacktestResult, df: pd.DataFrame | None = None) -> Metrics:
    eq = result.equity_curve.dropna()
    tf = result.trades_frame
    ppy = _periods_per_year(eq.index)

    total_return = float(eq.iloc[-1] / result.config.initial_capital - 1.0) if len(eq) else 0.0

    years = 0.0
    if result.start is not None and result.end is not None:
        years = (result.end - result.start).total_seconds() / _SECONDS_PER_YEAR
    cagr = float((eq.iloc[-1] / result.config.initial_capital) ** (1.0 / years) - 1.0) if years > 0 and len(eq) else 0.0

    if len(tf):
        wins = tf[tf["net_return"] > 0]["net_return"]
        losses = tf[tf["net_return"] <= 0]["net_return"]
        win_rate = float(len(wins) / len(tf))
        gross_win = float(wins.sum())
        gross_loss = float(-losses.sum())
        profit_factor = float(gross_win / gross_loss) if gross_loss > 0 else float("inf")
        avg_win = float(wins.mean()) if len(wins) else 0.0
        avg_loss = float(losses.mean()) if len(losses) else 0.0
        expectancy = float(tf["net_return"].mean())
        avg_bars_held = float(tf["bars_held"].mean())
        fees_drag = float(tf["gross_return"].sum() - tf["net_return"].sum())
        exposure = float(tf["bars_held"].sum() / result.bars) if result.bars else 0.0
    else:
        win_rate = profit_factor = avg_win = avg_loss = expectancy = 0.0
        avg_bars_held = exposure = fees_drag = 0.0

    buy_hold = 0.0
    if df is not None and len(df):
        buy_hold = float(df["close"].iloc[-1] / df["close"].iloc[0] - 1.0)

    return Metrics(
        strategy=result.strategy_name,
        timeframe=result.timeframe,
        start=str(result.start),
        end=str(result.end),
        bars=result.bars,
        trades=len(tf),
        total_return=total_return,
        cagr=cagr,
        sharpe=_sharpe(eq, ppy),
        max_drawdown=_max_drawdown(eq),
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        expectancy=expectancy,
        avg_bars_held=avg_bars_held,
        exposure=exposure,
        total_fees_return_drag=fees_drag,
        buy_hold_return=buy_hold,
        final_equity=float(eq.iloc[-1]) if len(eq) else result.config.initial_capital,
    )
