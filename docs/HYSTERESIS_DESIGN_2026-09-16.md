# Kandydat #10 — histereza na przecięciu EMA20/100, kanał 4h — PROJEKT PRE-REJESTROWANY (2026-09-16)

> Pisany **przed** uruchomieniem testu. Reguła decyzyjna niżej jest wiążąca. Jeśli
> wynik jej nie spełni, kandydat #10 zostaje odrzucony. Reguły nie renegocjujemy po
> zobaczeniu liczb. Żadna liczba kandydata nie była liczona przed spisaniem tego
> dokumentu. Policzona była wyłącznie przesłanka (niżej).

## Dlaczego wracamy do kolejki

Reguła powrotu z 2026-08-08: wracamy tylko przy **nowym typie hipotezy**. Każdy z
dziewięciu odrzuconych kandydatów zmieniał szybkość sygnału (ensemble), filtrował go
czymś zewnętrznym (reżim, meta-labeler), zmieniał wielkość pozycji albo wyjście (stop
kroczący). Żaden nie zmieniał **progu przełączenia samego przecięcia**. Histereza nie
dotyka ani szybkości średnich, ani danych spoza ceny. Zmienia wyłącznie to, jak blisko
zera różnica EMA może się wahać, zanim bot zmieni zdanie.

Bezpośredni powód: kanał 4h zapłacił 14→15.09.2026 za whipsaw (−2,7% w 24 h).
Pojedyncze zdarzenie nie jest dowodem, dlatego najpierw zmierzono przesłankę na historii.

## Zmierzona przesłanka (2026-09-16, dane < 2026-07-16, silnik produkcyjny, bez F7)

| | 4h | 1d |
|---|---|---|
| transakcje | 91 | 15 |
| win rate | 30% | 47% |
| transakcje ≤ 1 dnia (≤6 barów 4h / ≤5 barów 1d) | 8, **0 zwycięskich**, średnio −3,97% | 2, 0 zwycięskich |
| transakcje ≤ 4 dni (≤24 bary 4h) | 25 z 91, **40% sumy strat** (log) | — |
| 3 największe transakcje | +1,70 z +2,92 log (**58%** wyniku) | +2,69 z +1,94 |

Przesłanka **PRZECHODZI**: krótkie transakcje to czysty koszt i jest go dużo.

**Dlaczego to mimo to prawdopodobnie nie zadziała** (uczciwie, przed wynikiem):
- Pasmo opóźnia **każde** wejście, także w te trzy transakcje, które niosą 58%
  wyniku. Kandydat #9 padł dokładnie na tym: przesłanka była prawdziwa, a efektu
  nie dało się zebrać.
- Pasmo opóźnia też wyjście, więc oddaje część zysku na końcu trendu.
- Przy 91 transakcjach w 7,5 roku poprawa może wisieć na kilku zdarzeniach.

Prior: **niski do średniego.**

## Projekt

- **Dane:** `data/ml/historical/BTCUSDT_4h.csv`, wyłącznie `< 2026-07-16`.
  Kanał 1d **nie jest** oceniany (15 transakcji, żywy kanał M5 zamrożony);
  raportowany wyłącznie jako diagnostyka.
- **Sygnał kandydata (dokładnie):** `gap_t = (EMA20_t − EMA100_t) / EMA100_t`,
  liczone funkcją `indicators.ema` tak jak `EmaCrossover`. Stan:
  `s_t = 1` gdy `gap_t > b`; `s_t = 0` gdy `gap_t < −b`; w przeciwnym razie
  `s_t = s_{t−1}`; `s = 0` przed rozgrzewką (pierwsze 100 barów zerowane jak w
  `Strategy.target_positions`).
- **Kontrola poprawności:** przy `b = 0` seria celów kandydata musi być **identyczna**
  (`==`) z `EmaCrossover(20, 100, allow_short=False).target_positions`. Bez tego nie
  ma testu.
