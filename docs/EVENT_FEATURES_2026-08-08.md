# Tabela cech per zdarzenie — dataset meta-labelera GOTOWY (2026-08-08)

> Krok 1 pre-rejestrowanej ścieżki D11, po odblokowaniu próby (128 zdarzeń,
> docs/POOLED_EVENTS_2026-08-08.md). Narzędzie:
> `scripts/research/event_feature_table.py` → `data/ml/events_features.csv`
> (gitignorowany, regenerowalny). Projekt cech ZADEKLAROWANY w docstringu
> PRZED policzeniem czegokolwiek — żadna cecha nie była dobierana po
> obejrzeniu korelacji z etykietami.

## Kształt: 128 zdarzeń × 12 cech + etykieta (net_return po kosztach / win)

**Cechy per-aktywo** (z własnych świec 1d, pokrycie 87–100%):
`vol20`, `vol_pctl_1y` (spokój zmienności — cecha ocalona z
REGIME_FILTER_2026-08-08), `trend_gap` (siła sygnału EMA), `ret20`
(momentum wejścia), `dd_from_1y_high` (pozycja w cyklu aktywa).

**Cechy rynkowe** (serie BTC jako proxy cyklu całego krypto — funding/OI/
on-chain istnieją tylko dla BTC; cykl, który opisują, jest wspólny):
`btc_vol20`, `btc_trend_gap`, `funding_last`, `funding_cum30`,
`doi7`, `doi30` (zmiana open interest), `mvrv_z` (z-score CapMVRVCur w
kroczącym oknie 4 lat).

## Dyscyplina point-in-time (najważniejsza część tego kroku)

- Czas decyzji = close świecy sygnałowej t (fill następnym openem); cechy
  liczone ze świecy sygnałowej, NIE ze świecy wejścia.
- Funding: settlementy o timestampie ≤ czas decyzji (dokładne, stemplowane).
- Serie dzienne zewnętrzne (OI, MVRV): wartość z dnia **t−1** (shift o pełny
  dzień) — lag publikacji end-of-day nie może przeciec.
- `mvrv_z`: wyłącznie kroczące okno 1460 d (żadnych statystyk z pełnej próby).
- Zerowa baza OI → pct_change = NaN (bez `inf`), bez pad-fillu dziur.
- **Braki NIE są imputowane**: zdarzenia sprzed startu serii (funding
  2020-01, OI 2020-09, roczne okna percentyli) mają NaN. Pokrycie: 91/128
  zdarzeń z kompletem 12 cech; decyzja o obsłudze braków należy do etapu
  modelu (i musi być pre-rejestrowana tam).

## Sanity-check zakresów (bez patrzenia na korelacje z etykietą)

`trend_gap` min = 0,000 (wejścia dzieją się tuż po przecięciu — zgodnie z
konstrukcją), `mvrv_z` −1,35…+3,12 (dno bessy → euforia; rozsądny zakres),
`funding_cum30` do 5,4% (szczyty lewarowanej chciwości), `dd_from_1y_high`
mediana −37% (typowe wejście EMA following po odbiciu od dna). Wygląda jak
rynek, nie jak błąd.

## Co dalej (krok 2 — osobna sesja, żeby projekt splitu nie powstawał
z tym samym kontekstem, co dataset)

Model wg D11: logit/XGBoost z silną regularyzacją, split purged po WSPÓLNYM
czasie wszystkich aktywów + embargo ≥60 d (mediana holdu!) + wariant
leave-one-asset-out; metryka = wpływ na P&L/Sharpe po kosztach (NIE
accuracy — baseline 36% win rate); kalibracja przed progiem. Poprzeczka:
pobić czyste EMA20/100 na harnessie M4. Przegrana = zostajemy przy EMA.
Adopcja wyłącznie po M5, przez własne okno paper.

## Jak powtórzyć

```bash
PYTHONPATH=. python scripts/research/event_feature_table.py
```
