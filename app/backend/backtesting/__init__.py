"""TradePulse backtesting layer.

A small, self-contained framework for validating rule-based trading strategies
on historical OHLCV data — no app, DynamoDB or TensorFlow dependencies.

Typical use::

    from app.backend.backtesting import data, run_backtest, BacktestConfig, compute_metrics
    from app.backend.backtesting.strategies import EmaCrossover

    df = data.resample(data.load_glob('data/ml/historical/raw_files/BTCUSDT-1m-2021-*.csv'), '1h')
    strat = EmaCrossover(fast=20, slow=50)
    result = run_backtest(df, strat.target_positions(df), BacktestConfig(),
                          strategy_name=strat.name, timeframe='1h')
    print(compute_metrics(result, df))
"""

from . import data, indicators
from .engine import BacktestConfig, BacktestResult, Trade, run_backtest
from .metrics import Metrics, compute_metrics
from .strategy import Strategy

__all__ = [
    "data",
    "indicators",
    "Strategy",
    "BacktestConfig",
    "BacktestResult",
    "Trade",
    "run_backtest",
    "Metrics",
    "compute_metrics",
]
