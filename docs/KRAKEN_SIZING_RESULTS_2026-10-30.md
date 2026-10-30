# Jak bot trzyma `w` konta — WYNIKI (2026-10-30)

Projekt: `docs/KRAKEN_SIZING_DESIGN_2026-10-30.md` (commit `f10455a` przed pomiarem,
SHA-256 `0d83926f…4103f0`, wydrukowany przez skrypt).
Skrypt: `PYTHONPATH=. .venv/bin/python scripts/research/kraken_sizing_study.py --cache <dir>`.
Dane: GBP 1d od 2018-01-01 do 2026-07-15 (3118 dni, 16 transakcji), opłata 0,80%,
konto £200, gotówka 0%.

## Werdykt: **`w = 0,5` z pasmem wyrównywania `b = 0,15`**

Reguła wyboru: żaden wariant rodziny A nie przechodzi, więc wybieram najszersze
pasmo rodziny B, które przechodzi.

| Wariant | maxDD | CAGR | okna 365 d DD ≤ 25% | okna 730 d DD ≤ 25% | wyrównania/rok | koszt/rok | R2 |
|---|---|---|---|---|---|---|---|
| A `w=0,5` | −40,7% | +20,0% | 75% | 49% | 0 | 0 | FAIL |
| A `w=0,4` | −38,0% | +16,8% | 79% | 49% | 0 | 0 | FAIL |
| A `w=0,3` | −34,3% | +13,2% | 87% | 70% | 0 | 0 | FAIL |
| B `b=0,05` | −27,2% | +17,9% | 92% | 76% | 3,0 | 0,14% | PASS |
| B `b=0,10` | −27,0% | +19,4% | 92% | 76% | 1,2 | 0,10% | PASS |
| **B `b=0,15`** | **−26,7%** | **+19,7%** | **94%** | **78%** | **0,6** | **0,07%** | **PASS** |

## Co z tego wynika

- **Samo „połowa konta przy wejściu” nie wystarcza**, nawet przy `w = 0,3`. Po
  długim rajdzie udział BTC rośnie do ~0,9, a krach w tej samej pozycji uderza
  w prawie całe konto.
- **Rzadkie wyrównywanie w zupełności wystarcza.** Kiedy udział BTC wyjdzie poza
  0,35–0,65, bot sprzedaje albo dokupuje do 0,5. Zdarza się to średnio 0,6 razy
  w roku i kosztuje 0,07% rocznie. Wynik jest praktycznie równy wyidealizowanemu
  M2 (codzienne wyrównywanie bez kosztów: −26,7%, 93% / 76%).
- **Najgorszy przypadek (−26,7%) nadal przekracza 25%**, więc kill-switch konta
  zostaje, tak jak w pre-rejestracji pilota.

## Konsekwencja dla kodu

Księga i silnik dotąd znały tylko pozycję 0 albo 1. Pilot potrzebuje:
1. udziału `w` przy wejściu;
2. transakcji wyrównującej w trakcie pozycji (sprzedaż albo dokupienie części),
   z minimalnym zleceniem £5;
3. tej samej logiki w backteście i w bocie paper: test równoważności, jak dla
   obecnej księgi.

## Dowód na implementacji (2026-10-30, po zbudowaniu księgi)

`PaperPortfolio(exposure=0.5, rebalance_band=0.15, min_rebalance=5)` przeprowadzona
przez tę samą historię GBP **tak, jak prowadzi ją bot**: decyzja i transakcja po
cenie zamknięcia, stop F7 z `position_risk` na zamknięciach, 0,80%. Skrypt:
`scripts/research/kraken_book_replay.py`.

| Wariant | maxDD | CAGR | 365 d DD ≤ 25% | 730 d DD ≤ 25% | wyrównania/rok | R2 |
|---|---|---|---|---|---|---|
| cały kapitał (dzisiejszy bot) | −48,0% | +31,4% | 22% | 0% | 0 | FAIL |
| `w=0,5` tylko przy wejściu | −40,7% | +19,3% | 75% | 49% | 0 | FAIL |
| **`w=0,5`, pasmo 0,15 (pilot)** | **−27,5%** | **+19,0%** | **93%** | **77%** | **0,6** | **PASS** |

Implementacja odtwarza wynik modelu: 93% / 77% wobec 94% / 78%, maxDD −27,5% wobec
−26,7%. Różnica bierze się z innego momentu transakcji (zamknięcie zamiast
otwarcia następnego baru) i stopu na zamknięciu zamiast na minimum dnia.

⚠️ **Gotówkowa połowa nie jest nietykalna.** Pasmo działa w obie strony: po spadku
BTC bot dokupuje z gotówki, żeby wrócić do 50%. W długim spadku robi to wielokrotnie,
a zatrzymuje go dopiero kill-switch konta (25% od szczytu). Pomiar to uwzględnia;
test: `test_a_crash_is_rebalanced_by_buying_from_the_cash_half`.

Testy: `app/backend/tests/test_portfolio_partial.py` (16), w tym zgodność z regułą
zapisaną ręcznie, bar po barze. Golden master pełnej księgi bez zmian (521 → 537
testów). Mutacje 8/8 złapane.
