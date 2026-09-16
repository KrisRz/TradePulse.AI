# Kandydat #11 — EMA20/100 na koszyku dużych coinów — WYNIK: **REJECT**

> Projekt: `docs/PORTFOLIO_DESIGN_2026-09-16.md`, zacommitowany przed testem
> (`76df464`, 2026-09-16 19:33 UTC), SHA-256
> `520347ed24ee18d5b035ffd37bc08fd2005fdd29258778cb3ac18422d7c45fbd`; skrypt wydrukował
> tę samą sumę. Kod: `scripts/research/portfolio_study.py`. Kontrola spójności
> przeszła: część BTC × N = BTC-EMA z pełnym kapitałem (rtol 1e-9).

## Werdykt

| | H1 płytszy DD o ≥5 pp wszędzie | H2 Sharpe ≥ BTC−0,10 | H3 bez dowolnego rynku | H4 > koszyk B&H |
|---|---|---|---|---|
| U8 (z SOL, DOGE) | ❌ | ✅ | ❌ | ✅ |
| U6 (bez nich) | ❌ | ✅ | ❌ | ✅ |

**REJECT.** Bilans: **11 zmierzonych, 11 odrzuconych.**

## Liczby (prowizja 0,1%; przy 0,2% różnice ≤ 0,01 Sharpe'a)

| | U8: 2020-11-19 → 2026-07-15 | | U6: 2018-08-12 → 2026-07-15 | |
|---|---|---|---|---|
| | Sharpe / maxDD | transakcje | Sharpe / maxDD | transakcje |
| **portfel EMA** | 1,08 / **−78,8%** | 95 | 0,91 / **−59,2%** | 94 |
| **BTC-EMA (żywa)** | 0,89 / **−49,7%** | 10 | 1,00 / **−49,7%** | 12 |
| BTC trzymany | 0,68 / −76,6% | — | 0,79 / −76,6% | — |
| koszyk trzymany | 0,92 / −85,8% | — | 0,80 / −73,5% | — |

Połówki (marża DD portfela wobec BTC-EMA, dodatnia = lepiej): U8 **−28,8** i **−10,1 pp**;
U6 **−8,8** i **−4,2 pp**. Portfel ma głębszy drawdown w **każdej** połówce obu uniwersów.

Pojedyncze części (Sharpe / maxDD, U8): BTC 0,89/−50%, ETH 0,84/−63%,
BNB 1,02/−72%, XRP 0,48/−82%, LTC 0,31/−85%, ADA 1,06/−64%, DOGE 0,79/**−93%**,
SOL 1,38/−69%.

## Dlaczego przesłanka zawiodła

- **Ta sama reguła na altach ma dużo głębsze spadki niż na BTC** (−63…−93% wobec −50%).
  Najprostsze wyjaśnienie (niezmierzone osobno): filtr trendu wychodzi z rynku
  dopiero po potwierdzeniu, a alty zdążą przez ten czas spaść mocniej.
  Dywersyfikacja z rynkami, które same mają gorsze drawdowny i spadają razem
  z BTC, nie spłaca się.
- **Brak rebalansowania koncentruje ryzyko.** Część, która urosła najbardziej
  (DOGE w 2021), staje się większością portfela i ciągnie go w dół przy krachu.
  Zmierzone: w szczycie portfela (2021-05-07) część DOGE to **77%** jego wartości.
  Portfel U8 bez DOGE ma −55,3% zamiast −78,8%. H3 istniało właśnie po to, żeby
  złapać taki efekt jednego rynku.
- Wynik literatury (Zarattini i in.: niższy DD) opierał się na wielkości pozycji wg
  zmienności i rebalansie z progiem 20%. To inna konstrukcja niż „ten sam bot na
  kilku rynkach”. Tamten wariant byłby kandydatem z nowymi parametrami, a nie tym.

## Co z tego zostaje

- Wyższy Sharpe U8 (1,08) to efekt spanu 2020–2021 i dwóch rynków wybranych dziś
  z wiedzą o ich rajdach. W U6, bez tej wiedzy i z bessą 2018, Sharpe wynosi 0,91,
  czyli poniżej BTC (1,00).
- **Samo BTC jest najlepszym rynkiem dla tej reguły** z tych, które mamy. Żywa
  konfiguracja się broni.
- Kolejna „dywersyfikacja” miałaby sens tylko z rynkami, które naprawdę nie spadają
  razem z kryptowalutami (inna klasa aktywów). Tego Binance spot nie oferuje.
