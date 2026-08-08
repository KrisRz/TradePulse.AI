# Spis zdarzeń poolingu: 128 > 100 — meta-labeler ODBLOKOWANY (2026-08-08)

> Pytanie usera: „czy dane do nauki można pobrać z historii, zamiast czekać?"
> Odpowiedź: TAK. Pre-rejestrowana ścieżka z researchu 2026-08-07 („pooling
> BTC+ETH+2–3 majorsy z identyczną regułą") zmierzona:
> `scripts/research/pooled_events_census.py`.

## Uniwersum (zadeklarowane REGUŁĄ przed liczeniem, bez cherry-pickingu)

Pary USDT spot na Binance, top kapitalizacji, bez stablecoinów, notowane
≥5 lat: **BNB, XRP, LTC, ADA, DOGE + SOL** (największy z kohorty ~6-letniej).
Dane: bulk archives data.binance.vision (immutable), **integrity: 6/6 clean,
zero luk**, ucięte na holdoutcie <2026-07-16. Pliki gitignorowane —
regeneracja: `bulk_download.py --symbol X --interval 1d --start <listing>
--end 2026-07-16`.

## Wynik

Zdarzenie = jedno wejście long EMA20/100 (sygnał 0→1), fill na następnym
otwarciu, wyjście na otwarciu po zgaśnięciu sygnału, netto po 2×(0,1%+0,02%).
Zdarzenia otwarte na holdoutcie odrzucone (brak etykiety).

| rynek | świec | zdarzeń | wygranych | mediana hold |
|---|---|---|---|---|
| BTC | 3240 | 15 | 47% | 60 d |
| ETH | 3240 | 16 | 44% | 70 d |
| BNB | 3174 | 17 | 35% | 54 d |
| XRP | 2995 | 23 | 17% | 50 d |
| LTC | 3137 | 17 | 35% | 50 d |
| ADA | 3012 | 13 | 46% | 84 d |
| DOGE | 2568 | 16 | 31% | 48 d |
| SOL | 2165 | 11 | 45% | 49 d |
| **POOL** | | **128** | **36%** | |

**128 > 100 → próg osiągnięty.** Balans klas 46/82 — uczciwie uczący się
klasyfikator jest wykonalny.

## Co mówią te liczby (ważne dla projektu meta-labelera)

1. **Mediana zdarzenia jest UJEMNA na każdym rynku** (−2,7…−11,6%), a pool
   wygrywa tylko 36% wejść. To jest anatomia trend-followingu: strategia
   żyje z ogona wielkich wygranych, które płacą za większość małych strat.
   Zadanie meta-labelera jest przez to precyzyjnie zdefiniowane: **odfiltrować
   przegrane wejścia, NIE gubiąc rzadkich wielkich wygranych** — czyli metryką
   nie może być accuracy (36% baseline!), tylko wpływ na P&L/Sharpe po
   kosztach.
2. **Pooling importuje przesunięcie rozkładów między rynkami** — model uczy
   się „majorsów krypto", nie „BTC w szczególe". Znany, zaakceptowany koszt
   (tak samo zrobiło badanie 10-krypto). Konsekwencja metodologiczna:
   walidacja MUSI być grupowana — leave-one-asset-out albo purged split po
   CZASIE równocześnie na wszystkich rynkach (zdarzenia z różnych rynków
   nakładają się kalendarzowo — hossa 2021 jest jedna, nie osiem).
3. XRP (17% wygranych) i DOGE (31%) pokazują, że reguła bywa na niektórych
   rynkach wyraźnie słabsza — to dobra wiadomość dla ucznia: jest czego się
   uczyć (cechy reżimowe mogą to widzieć), i przestroga dla walidacji
   (per-asset shift jest realny, pkt 2).

## Co dalej (kolejność, nic nie dotyka M5)

1. Zbudować tabelę cech per zdarzenie (stan NA WEJŚCIU: funding, ΔOI,
   MVRV-Z, calm-vol z REGIME_FILTER, zmienność 20d, siła trendu) — dane już
   pobrane 2026-08-07.
2. Meta-labeler wg pre-rejestracji D11: triple-barrier/net-return label,
   logit/XGBoost z silną regularyzacją, purged split z embargo ≥ mediana
   hold (≈60 d!), kalibracja przed progiem.
3. Poprzeczka (ustalona 2026-08-08): **pobić czyste EMA20/100 po kosztach
   na harnessie M4**. Przegrana = zostajemy przy czystym EMA (to też wynik).
4. Adopcja wyłącznie po M5, przez własne okno paper.

## Jak powtórzyć

```bash
PYTHONPATH=. python scripts/research/pooled_events_census.py
```
