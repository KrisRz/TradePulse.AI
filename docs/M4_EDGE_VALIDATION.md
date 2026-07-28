# M4 — Edge validation (walk-forward, out-of-sample) — 2026-07-16

> **⚠️ SPROSTOWANIE 2026-07-28.** Liczby w tabeli F0 („EMA Sharpe 1.11–1.18")
> należą do strategii **przestrajanej na każdym foldzie**, a nie do stałego
> EMA20/100, które handluje na Lambdzie. Optymalizator walk-forward nie wybrał
> 20/100 ani razu (0/73 foldów — zawsze 10/50), więc zdanie „Paper bot keeps
> trading EMA20/100 … exactly what is deployed on Lambda" nie znaczyło, że te
> Sharpe'y dotyczą produkcji.
>
> Konfiguracja produkcyjna została zmierzona osobno 2026-07-28 i **broni się**:
>
> | layout | adaptive (poniżej) | **stałe 20/100 = prod** | Buy&Hold |
> |---|---|---|---|
> | 730/180 | 1.11 | **1.01** | 0.87 |
> | 500/125 | 1.14 | **1.00** | 0.97 |
> | 1000/250 | 1.12 | **1.14** | 1.00 |
> | 365/90 | 1.18 | **1.02** | 0.81 |
>
> Bije buy & hold w każdym layoucie; brak śladów przeuczenia (in-sample ranga
> 28/42). Pełna analiza: `docs/ANALIZA_KALIBRACJI_2026-07-28.md`,
> reprodukcja: `python scripts/research/calibration_audit.py`.

Data: Binance BTCUSDT/ETHUSDT, fresh through 2026-07-16
(`data/ml/historical/`, regenerate with `backtesting.download`).
Engine: shared backtest engine (next-bar-open, fees 0.1% + slippage 0.02%,
long-only). Walk-forward: params fitted in-sample per fold, metrics reported
out-of-sample only.

## F0 — Baseline reproduction (BTC 1d, long-only)

| fold layout (train/test bars) | EMA Sharpe | B&H Sharpe | EMA maxDD | B&H maxDD |
|---|---|---|---|---|
| 730 / 180 | **1.11** | 0.87 | −49% | −77% |
| 500 / 125 | **1.14** | 0.97 | −50% | −77% |
| 1000 / 250 | **1.12** | 1.00 | −50% | −77% |
| 365 / 90 | **1.18** | 0.81 | −43% | −77% |

EMA long-only beats buy & hold risk-adjusted in **every** fold layout and
roughly halves max drawdown. **Robust — stays as the core strategy.**

Regime-routed (EMA gated by ADX) looked spectacular in one layout
(Sharpe 1.63) and mediocre in others (0.83–0.94): **fold-layout sensitive →
rejected** (instability = overfitting the switch).

### Fee sensitivity (730/180, EMA)

| fee per side | OOS Sharpe |
|---|---|
| 0.075% | 1.12 |
| 0.1% | 1.11 |
| 0.2% | 1.08 |
| 0.3% | **1.06** |

Only 36 trades over ~6.5 OOS years → the edge **survives even 0.3% fees**
(the old "dies above 0.3%" note came from a shorter-TF variant; updated).

## F3 — Edge transfer

| market / TF | EMA Sharpe | B&H Sharpe | EMA maxDD | verdict |
|---|---|---|---|---|
| ETH 1d | 1.01 | 0.96 | −57% | marginal — not worth a second bot yet |
| BTC 4h | 0.99 | 0.90 | −60% | worse than 1d, 3× the trades — **no** |

**Decision ❓D10: stay BTC 1d only.** Revisit ETH after the 8-week paper gate.

## F2 — Volatility-targeting sizing (return-level study)

`scripts/research/vol_targeting_study.py` (weights on next-bar returns,
costs on turnover):

| variant | full 2017-26 Sharpe | 2022-26 Sharpe | full maxDD |
|---|---|---|---|
| EMA full-equity | 0.93 | **0.72** | −64% |
| vol-target 30–60% | 0.91–0.99 | 0.56–0.70 | −31..−46% |

Vol targeting cuts drawdown but **degrades risk-adjusted return in the
recent regime (2022+) across every target level**, and doubles turnover.
**Decision: NO sizing layer — full-equity stays; the engine keeps its
simple ±1/0 position model.**

## F1 / ❓D9 — ML as a filter over EMA

Two findings close this decision:

1. **The existing 6-layer "enterprise" models cannot honestly filter a 1d
   strategy.** They were trained on 1-minute-candle features for intraday
   horizons (L5 v2.0 metadata: 15 features from 1m bars, intraday outcome
   targets). Using them to veto 1d trend entries is a horizon mismatch —
   any walk-forward "result" would be noise dressed as validation.
2. **Simple 1d regime filters do not robustly help** (same simulator):
   `price>SMA200` improves 2022+ (0.92 vs 0.72) but *worsens* the full
   period (0.91 vs 0.93); `SMA200 rising` is worse everywhere. Regime
   switching by ADX already failed fold-sensitivity above.

**Decision ❓D9: pure EMA.** An ML filter enters only as a purpose-built
model **trained on 1d features with 1d-horizon targets**, and only if it
beats pure EMA on this same walk-forward harness (that is M4/F4, gated —
currently not justified by any evidence).

## What this means for the roadmap

- Paper bot keeps trading **EMA20/100 long-only, BTC 1d, full equity** —
  exactly what is deployed on Lambda.
- M4 is **done as a decision milestone**: measured, decided, documented.
- Next milestone: **M5** — let the paper bot accumulate ≥8 weeks of live
  decision records; then evaluate against the hard gates
  (OOS Sharpe ≥ 1 ✅ already, paper maxDD ≤ 25%, PF ≥ 1.3, net P&L > 0,
  live tracking error < 10%).
