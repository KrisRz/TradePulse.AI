"""Tests for the paper-trading portfolio.

The key test proves the paper portfolio and the backtest engine produce the
*same* equity when fed the same prices in the same order — i.e. backtest and
live share one accounting/cost model and cannot diverge.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.backend.backtesting import BacktestConfig, compute_metrics, run_backtest
from app.backend.backtesting.strategies import EmaCrossover
from app.backend.paper_trading.portfolio import PaperPortfolio


def _drive_like_engine(df: pd.DataFrame, target: pd.Series, cfg: BacktestConfig) -> PaperPortfolio:
    """Feed the portfolio bar-by-bar with the engine's execution convention:
    the target decided at close of bar t-1 is executed at the OPEN of bar t;
    any position still open at the end is closed at the last close.
    """
    port = PaperPortfolio(fee_rate=cfg.fee_rate, slippage=cfg.slippage,
                          initial_capital=cfg.initial_capital)
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    tgt = target.reindex(df.index).fillna(0).round().astype(int).to_numpy()
    times = [str(t) for t in df.index]
    pending = 0
    for i in range(len(df)):
        port.reconcile(pending, o[i], times[i])   # execute previous target at this open
        pending = int(tgt[i])
    port.reconcile(0, c[-1], times[-1])           # flat at the end, like engine
    return port


def _frame(closes, opens):
    idx = pd.date_range("2021-01-01", periods=len(closes), freq="1D", tz="UTC")
    close = np.asarray(closes, float)
    open_ = np.asarray(opens, float)
    return pd.DataFrame({
        "open": open_, "high": np.maximum(open_, close),
        "low": np.minimum(open_, close), "close": close,
    }, index=idx)


def test_portfolio_matches_engine_synthetic():
    df = _frame([100, 105, 103, 108, 110, 107, 112],
                [100, 101, 104, 102, 109, 111, 108])
    target = pd.Series([1, 1, 0, 1, 1, 0, 1], index=df.index, dtype=float)
    cfg = BacktestConfig(fee_rate=0.001, slippage=0.0002, allow_short=True)

    engine = run_backtest(df, target, cfg)
    port = _drive_like_engine(df, target, cfg)

    eng_final = float(engine.equity_curve.iloc[-1])
    assert abs(port.equity() - eng_final) < 1e-6
    assert len(port.trades) == len(engine.trades)
    for pt, et in zip(port.trades, engine.trades):
        assert abs(pt["net_return"] - et.net_return) < 1e-9


def test_portfolio_matches_engine_real_ema():
    # Deterministic pseudo-market; EMA strategy target run through both paths.
    rng = np.random.RandomState(42)
    close = 100 * np.exp(np.cumsum(rng.randn(600) * 0.02))
    idx = pd.date_range("2020-01-01", periods=600, freq="1D", tz="UTC")
    df = pd.DataFrame({
        "open": close * (1 + rng.randn(600) * 0.001),
        "high": close * 1.01, "low": close * 0.99, "close": close,
    }, index=idx)
    strat = EmaCrossover(fast=20, slow=100, allow_short=False)
    target = strat.target_positions(df)
    cfg = BacktestConfig(fee_rate=0.001, slippage=0.0002, allow_short=True)

    engine = run_backtest(df, target, cfg)
    port = _drive_like_engine(df, target, cfg)

    assert abs(port.equity() - float(engine.equity_curve.iloc[-1])) < 1e-6
    assert len(port.trades) == len(engine.trades)


def test_reconcile_is_idempotent_when_target_unchanged():
    port = PaperPortfolio()
    assert port.reconcile(1, 100.0, "t0") is not None   # opens long
    assert port.reconcile(1, 105.0, "t1") is None        # already long -> no-op
    assert len(port.trades) == 0                          # no close yet


def test_persistence_roundtrip():
    port = PaperPortfolio(fee_rate=0.001, slippage=0.0002)
    port.reconcile(1, 100.0, "t0")
    port.reconcile(0, 110.0, "t1")   # one closed trade
    restored = PaperPortfolio.from_dict(port.to_dict())
    assert restored.side == port.side
    assert abs(restored.equity() - port.equity()) < 1e-12
    assert len(restored.trades) == len(port.trades)


def _run_all() -> None:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed.")


if __name__ == "__main__":
    _run_all()
