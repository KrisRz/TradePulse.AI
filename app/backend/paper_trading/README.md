# Paper-trading bot

Runs a **backtest-validated** strategy on live Binance data against a virtual
portfolio. It reuses the *exact* strategy signal code and cost model from the
`backtesting` package, so the live bot and the backtest cannot silently diverge
— proven by the equivalence test in `tests/test_paper_trading.py`.

Default strategy: **long-only EMA 20/100 on the daily (1d) timeframe** — the
configuration that survived walk-forward + a blind 2024/2025 holdout (see
`../backtesting/README.md`).

## How it works

```
Binance public klines (closed bars only)
  → Strategy.target_positions(df).iloc[-1]     # same code as the backtest
  → PaperPortfolio.reconcile(target, price)    # same cost model as the backtest
  → JSON state file (position, equity, trades)
```

Each `step` is **idempotent per bar**: if the latest closed bar was already
processed it does nothing, so it is safe to run more often than the bar
interval.

## Usage

```bash
# Process the latest closed daily bar
python -m app.backend.paper_trading.run step

# Show portfolio status without trading
python -m app.backend.paper_trading.run status

# Custom params (e.g. hourly, different EMA)
python -m app.backend.paper_trading.run step --timeframe 1h --fast 20 --slow 100
```

State is written to `paper_state/<symbol>_<timeframe>.json` (git-ignored).

## Running it continuously

For a 1d strategy, run `step` once a day shortly after the daily close (00:00
UTC). Example cron entry:

```cron
5 0 * * *  cd /Applications/TradePuls && PYTHONPATH=. .venv/bin/python -m app.backend.paper_trading.run step >> paper_state/bot.log 2>&1
```

## Not included yet (deliberately)

- **Real order execution.** This is paper only. Real trading needs a hardened
  execution/risk track (kill-switch, hard limits, testnet→mainnet, key
  security) before a single real dollar — that is a separate phase.
- **Intrabar stop-loss/take-profit.** The daily trend-following edge is *hurt*
  by tight stops (shown in backtests), so the default bot is signal-only.
