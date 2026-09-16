# Kandydat #10 — histereza na przecięciu EMA20/100 (4h) — WYNIK: **REJECT**

> Projekt: `docs/HYSTERESIS_DESIGN_2026-09-16.md`, zacommitowany przed testem
> (`2074f03`, 2026-09-16 19:46 +0100), SHA-256
> `4df01cc86e3d1c4696f2327ea980ca30bf5ab5a51d57f909bcb615e4137521d9`. Skrypt
> wydrukował tę samą sumę przy starcie. Kod: `scripts/research/hysteresis_study.py`.
> Reprodukcja: `PYTHONPATH=. .venv/bin/python scripts/research/hysteresis_study.py`.

## Werdykt

| warunek | wynik |
|---|---|
| kontrola `b = 0` ≡ `EmaCrossover(20,100)` | ✅ identyczne (`==`) na 16 513 barach 4h i 3 240 barach 1d |
| **R1** — ciąg ≥3 pasm bijących bazę w ≥3/4 układów przy 0,1% **i** 0,2% | ❌ **żadne pasmo nie spełnia** |
| R2 — więcej wygranych z B&H przy 0,3% niż baza | ❌ niespełnialne (patrz niżej); nieoceniane, bo brak ciągu z R1 |
| R3 — nie jeden rok | nieoceniane (brak ciągu z R1) |
| R4 — DSR najlepszej komórki ≥ 0,95 (N = 16) | ✅ 0,998 — ale to słaby filtr (niżej) |

**REJECT.** Bilans: **10 zmierzonych, 10 odrzuconych.**

## Co mówią liczby (Sharpe, ciągłe spany OOS, BTC 4h, < 2026-07-16)

Liczba układów (z 4), w których kandydat bije bazę, przy prowizji 0,1% / 0,2% / 0,3%:

| b | 0,1% | 0,2% | 0,3% |
|---|---|---|---|
| 0,25% | 0 | 0 | 0 |
| 0,50% | 0 | 0 | 0 |
| 0,75% | 1 | 4 | 4 |
| 1,00% | 0 | 2 | 4 |
| 1,50% | 0 | 0 | 0 |
| 2,00% | 1 | 4 | 4 |

Przy prowizji 0,1% (taką płaci konto):

| | 730/180 | 500/125 | 1000/250 | 365/90 |
|---|---|---|---|---|
| buy & hold | 0,86 | 0,92 | 0,75 | 0,93 |
| **baza EMA20/100** | **1,06** (89 tr.) | **1,14** (90) | **0,91** (89) | **1,13** (91) |
| b = 0,75% | 1,05 (63) | 1,13 (64) | 0,91 (63) | 1,14 (64) |
| b = 2,00% | 1,03 (40) | 1,12 (40) | 0,91 (39) | 1,13 (40) |

Pełna siatka (trzy prowizje, max DD, liczba transakcji) jest w wyjściu skryptu.

**Odczyt:**
- Pasmo **ścina liczbę transakcji o 11–56%** (89 → 79 … 40) i przy 0,1% nie daje
  w zamian nic. Oszczędność na wyciętych whipsawach zjadają spóźnione wejścia
  i wyjścia. To ta sama lekcja co przy stopie kroczącym (#9): przesłanka była prawdziwa (krótkie transakcje = 40% strat), ale efektu nie da się zebrać.
- Wygrana przy 0,2–0,3% to czysta oszczędność na prowizji. Konto płaci 0,1%, więc
  żywego kanału to nie dotyczy.
- Wąskie pasma (0,25–0,50%) i 1,50% są gorsze od bazy wszędzie. Brak monotonii
  (0,75% lepsze niż 0,50%, a 1,50% gorsze niż 1,00% i 2,00%) to szum, a nie zależność.

**Diagnostyka 1d (poza werdyktem):** pasmo ≥0,50% psuje 3 z 4 układów (Sharpe
0,79–0,93 wobec 0,96–1,07) i **pogłębia** drawdown (−61…−69% wobec −50%). Wyjątkiem
jest układ 1000/250 (1,16–1,20 wobec 1,14–1,16); przyczyny nie badałem.

## Dwie rzeczy, których projekt nie przewidział (zapisane, nie renegocjowane)

1. **R2 był niespełnialny.** Projekt zakładał, zgodnie z notatką z 2026-08-06, że
   baza 4h przy 0,3% nie bije buy & hold w żadnym układzie. W **ciągłym** pomiarze
   baza bije go w **4/4** układach także przy 0,3% (0,94 / 1,02 / 0,79 / 1,01 wobec
   0,86 / 0,92 / 0,75 / 0,93). Kandydat nie mógł mieć „więcej niż 4”.
   Werdykt i tak rozstrzygnął R1, więc to nie zmienia wyniku. **Sprostowanie do
   notatki z 06.08:** „4h: 0/4 przy 0,3%” pochodziło ze sklejania foldów, czyli
   z artefaktu MEDIUM-3. Przy ciągłym przebiegu kanał 4h ma jeszcze zapas przy
   prowizji 0,3% (najmniejszy w układzie 1000/250: 0,79 wobec 0,75).
2. **R4 nie filtruje.** Wariancja Sharpe'a w siatce sześciu mocno skorelowanych pasm
   jest mikroskopijna (4,9e-7 na bar), więc oczekiwane maksimum „z przypadku” też
   jest mikroskopijne i DSR wychodzi 0,998. Scenario lab trafił na to samo
   2026-08-06. Na przyszłość deflację liczyć raczej testem SPA (`arch`) na pełnych
   szeregach niż wariancją z siatki.

Do tego cztery „układy” na 4h to niemal ta sama próbka (spany zaczynają się
w barach 365–1000 z 16 513). Warunek „3 z 4” jest więc słabszy, niż wygląda. Tym
bardziej wymowny jest wynik 0–1 z 4 przy 0,1%.

## Konsekwencje

- Żywy kanał 4h zostaje bez zmian. Bot 1d (M5) nietknięty.
- **Whipsawów nie da się „wyciąć” progiem przecięcia** przy prowizji 0,1%. Kolejny
  kandydat z tej rodziny (potwierdzenie N barów, cooldown po wyjściu) musiałby mieć
  inny mechanizm niż opóźnienie, bo opóźnienie właśnie zostało zmierzone.
- Następny w kolejce: #11 (portfel 8 majorsów, cel = płytszy DD), dopiero po
  osobnej pre-rejestracji.
