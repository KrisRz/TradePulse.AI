# Kraken jako giełda bota — WYNIKI (2026-10-30)

Projekt: `docs/KRAKEN_VENUE_DESIGN_2026-10-30.md`, commit `407c48b` przed pomiarem,
SHA-256 `253d2061…f206674c`, wydrukowany przez skrypt.
Skrypt: `PYTHONPATH=. .venv/bin/python scripts/research/kraken_venue_study.py --cache <dir>`.

## Werdykt: **Kraken PASS 4/4 → giełda pilota**

| Warunek | Próg | Wynik | |
|---|---|---|---|
| R1: Sharpe ≥ B&H przy 0,80%, GBP | ≥ 3/4 układów | **4/4** | PASS |
| R2: DD konta ≤ 25% (`w = 0,5`, gotówka 0%, 0,80%) | 730 d ≥ 75%, 365 d ≥ 90% | **76%**, **93%** | PASS (na styk) |
| R3: zgodność sygnału EMA20/100 | ≥ 95% | **99,6%** (GBP), 99,8% (USD) | PASS |
| R4: koszt kupna £100 względem ceny środkowej | ≤ 0,10% | **0,002%** (mediana) | PASS |

## M1 — strategia w GBP, ciągłe OOS (Sharpe / maxDD, strategia vs B&H)

| Opłata | 730/180 | 500/125 | 1000/250 | 365/90 |
|---|---|---|---|---|
| 0,10% (Binance) | 1,03 −47% vs 0,84 −73% | 1,13 vs 0,96 | 1,18 vs 0,98 | 1,09 vs 0,80 |
| 0,40% (Kraken maker) | 1,01 −48% | 1,11 | 1,16 | 1,07 |
| **0,80% (Kraken taker)** | **0,97 −48%** | **1,08** | **1,13** | **1,04** |

W USD obraz jest ten sam: 4/4 przy każdej opłacie, przy 0,80% Sharpe 1,00 / 1,08 /
1,17 / 1,04 wobec B&H 0,87 / 0,96 / 0,99 / 0,81.

**Ile kosztuje rezygnacja z Binance:** około **0,05–0,06 Sharpe'a** przy opłacie
taker (0,10% → 0,80%) albo 0,02 przy zleceniach post-only (0,40%). Przewaga nad B&H
zostaje we wszystkich układach. Binance byłby tańszy, ale nie da się na nim handlować
(konto UE i MiCA, do tego hack z 2026-10-29). Ta różnica decyzji nie zmienia.

## M2 — limit spadku na całym koncie, `w = 0,5`, GBP, 0,80%, gotówka 0%

- Pełna próba od 2018: **maxDD −26,7%**, CAGR +17,9%.
- Okna 365 dni (394): DD ≤ 25% w **93%**, mediana DD −13,6%.
- Okna 730 dni (342): DD ≤ 25% w **76%**, mediana DD −21,7%.

⚠️ **R2 przechodzi na styk, a najgorszy przypadek z historii (−26,7%) przekracza
25%.** Wniosek dla pilota: limit 25% musi być twardym kill-switchem na kapitale
konta, a nie tylko kryterium oceny. Ten kill-switch zadziała mniej więcej w co
czwartym 2-letnim okresie i będzie to jego normalna praca, a nie awaria.

## M3 — zgodność danych (ostatnie 720 dni, sygnał porównany po 200 barach rozgrzewki)

- Kraken XBT/GBP vs Binance BTCUSDT / DEXUSUK: korelacja dziennych zwrotów 0,9920,
  mediana różnicy zamknięcia 11,3 bps, **sygnał zgodny 99,6%** dni (520).
- Kraken XBT/USD vs Binance BTCUSDT: korelacja 0,9998, różnica 4,2 bps, **sygnał
  zgodny 99,8%**.

Backtest na historii BTCUSDT przeliczonej na GBP dobrze opisuje to, co bot zobaczy
na Krakenie. Osobna paczka danych Krakena nie jest potrzebna.

## M4 — książka XBT/GBP na żywo (5 odczytów co minutę, 2026-10-30)

- Spread: 0,02–0,96 bps.
- Koszt kupna względem ceny środkowej: £100 → 0,01–0,48 bps (mediana **0,17 bps**);
  £1 000 bez zmian.

Przy tych kwotach płynność nie gra roli. Koszt to prawie wyłącznie prowizja.

## Czego projekt nie przewidział (zapisane, reguła nierenegocjowana)

- **Rozgrzewka w M3:** projekt mówił „odsetek dni z tym samym stanem”. Pomijam
  pierwsze 200 barów każdej serii, bo EMA100 policzona na obciętych 720 dniach
  potrzebuje rozbiegu. Ustawione przed uruchomieniem, w kodzie (`WARMUP = 200`).
- **Kurs FX:** ostatnia obserwacja DEXUSUK to 2026-10-23, ostatni tydzień M3 jest
  wypełniony tym kursem. Wpływ na 520 dni porównania jest pomijalny.
- **Stop F7 w B&H:** benchmark liczony bez stopu (`stop_loss_pct=None`), czyli
  zwykłe kup i trzymaj.

## Co dalej

1. Pre-rejestracja pilota, w tym warunek usera z 2026-10-30: **paper na Krakenie ma
   pokazać zarobek, zanim wejdą prawdziwe pieniądze.**
2. Executor Krakena (spot, XBT/GBP, post-only z fallbackiem na taker do decyzji
   w projekcie pilota) i bot paper na danych Krakena: nowy zegar.
3. Wygaszenie kanałów Binance demo (4h, shadow), dopiero gdy Kraken paper działa.
