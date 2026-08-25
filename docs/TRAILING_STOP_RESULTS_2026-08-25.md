# Trailing stop — WYNIK: REJECT (kandydat #9)

> Projekt i reguła decyzyjna: `docs/TRAILING_STOP_DESIGN_2026-08-25.md`,
> zapisane **przed** uruchomieniem. Reguła zastosowana mechanicznie, bez
> renegocjacji. Kod: `scripts/research/trailing_stop_study.py`.

## Wiarygodność liczb

Pętla symulacji jest **lustrem silnika produkcyjnego** — nie przybliżeniem.
`--verify-baseline` porównuje ją z `run_backtest` przy wyłączonym trailingu i
wymaga **identyczności `==` na floatach**, nie tolerancji:

```
1d: trades 15 vs 15 | identical net returns: True
4h: trades 91 vs 91 | identical net returns: True
VERDICT: identical
```

Pierwsze uruchomienie **wykryło rozbieżność** (4h: 90 vs 91) — brakowało
domknięcia otwartej pozycji na końcu danych. Naprawione, dopiero potem test.

## Pełna siatka (BTCUSDT, dane < 2026-07-16, EMA20/100 long-only)

### 1d — baseline Sharpe 0,710 · maxDD −64,3% · total +594,1%

| wariant | Sharpe | maxDD | total | stopy |
|---|---|---|---|---|
| 2×ATR14 | −0,105 | −36,2% | −14,6% | 15/15 |
| 3×ATR14 | −0,174 | −52,0% | −30,2% | 14/15 |
| 4×ATR14 | 0,306 | −56,1% | +48,1% | 13/15 |
| 5×ATR14 | 0,213 | −63,5% | +14,8% | 12/15 |
| 6×ATR14 | 0,373 | −59,9% | +85,0% | 11/15 |
| 8×ATR14 | **0,747** | −64,3% | +700,4% | 2/15 |
| 10% | −0,154 | −26,1% | −19,1% | 15/15 |
| 15% | 0,377 | −34,1% | +67,9% | 13/15 |
| 20% | 0,476 | −43,3% | +130,6% | 10/15 |
| 25% | **0,907** | −43,5% | +881,2% | 7/15 |
| 30% | **0,864** | −46,2% | +836,9% | 5/15 |
| 40% | **0,819** | −53,9% | +888,6% | 3/15 |

### 4h — baseline Sharpe 1,138 · maxDD −55,5% · total +1752,1%

| wariant | Sharpe | maxDD | total | stopy |
|---|---|---|---|---|
| 2×ATR14 | −0,782 | −49,8% | −45,1% | 89/91 |
| 3×ATR14 | −0,199 | −44,3% | −27,4% | 83/91 |
| 4×ATR14 | 0,520 | −39,7% | +103,9% | 77/91 |
| 5×ATR14 | 0,942 | −53,5% | +580,0% | 68/91 |
| 6×ATR14 | 0,912 | −55,9% | +653,0% | 57/91 |
| 8×ATR14 | 0,965 | −55,5% | +889,9% | 15/91 |
| 10% | 0,832 | −46,7% | +365,5% | 42/91 |
| 15% | **1,142** | −57,9% | +1467,9% | 18/91 |
| 20% | **1,179** | −59,6% | +1788,5% | 5/91 |
| 25% | **1,165** | −55,5% | +1768,2% | 2/91 |
| 30% | 1,127 | −55,5% | +1639,3% | 1/91 |
| 40% | 1,138 | −55,5% | +1752,1% | 0/91 |

## Werdykt reguły

```
ATR: bije na 1d w [8.0] · na 4h w niczym       -> wspólne pasmo 0
pct: bije na 1d w [25%, 30%, 40%]
     bije na 4h w [15%, 20%, 25%]
     bije na OBU w [25%] -> najdłuższe spójne pasmo = 1  (wymagane >=3)
VERDICT: REJECT
```

Bezpiecznik zadziałał dokładnie tak, jak był zaprojektowany. Pasma na obu
horyzontach **idą w przeciwne strony** — na 1d ciaśniej niż 25% szkodzi, na 4h
luźniej niż 25% nic nie robi. Stykają się w jednym punkcie. To sygnatura dwóch
różnych optimów, które przypadkiem się dotknęły, a nie wspólnego efektu.

## REJECT także w treści (diagnostyka koncentracji)

Ta sama diagnostyka, która obaliła meta-labelera — czy „poprawa" stoi na kilku
zdarzeniach:

**1d @ 25%** (Sharpe +0,197): suma wszystkich różnic per-transakcja **+4,30%**,
a pojedyncza największa **−58,88%** = **1368%** tej sumy. Poszczególne efekty są
o rząd wielkości większe niż wynik zbiorczy i wzajemnie się znoszą. Największy
pojedynczy efekt jest **ujemny** (stop 2020-05-02 ucina wejście w hossę
2020–21). To szum, który się skasował, a nie przewaga.

**4h @ 20%** (Sharpe +0,041): suma różnic +10,38%, największa pojedyncza
**+11,56%** = **111%** całości. Jedna transakcja (2020-12-13) odpowiada za
więcej niż cała „poprawa" — bez niej kandydat jest na minusie. 5 stopów na 91
transakcji.

## Czego się nauczyliśmy (poza odrzuceniem)

1. **Moja własna przesłanka projektowa była błędna w jednym punkcie.** Pisałem,
   że każdy stop dokłada round-trip po ~24 bps. Nieprawda: liczba transakcji
   jest **stała** (15 i 91) we wszystkich wariantach, bo blokada ponownego
   wejścia (`blocked_side`) zamienia stop w *inne wyjście* z tej samej
   transakcji, a nie w dodatkową. Koszt whipsawu tu nie występuje.
2. **Ciasne stopy trailingowe niszczą strategię** — 2×ATR wybija 89/91
   transakcji i daje Sharpe −0,78. Prawy ogon to cała przewaga.
3. **Oddawanie zysku jest realne i duże** (zwycięskie 1d szczytują +73,5%,
   wychodzą +33,5%), ale **nie da się go odzyskać stopem**. Przesłanka
   przeszła, kandydat i tak padł. To pierwszy raz, kiedy te dwie rzeczy się
   rozjechały — warto pamiętać, że dobra przesłanka nie jest obietnicą.

## Kontrola przy okazji: F7 jest zdrowe

Skoro stopy w okolicy 10% bywają zabójcze, sprawdziłem żywy F7
(**stały** stop 10% od wejścia, nie trailingowy):

| | Sharpe | maxDD | total | stopy |
|---|---|---|---|---|
| 1d bez stopu | 0,710 | −64,3% | +594,1% | 0/15 |
| **1d + F7 10%** | **0,895** | **−46,8%** | +1194,5% | 7/15 |
| 4h bez stopu | 1,138 | −55,5% | +1752,1% | 0/91 |
| **4h + F7 10%** | **1,097** | −57,3% | +1501,4% | 6/91 |

Na 1d F7 **wyraźnie pomaga** (Sharpe +0,185, drawdown płytszy o 17,5 pp).
Na 4h kosztuje 0,04 Sharpe'a — tania składka za urządzenie bezpieczeństwa.
Żadnej akcji. Kluczowa różnica wobec kandydata: stop **od wejścia** ryzykuje
tylko świeżą pozycję, stop **od szczytu** wchodzi w drogę wygrywającemu
trendowi.

## Status

Kandydat **#9 odparty**. Bilans: 9 zmierzonych, 9 odrzuconych.
Reguła powrotu bez zmian: ~2× zdarzeń albo cecha z nowej hipotezy.
