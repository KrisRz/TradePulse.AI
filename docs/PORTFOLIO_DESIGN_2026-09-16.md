# Kandydat #11 — ta sama reguła na koszyku dużych coinów — PROJEKT PRE-REJESTROWANY (2026-09-16)

> Pisany **przed** testem. Reguła decyzyjna niżej jest wiążąca i nie będzie
> renegocjowana. Żadna liczba portfela nie była liczona przed spisaniem tego
> dokumentu.

## Po co

Dziesięciu kandydatów próbowało zrobić **lepsze transakcje** z jednej reguły na
jednym rynku i wszyscy przegrali. Ten kandydat nie zmienia ani jednej transakcji.
Zmienia **liczbę niezależnych zakładów**: EMA20/100 long/flat, identyczna jak na
żywo, prowadzona osobno na kilku dużych coinach, każdy z własną częścią kapitału.

Po co to botowi, w kolejności ważności:
1. **Płytszy drawdown.** Cel z gwiazdy polarnej to „nie tracić”; na BTC sam bot
   miał historycznie −50%.
2. **Więcej transakcji rocznie** (8 × ~1,7). Przy jednym rynku bramka B czeka latami
   na garść zamkniętych transakcji.
3. Sharpe **nie jest** celem. Literatura mówi, że szerokość obniża DD, a Sharpe'a nie
   podnosi, i tego się spodziewamy.

## Przesłanka (zmierzona przez research 2026-09-16, bez liczenia portfela)

Średnia korelacja par dziennych zwrotów 8 coinów: **0,54** (od 2021) i **0,64**
(od 2023), czyli efektywnie ~1,5–1,7 niezależnego zakładu, a nie 8. Zysk
z dywersyfikacji istnieje, ale jest ograniczony. Krachy krypto są zsynchronizowane,
a filtr trendu wychodzi ze wszystkich rynków mniej więcej naraz.

Źródła: Zarattini, Pagani i Barbon 2025 (in-sample, 20 coinów: Sharpe 1,57 przy
MDD 11% wobec BTC 1,56 przy 19%); Man AHL („In crypto we trend”: korelacja par ~0,6,
optimum 10–15 coinów).

**Prior:** średni dla DD, niski dla „bez straty Sharpe'a”.

## Projekt

- **Reguła na każdym rynku:** `EmaCrossover(20, 100, allow_short=False)`,
  `engine.run_backtest`, prowizja + `slippage = 0,0002`. Zero nowych parametrów.
- **Kapitał:** równe części na starcie, **bez rebalansowania** (każda część żyje
  własnym życiem, jak osobny bot). Portfel = suma krzywych kapitału części.
- **Dwa uniwersa, oba muszą przejść:**
  - **U8** = BTC, ETH, BNB, XRP, LTC, ADA, DOGE, SOL (reguła z 2026-08-08: top
    kapitalizacji, bez stablecoinów, ≥5 lat notowań). Wspólny start = pierwszy bar
    SOL + 100 barów rozgrzewki.
  - **U6** = U8 bez SOL i DOGE. Obu mogę dziś wybierać z wiedzą o ich późniejszych
    rajdach, więc U6 jest kontrolą przeciwko tej wiedzy. Wspólny start = pierwszy
    bar ADA + 100 barów rozgrzewki (dłuższa historia, obejmuje bessę 2018).
- **Dane:** `data/ml/historical/*_1d.csv`, wyłącznie `< 2026-07-16`.
- **Punkt odniesienia (ten sam span, ta sama prowizja):**
  - **BTC-EMA** = żywa strategia z całym kapitałem na BTC;
  - buy & hold BTC;
  - **koszyk B&H** = równe części, kup i trzymaj, bez rebalansowania.
- **Prowizje:** 0,1% i 0,2% na stronę.
- **Połówki:** span dzielony w połowie dat kalendarzowych. Drawdown połówki liczony
  od szczytu wewnątrz tej połówki.
- **Metryki:** Sharpe (dzienny, √365), max drawdown, zwrot, liczba transakcji,
  najdłuższy drawdown w dniach.

## REGUŁA DECYZYJNA (wiążąca)

**AKCEPTUJEMY wyłącznie, gdy spełnione są WSZYSTKIE warunki, dla OBU uniwersów:**

- **H1 — płytszy drawdown, wszędzie.** Max DD portfela jest płytszy od max DD
  BTC-EMA o **≥ 5 pp** na całym spanie **i** w każdej z dwóch połówek, przy prowizji
  0,1% **i** 0,2%.
- **H2 — bez dużej ofiary.** Sharpe portfela ≥ Sharpe BTC-EMA **− 0,10** na całym
  spanie, przy obu prowizjach.
- **H3 — nie jeden rynek.** Przy prowizji 0,1% portfel **bez dowolnego jednego**
  rynku (każdy wariant z osobna) nadal spełnia warunek DD z H1 na całym spanie.
- **H4 — to nie jest po prostu trzymanie altów.** Sharpe portfela > Sharpe koszyka
  B&H na całym spanie, przy prowizji 0,1%.

W każdym innym wypadku: **REJECT**, z pełną tabelą.

## Co oznacza wynik

- **REJECT:** nic się nie zmienia; bilans 11/11.
- **ACCEPT:** żywe kanały się **nie zmieniają**. Portfel może dostać własny,
  osobno pre-rejestrowany kanał papierowy (np. na koncie demo), o czym decyduje
  user. Warunek praktyczny, zapisany z góry: Binance wymaga min. 5 USDT na
  zlecenie. Żeby część po spadku o 70% wciąż mogła złożyć zlecenie, musi startować
  z ≥ ~17 USDT, czyli ≥ ~140 USDT na cały koszyk U8.

## Budżet prób

Próba **#11** w życiu projektu; dwa uniwersa i dwie prowizje to jedna hipoteza
sprawdzana wszędzie, a nie wybór najlepszej komórki.

## Implementacja

`scripts/research/portfolio_study.py`, wynik w
`docs/PORTFOLIO_RESULTS_2026-09-16.md`.
