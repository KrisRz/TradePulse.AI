# Backtesting layer

A small, self-contained framework for validating **rule-based** trading
strategies on historical OHLCV data. No app / DynamoDB / TensorFlow imports, so
it runs in a fraction of a second and can be trusted in isolation.

This is the "strategy foundation" the project previously lacked: a way to get
**ground truth** on whether any given rule actually has an edge — *before*
wiring it (or the ML ensemble) into the live loop.

## Layout

| File | Purpose |
|------|---------|
| `indicators.py` | EMA, RSI (Wilder), ATR, MACD, Bollinger, Donchian — pure pandas/numpy, backward-looking only |
| `data.py` | Load both repo CSV formats, resample 1m → any timeframe, date-slice |
| `strategy.py` | `Strategy` base class — returns a target position (−1/0/+1) per bar |
| `engine.py` | Event-driven backtester: next-bar-open execution, fees, slippage, intrabar SL/TP |
| `metrics.py` | Return, CAGR, Sharpe, max drawdown, win rate, profit factor, fee drag |
| `strategies/` | `EmaCrossover` (trend), `RsiMeanReversion` (range) |
| `run.py` | CLI report runner |
| `download.py` | Re-download historical OHLCV from Binance (data is not in git) |

## Getting the data

Historical price CSVs are **not committed** (they were ~556 MB and are freely
re-downloadable). Regenerate what you need from Binance's public API:

```bash
python -m app.backend.backtesting.download \
    --symbol BTCUSDT --interval 1h --start 2020-01-01 --end 2024-12-31 \
    --out data/ml/historical/BTCUSDT_1h_2020_2024.csv
```

## Correctness guarantees (see `tests/test_backtesting.py`)

- **No look-ahead**: a target decided at the close of bar *t* is executed at the
  **open of bar t+1**. Verified to the last decimal against a buy&hold baseline.
- **Symmetric shorts**: a short is the exact arithmetic mirror of a long at zero
  cost.
- **Costs bite**: every fill pays slippage + a per-side fee; fee drag is reported
  explicitly.
- **Intrabar SL/TP**: stop-loss / take-profit checked against each bar's
  high/low (pessimistic: stop assumed first if both could trigger).

## Usage

```bash
# One year of BTCUSDT at several timeframes
python -m app.backend.backtesting.run \
    --data 'data/ml/historical/raw_files/BTCUSDT-1m-2021-*.csv' \
    --timeframe 15m,1h,4h

# With risk management, long-only
python -m app.backend.backtesting.run \
    --data 'data/ml/historical/raw_files/BTCUSDT-1m-2022-*.csv' \
    --timeframe 1h --sl 0.01 --tp 0.02 --no-short
```

## What the first runs told us (BTCUSDT, 1h)

| Regime | Buy&Hold | EMA20/50 | RSI-MR | Key point |
|--------|---------:|---------:|-------:|-----------|
| 2021 bull | **+59%** | −16% | −26% | Naive strategies lose to simply holding in a trend |
| 2022 bear | −65% | −41% | −54% | They lose *less* than holding, but still lose |

Findings:

1. **Fees are the dominant cost at short timeframes.** EMA on 15m fired 730
   trades in 2021 with **+146% fee drag** → −89% return. The same rule on 4h
   (50 trades) had ~10% drag. This is almost certainly why the live system bled
   on 1m scalping (34.8% "tiny losses" in `NAPRAWA.md`).
2. **Naive symmetric long/short has no edge as-is.** No fixed-parameter variant
   beat buy&hold in either regime.
3. **Risk management trades return for drawdown.** SL 1% / TP 2% roughly halved
   max drawdown but usually cut total return too (it clips winners). In the 2022
   bear, long-only + SL/TP was the least-bad configuration.

This is the *healthy, expected* result — and exactly the point of building the
framework: we can now measure instead of guess.

## Next steps (Phase 1b)

- **Regime filtering**: only run EMA in trends and RSI-MR in ranges (use ADX /
  realized-vol to gate), instead of trading both everywhere.
- **Parameter search + walk-forward**: optimise on in-sample windows, validate
  out-of-sample (2024–2026 fresh data never seen in dev) to avoid overfitting.
- **ATR/Donchian breakout** as a third, complementary strategy.
- **ML as a confirmation filter** on top of a strategy that already shows edge —
  not as the sole signal source.
