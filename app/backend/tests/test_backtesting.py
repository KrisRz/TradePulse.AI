"""Tests for the backtesting engine and indicators.

Uses small synthetic OHLCV frames so the tests are fast, deterministic and do
not depend on the large historical CSVs. Runnable with pytest, or directly:

    python app/backend/tests/test_backtesting.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.backend.backtesting import (
    BacktestConfig,
    compute_metrics,
    indicators as ind,
    run_backtest,
)


def _frame(closes, highs=None, lows=None, opens=None, start="2021-01-01", freq="1h") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
    close = np.asarray(closes, dtype=float)
    open_ = np.asarray(opens, dtype=float) if opens is not None else close
    high = np.asarray(highs, dtype=float) if highs is not None else np.maximum(open_, close)
    low = np.asarray(lows, dtype=float) if lows is not None else np.minimum(open_, close)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=idx)


# --------------------------------------------------------------------------- #
# Engine correctness
# --------------------------------------------------------------------------- #

def test_always_long_zero_cost_equals_open1_to_last_close():
    # Signal at close of bar 0 -> entry at OPEN of bar 1 (no look-ahead).
    opens = [100, 110, 120, 130]
    closes = [105, 115, 125, 140]
    df = _frame(closes, opens=opens, highs=[106, 116, 126, 141], lows=[99, 109, 119, 129])
    target = pd.Series(1, index=df.index, dtype=float)
    res = run_backtest(df, target, BacktestConfig(fee_rate=0.0, slippage=0.0))
    m = compute_metrics(res, df)
    expected = df["close"].iloc[-1] / df["open"].iloc[1] - 1.0
    assert abs(m.total_return - expected) < 1e-12
    assert m.trades == 1
    assert res.trades[0].entry_time == df.index[1]


def test_short_is_mirror_of_long_at_zero_cost():
    df = _frame([100, 102, 101, 105, 108], opens=[100, 101, 102, 101, 106])
    long = run_backtest(df, pd.Series(1, index=df.index, dtype=float), BacktestConfig(fee_rate=0, slippage=0))
    short = run_backtest(df, pd.Series(-1, index=df.index, dtype=float), BacktestConfig(fee_rate=0, slippage=0))
    lr = compute_metrics(long, df).total_return
    sr = compute_metrics(short, df).total_return
    # A single mirrored trade at zero cost has short return == -long return
    # (arithmetic mirror: gross_short = -gross_long), so lr + sr == 0.
    assert abs(lr + sr) < 1e-9


def test_fees_reduce_return_and_show_drag():
    n = 20
    closes = list(np.linspace(100, 120, n))
    df = _frame(closes)
    alt = pd.Series(([1, 0] * n)[:n], index=df.index, dtype=float)  # churn every bar
    no_fee = compute_metrics(run_backtest(df, alt, BacktestConfig(fee_rate=0, slippage=0)), df)
    fee = compute_metrics(run_backtest(df, alt, BacktestConfig(fee_rate=0.001, slippage=0.0002)), df)
    assert fee.total_return < no_fee.total_return
    assert fee.total_fees_return_drag > 0
    assert fee.trades > 1


def test_stop_loss_triggers_on_adverse_move():
    # Long entered at bar1 open=100; bar2 dips to low=90 (>1% below) -> stop.
    df = _frame(
        closes=[100, 100, 95, 96],
        opens=[100, 100, 98, 96],
        highs=[101, 101, 99, 97],
        lows=[99, 99, 90, 95],
    )
    target = pd.Series([1, 1, 1, 1], index=df.index, dtype=float)
    res = run_backtest(df, target, BacktestConfig(fee_rate=0, slippage=0, stop_loss_pct=0.01))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "stop"
    # Stop fill is 1% below the 100 entry.
    assert abs(res.trades[0].exit_price - 99.0) < 1e-9


def test_take_profit_triggers_on_favourable_move():
    df = _frame(
        closes=[100, 100, 103, 103],
        opens=[100, 100, 101, 103],
        highs=[101, 101, 104, 104],  # bar2 high 104 >= 102 target
        lows=[99, 99, 100, 102],
    )
    target = pd.Series([1, 1, 1, 1], index=df.index, dtype=float)
    res = run_backtest(df, target, BacktestConfig(fee_rate=0, slippage=0, take_profit_pct=0.02))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "take_profit"
    assert abs(res.trades[0].exit_price - 102.0) < 1e-9


def test_no_reentry_into_stopped_side_until_signal_flattens():
    # After a stop, an unchanged long signal must NOT immediately re-enter.
    df = _frame(
        closes=[100, 100, 95, 95, 95],
        opens=[100, 100, 98, 95, 95],
        highs=[101, 101, 99, 96, 96],
        lows=[99, 99, 90, 94, 94],
    )
    target = pd.Series([1, 1, 1, 1, 1], index=df.index, dtype=float)  # stays long throughout
    res = run_backtest(df, target, BacktestConfig(fee_rate=0, slippage=0, stop_loss_pct=0.01))
    assert len(res.trades) == 1  # only the first entry, no re-entry while still long


# --------------------------------------------------------------------------- #
# Indicators
# --------------------------------------------------------------------------- #

def test_rsi_bounds_and_extremes():
    up = pd.Series(np.arange(1, 60, dtype=float))
    down = pd.Series(np.arange(60, 1, -1, dtype=float))
    assert abs(ind.rsi(up, 14).iloc[-1] - 100.0) < 1e-6
    assert abs(ind.rsi(down, 14).iloc[-1] - 0.0) < 1e-6
    mixed = pd.Series(np.random.RandomState(0).randn(200).cumsum() + 100)
    r = ind.rsi(mixed, 14).dropna()
    assert r.between(0, 100).all()


def test_atr_positive_and_donchian_ordering():
    rng = np.random.RandomState(1)
    close = pd.Series(rng.randn(100).cumsum() + 100)
    high = close + rng.rand(100)
    low = close - rng.rand(100)
    a = ind.atr(high, low, close, 14).dropna()
    assert (a > 0).all()
    don = ind.donchian(high, low, 20).dropna()
    assert (don["upper"] >= don["lower"]).all()


def _run_all() -> None:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed.")



# --------------------------------------------------------------------------- #
# Walk-forward: an optimiser with nothing admissible must not pick anything
# --------------------------------------------------------------------------- #
def _trend_then_chop(n=400):
    rng = np.random.default_rng(1)
    closes = 100 * np.cumprod(1 + rng.normal(0.001, 0.02, n))
    return _frame(closes, freq="1D")


def test_a_fold_with_no_admissible_combination_is_flat_and_counted():
    """Until 2026-09-16 such a fold silently traded the first grid entry."""
    from app.backend.backtesting.strategies import EmaCrossover
    from app.backend.backtesting.walkforward import NO_ADMISSIBLE_COMBO, walk_forward

    df = _trend_then_chop()
    wf = walk_forward(df, lambda fast, slow: EmaCrossover(fast=fast, slow=slow, allow_short=False),
                      {"fast": [5, 10], "slow": [20, 40]}, BacktestConfig(allow_short=False),
                      train_bars=150, test_bars=50, min_trades=10_000)

    assert wf.folds and wf.inadmissible_folds == len(wf.folds)
    assert all(f.best_params is None for f in wf.folds)
    assert wf.combined.trades == 0
    assert wf.params_summary() == {NO_ADMISSIBLE_COMBO: len(wf.folds)}


def test_an_admissible_fold_still_trades_its_pick():
    from app.backend.backtesting.strategies import EmaCrossover
    from app.backend.backtesting.walkforward import walk_forward

    df = _trend_then_chop()
    wf = walk_forward(df, lambda fast, slow: EmaCrossover(fast=fast, slow=slow, allow_short=False),
                      {"fast": [5, 10], "slow": [20, 40]}, BacktestConfig(allow_short=False),
                      train_bars=150, test_bars=50, min_trades=1)

    assert wf.inadmissible_folds == 0
    assert all(f.best_params in ({"fast": 5, "slow": 20}, {"fast": 5, "slow": 40},
                                 {"fast": 10, "slow": 20}, {"fast": 10, "slow": 40})
               for f in wf.folds)
    assert wf.combined.trades > 0


if __name__ == "__main__":
    _run_all()
