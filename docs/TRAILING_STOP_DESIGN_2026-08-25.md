# Trailing stop na EMA20/100 — PROJEKT PRE-REJESTROWANY (2026-08-25)

> Pisany **przed** uruchomieniem testu. Reguła decyzyjna poniżej jest wiążąca.
> Jeśli wynik jej nie spełni, kandydat #9 zostaje odrzucony i wraca na półkę
> razem z ośmioma poprzednimi. Nie renegocjujemy reguły po zobaczeniu liczb.

## Dlaczego w ogóle wracamy do ulepszeń

Kolejka kandydatów została zamknięta 2026-08-08 (8 odrzuconych). Wracamy, bo
pojawił się **nowy typ hipotezy**, którego żaden z ośmiu nie dotykał: wszystkie
poprzednie zmieniały **wejście** (kiedy handlować) albo **wielkość** pozycji.
Ten dotyka **wyjścia**. Silnik backtestu ma `stop_loss_pct`/`take_profit_pct`
od początku i **nikt nigdy nie zmierzył ich na żywej strategii**.

## Zmierzona przesłanka (2026-08-25, dane < 2026-07-16)

Zgodnie z zasadą „najpierw zmierz przesłankę":

| | 1d | 4h |
|---|---|---|
| transakcje | 15 | 91 |
| zwycięskie | 7 (47%) | 27 (30%) |
| mediana szczytu zysku (MFE) zwycięskich | **+73,50%** | **+33,49%** |
| mediana wyjścia zwycięskich | +33,51% | +21,32% |
| **mediana oddanego zysku** | **+45,20 pp** | **+12,59 pp** |
| zwycięskie, których szczyt był >2× wyjścia | 5/7 | 9/27 |

Przesłanka **PRZECHODZI**: oddawanie zysku jest duże i systematyczne.
To pierwszy raz od 2026-08-06, kiedy pomiar przesłanki nie zabił pomysłu od razu.

## Dlaczego to mimo wszystko prawdopodobnie NIE zadziała

Uczciwie, zanim zobaczę wynik: oddawanie zysku **nie jest błędem**
trend-followingu, tylko jego kosztem wejścia. Cała przewaga siedzi w prawym
ogonie — kilka ogromnych transakcji finansuje resztę (1d: +594% netto z 15
transakcji przy 47% trafień). Każdy stop, który utnie ogon, zabija strategię,
nawet jeśli poprawi medianę. Dodatkowo każde wybicie stopem to dodatkowy
round-trip po ~24 bps.

## Projekt

- **Dane:** BTCUSDT 1d i 4h, wyłącznie `< 2026-07-16` (holdout M5 nietknięty).
- **Baseline:** EMA20/100 long-only, `fee=0.001`, `slippage=0.0002` — dokładnie
  konfiguracja żywa. Zero zmian w koszcie.
- **Kandydat A — trailing ATR:** stop `k × ATR(14)` pod biegnącym szczytem ceny,
  `k ∈ {2, 3, 4, 5, 6, 8}`.
- **Kandydat B — trailing procentowy:** stop `p%` pod biegnącym szczytem,
  `p ∈ {10, 15, 20, 25, 30, 40}`.
- **Semantyka identyczna z silnikiem produkcyjnym:** sygnał wykonywany na
  otwarciu NASTĘPNEGO bara, stop sprawdzany śródbarowo po `low`, poślizg
  adwersyjny przez `entry_fill_price`/`exit_fill_price`, prowizja przez
  `apply_fee`, po wybiciu stopem blokada ponownego wejścia w tę samą stronę
  aż sygnał się wypłaszczy (`blocked_side`). Te same funkcje z `costs.py`.

## Metryka i REGUŁA DECYZYJNA (wiążąca)

- **Pierwotna:** Sharpe zannualizowany. **Wtórne:** max drawdown, zwrot całkowity,
  liczba transakcji. Nie „accuracy" i nie mediana transakcji.
- **AKCEPTUJEMY tylko jeśli spełnione OBA:**
  1. kandydat bije Sharpe baseline'u **na obu horyzontach** (1d i 4h), oraz
  2. robi to na **spójnym pasmie ≥3 sąsiednich wartości** parametru — nie na
     jednej szczęśliwej. To jest bezpiecznik przed przeszukaniem siatki.
- W każdym innym wypadku: **REJECT**, z pełną siatką w wynikach (bez wycinania).
- Raportujemy CAŁĄ siatkę, także gdy wypadnie źle.
