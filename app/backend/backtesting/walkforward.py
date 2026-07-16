"""Walk-forward optimisation and validation.

The single most important discipline for a strategy meant to trade real money:
optimise parameters on an in-sample window, then measure on the *next*,
untouched out-of-sample window. Roll forward and stitch all the OOS windows
into one continuous equity curve. Parameters are only ever chosen from data the
strategy would have had at the time, so the combined curve is an honest
estimate of live behaviour.

No look-ahead:
* OOS parameters come solely from the preceding train window.
* OOS signals are computed on a window that *includes* the train window as
  indicator lookback, then sliced to the test rows — so indicators are warm at
  each fold boundary without ever using future bars (all indicators are
  backward-looking).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .engine import BacktestConfig, BacktestResult, Trade, run_backtest
from .metrics import Metrics, compute_metrics
from .strategy import Strategy

StrategyFactory = Callable[..., Strategy]


def expand_grid(grid: dict[str, list]) -> list[dict]:
    """Cartesian product of a {param: [values]} grid into a list of kwargs."""
    if not grid:
        return [{}]
    keys = list(grid)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(grid[k] for k in keys))]


def _objective_value(metrics: Metrics, objective: str, min_trades: int) -> float:
    if metrics.trades < min_trades:
        return -np.inf
    if objective == "sharpe":
        return metrics.sharpe
    if objective == "return":
        return metrics.total_return
    if objective == "calmar":  # return per unit of drawdown
        dd = abs(metrics.max_drawdown)
        return metrics.total_return / dd if dd > 1e-9 else -np.inf
    raise ValueError(f"Unknown objective {objective!r}")


@dataclass
class Fold:
    index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    best_params: dict
    train_score: float
    oos: Metrics


@dataclass
class WalkForwardResult:
    strategy_name: str
    timeframe: str
    combined: Metrics
    folds: list[Fold] = field(default_factory=list)
    equity_curve: pd.Series | None = None

    def params_summary(self) -> dict:
        """How often each parameter set was chosen across folds."""
        from collections import Counter
        c = Counter(tuple(sorted(f.best_params.items())) for f in self.folds)
        return {dict(k).__repr__(): n for k, n in c.most_common()}


def walk_forward(
    df: pd.DataFrame,
    factory: StrategyFactory,
    param_grid: dict[str, list],
    config: BacktestConfig,
    train_bars: int,
    test_bars: int,
    strategy_name: str = "strategy",
    timeframe: str = "?",
    objective: str = "sharpe",
    min_trades: int = 10,
) -> WalkForwardResult:
    combos = expand_grid(param_grid)
    n = len(df)
    folds: list[Fold] = []
    all_trades: list[Trade] = []
    equity_pieces: list[pd.Series] = []
    running_equity = config.initial_capital
    init_cap = config.initial_capital

    start = 0
    fold_idx = 0
    while start + train_bars + test_bars <= n:
        train = df.iloc[start: start + train_bars]
        test_start_i = start + train_bars
        test_end_i = test_start_i + test_bars
        ext = df.iloc[start: test_end_i]           # train + test, for lookback
        test = df.iloc[test_start_i: test_end_i]

        # --- in-sample: pick best params on the train window only ---
        best_params, best_score = combos[0], -np.inf
        for params in combos:
            strat = factory(**params)
            res = run_backtest(train, strat.target_positions(train), config,
                               strategy_name, timeframe)
            score = _objective_value(compute_metrics(res, train), objective, min_trades)
            if score > best_score:
                best_score, best_params = score, params

        # --- out-of-sample: apply best params, signals warmed via ext lookback ---
        strat = factory(**best_params)
        target_test = strat.target_positions(ext).reindex(test.index).fillna(0.0)
        oos_cfg = BacktestConfig(**{**config.__dict__, "initial_capital": init_cap})
        oos_res = run_backtest(test, target_test, oos_cfg, strategy_name, timeframe)
        oos_metrics = compute_metrics(oos_res, test)

        # stitch OOS equity into one compounded curve
        piece = oos_res.equity_curve / init_cap * running_equity
        equity_pieces.append(piece)
        running_equity = float(piece.iloc[-1]) if len(piece) else running_equity
        all_trades.extend(oos_res.trades)

        folds.append(Fold(
            index=fold_idx,
            train_start=train.index[0], train_end=train.index[-1],
            test_start=test.index[0], test_end=test.index[-1],
            best_params=best_params, train_score=best_score, oos=oos_metrics,
        ))
        start += test_bars
        fold_idx += 1

    combined_equity = pd.concat(equity_pieces) if equity_pieces else pd.Series(dtype=float)
    combined_result = BacktestResult(
        strategy_name=strategy_name,
        timeframe=timeframe,
        equity_curve=combined_equity,
        trades=all_trades,
        config=config,
        bars=len(combined_equity),
        start=combined_equity.index[0] if len(combined_equity) else None,
        end=combined_equity.index[-1] if len(combined_equity) else None,
    )
    price_span = df.loc[combined_equity.index] if len(combined_equity) else None
    combined = compute_metrics(combined_result, price_span)

    return WalkForwardResult(
        strategy_name=strategy_name,
        timeframe=timeframe,
        combined=combined,
        folds=folds,
        equity_curve=combined_equity,
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _candidates():
    """(name, factory, grid) for each strategy we walk-forward."""
    from .strategies import EmaCrossover, RsiMeanReversion
    from .strategies.regime_routed import RegimeRouted

    def ema(fast, slow):
        return EmaCrossover(fast=fast, slow=slow)

    def rsi(period, oversold, overbought):
        return RsiMeanReversion(period=period, oversold=oversold, overbought=overbought)

    def routed(adx_threshold, trend_fast, trend_slow):
        return RegimeRouted(
            trend_strategy=EmaCrossover(fast=trend_fast, slow=trend_slow),
            adx_threshold=adx_threshold,
        )

    return [
        ("EMA", ema, {"fast": [10, 20, 30], "slow": [50, 100, 200]}),
        ("RSI-MR", rsi, {"period": [14], "oversold": [25, 30, 35], "overbought": [65, 70, 75]}),
        ("Regime", routed, {"adx_threshold": [20, 25, 30], "trend_fast": [20], "trend_slow": [50, 100]}),
    ]


def _print_row(name: str, m: Metrics) -> None:
    pf = "inf" if m.profit_factor == float("inf") else f"{m.profit_factor:.2f}"
    print(
        f"{name:<12}{m.total_return * 100:>+8.0f}%{m.cagr * 100:>+8.0f}%{m.sharpe:>8.2f}"
        f"{m.max_drawdown * 100:>8.0f}%{m.win_rate * 100:>6.0f}%{pf:>7}{m.trades:>8}"
    )


def main(argv: list[str] | None = None) -> None:
    import argparse
    from . import data as data_mod
    from .metrics import compute_metrics

    p = argparse.ArgumentParser(description="Walk-forward validate strategies (out-of-sample).")
    p.add_argument("--data", required=True, help="CSV path or glob pattern")
    p.add_argument("--timeframe", default="1h")
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--train-bars", type=int, default=2000, help="in-sample window length")
    p.add_argument("--test-bars", type=int, default=500, help="out-of-sample window length")
    p.add_argument("--objective", default="sharpe", choices=["sharpe", "return", "calmar"])
    p.add_argument("--fee", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0002)
    p.add_argument("--sl", type=float, default=None)
    p.add_argument("--tp", type=float, default=None)
    p.add_argument("--no-short", action="store_true")
    args = p.parse_args(argv)

    raw = data_mod.load_glob(args.data) if any(c in args.data for c in "*?[") else data_mod.load_csv(args.data)
    raw = data_mod.slice_dates(raw, args.start, args.end)
    df = data_mod.resample(raw, args.timeframe) if args.timeframe != "1m" else raw

    cfg = BacktestConfig(
        fee_rate=args.fee, slippage=args.slippage,
        stop_loss_pct=args.sl, take_profit_pct=args.tp,
        allow_short=not args.no_short,
    )

    print(f"Walk-forward | {df.index[0].date()} → {df.index[-1].date()} | {args.timeframe} | "
          f"train={args.train_bars} test={args.test_bars} bars | objective={args.objective}\n")
    header = f"{'strategy':<12}{'OOS ret':>9}{'CAGR':>8}{'Sharpe':>8}{'maxDD':>8}{'win%':>6}{'PF':>7}{'trades':>8}"
    print(header)
    print("-" * len(header))

    results = []
    for name, factory, grid in _candidates():
        wf = walk_forward(
            df, factory, grid, cfg,
            train_bars=args.train_bars, test_bars=args.test_bars,
            strategy_name=name, timeframe=args.timeframe, objective=args.objective,
        )
        results.append(wf)
        _print_row(name, wf.combined)

    # Buy & hold over the exact OOS span (first fold's test start → last bar).
    if results and results[0].equity_curve is not None and len(results[0].equity_curve):
        oos_span = df.loc[results[0].equity_curve.index]
        bh_target = pd.Series(1, index=oos_span.index, dtype=float)
        bh = compute_metrics(
            run_backtest(oos_span, bh_target,
                         BacktestConfig(fee_rate=args.fee, slippage=args.slippage, allow_short=False),
                         "Buy&Hold", args.timeframe),
            oos_span,
        )
        _print_row("Buy&Hold", bh)

    # Parameter stability for the regime-routed strategy.
    print()
    for wf in results:
        if wf.strategy_name == "Regime":
            print(f"Regime param choices across {len(wf.folds)} folds:")
            for params, count in wf.params_summary().items():
                print(f"  {count:>2}×  {params}")


if __name__ == "__main__":
    main()