- **Siatka (jedyna, z góry):** `b ∈ {0,25%, 0,50%, 0,75%, 1,00%, 1,50%, 2,00%}`.
- **Wykonanie:** `engine.run_backtest` bez zmian (sygnał na close, fill na open
  następnego bara, `slippage = 0,0002`, long-only, bez stopu). Baseline = ten sam
  silnik z `EmaCrossover(20, 100)`.
- **Okna OOS:** cztery układy `(730,180) (500,125) (1000,250) (365,90)` wyznaczają
  **początek** spanu OOS (pierwszy bar testowy) i jego koniec (ostatni bar ostatniego
  folda). Każdy span liczony jest **jednym ciągłym przebiegiem** z indykatorami
  rozgrzanymi historią sprzed spanu. Parametry są stałe, więc sklejanie foldów nie
  byłoby niczym więcej niż artefaktem (audyt 2026-09-04, MEDIUM-3).
- **Prowizje:** `{0,1%, 0,2%, 0,3%}` na stronę.
- **Buy & hold:** ten sam span, ten sam silnik, cel = 1 (definicja z kosztami).
- **Metryka pierwotna:** Sharpe zannualizowany (`metrics.compute_metrics`).
  Wtórne: max drawdown, zwrot, liczba transakcji. Nie win rate.

## REGUŁA DECYZYJNA (wiążąca)

**AKCEPTUJEMY wyłącznie, gdy spełnione są WSZYSTKIE cztery warunki:**

- **R1 — przewaga nad bazą na pasmie, nie w punkcie.** Istnieje ciąg **≥3 sąsiednich**
  wartości `b` z siatki, dla których Sharpe kandydata jest **ściśle wyższy** niż
  Sharpe bazy w **≥3 z 4** układów, osobno przy prowizji 0,1% **i** przy 0,2%.
- **R2 — powód istnienia: odporność na koszt.** Dla każdego `b` z tego ciągu, przy
  prowizji 0,3%, kandydat bije buy & hold w **większej** liczbie układów niż baza
  (baza w tym samym przebiegu, zmierzona w tym samym skrypcie).
- **R3 — nie jedno zdarzenie.** Dla środkowej wartości ciągu (przy parzystej długości
  bierzemy niższą z dwóch środkowych), układu (365,90) i prowizji 0,1%:
  `D_y = log(1 + zwrot kandydata w roku y) − log(1 + zwrot bazy w roku y)` dla lat
  kalendarzowych spanu. Wymagane: `Σ D_y > 0` **oraz** suma po usunięciu roku
  z największym `D_y` **nadal > 0**.
- **R4 — wielokrotne testowanie.** DSR (Bailey i López de Prado, 2014) najlepszej komórki
  (prowizja 0,1%, układ (365,90)) wobec oczekiwanego maksimum z **N = 16** prób
  (10 dotychczasowych + 6 wartości siatki), z wariancją Sharpe'a wziętą z tej siatki
  w tym samym układzie, wynosi **≥ 0,95**.

W każdym innym wypadku: **REJECT**, z pełną siatką w wynikach (także gdy wypadnie źle).

## Co oznacza wynik

- **REJECT:** nic się nie zmienia. Bilans: 10 zmierzonych, 10 odrzuconych.
- **ACCEPT:** żywy kanał 4h **się nie zmienia** w trakcie zbierania bramki C.
  Kandydat dostaje własny, osobno pre-rejestrowany okres papierowy (osobny kanał
  albo kanał 4h po zamknięciu bramki C). Decyzja o tym należy do usera. Bot 1d (M5)
  pozostaje nietknięty w każdym przypadku.

## Budżet prób

To jest próba **#10** w życiu projektu (licznik: 9 kandydatów + ten) i sześć komórek
siatki w jej obrębie. Do DSR idzie `N = 16`.

## Implementacja

`scripts/research/hysteresis_study.py` — wynik zapisany do
`docs/HYSTERESIS_RESULTS_2026-09-16.md` razem z sumą kontrolną SHA-256 tego pliku,
policzoną przed uruchomieniem.
