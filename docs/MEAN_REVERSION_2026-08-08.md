# „Kupuj jak spada, sprzedawaj jak rośnie" — zmierzone: NIE (2026-08-08)

> Pytanie usera: czy nie grać agresywniej, kontrariańsko, jak w systemie
> 6 warstw dostrojonym do day-tradingu — bot ma „widzieć, kiedy zmienia się
> kierunek"? Zamiast dyskutować, przepuściliśmy tę przesłankę przez młynek:
> `RsiMeanReversion` (podręcznikowe 14, 30/70, wyjście 50, ŚWIADOMIE bez
> strojenia) × {1d long-only, 1d long+short, 4h L+S, 1h L+S} w scenario_lab —
> ta sama pre-rejestrowana reguła z 2026-08-06, holdout <2026-07-16, spany
> OOS, siatka prowizji. Kontrolka `btc_1d_live` w tym samym przebiegu.

## Werdykt: wszystkie 4 warianty REJECT — i to nie jest blisko

Sharpe @ prowizja 0,2% (OOS; kontrolka EMA20/100 dla skali):

| layout | EMA20/100 (kontrolka) | RSI 1d long | RSI 1d L+S | RSI 4h L+S | RSI 1h L+S |
|---|---|---|---|---|---|
| (730, 180) | **1,00** | 0,57 | −0,18 | ~−1,2 | −1,81 |
| (500, 125) | **0,99** | 0,48 | −0,19 | ~−1,3 | −1,92 |
| (1000, 250) | **1,13** | 0,44 | −0,23 | ~−1,2 | −1,80 |
| (365, 90) | **1,01** | 0,29 | 0,36 | −1,24 | −1,96 |

- **1d long-only (kup dołek):** Sharpe 0,29–0,57 — nie bije ani EMA (≈1,0),
  ani buy&holda (0,81–1,00) w ŻADNYM layoucie. Jedyny plus: płytszy DD
  (−23…−43%), ale przy 2–8× niższym zwrotach (39–116% vs 793–1328%).
- **1d long+short (kup dołek, sprzedaj górkę):** zwroty −99…−111%,
  DD do −213% — konto wielokrotnie wyzerowane.
- **4h L+S:** −99,6% w każdym layoucie, 307 trejdów.
- **1h L+S („day trading"):** Sharpe **−1,3…−3,8**, zwrot **−100% wszędzie**,
  1200–1400 trejdów/span. Im częściej gra, tym szybciej umiera: przy 0,1%
  prowizji za stronę 1382 trejdy to ~276% kapitału oddane w samych opłatach,
  zanim strategia cokolwiek przewidzi.

## Dlaczego to było do przewidzenia (i po co mimo to zmierzyliśmy)

1. **BTC ma długoterminowy dryf w górę i trendy grubsze niż korekty.**
   Kontra-trend na takim aktywie systematycznie łapie spadające noże i
   ścina zyski wzrostów. To samo pokazał short trend-followingowy
   (2026-08-06: gorszy w 4/4 layoutach).
2. **Częstotliwość = prowizje.** Daily TSMOM na krypto przeżywa 0,1%, umiera
   >0,25% (RESEARCH_ULEPSZEN §2). Day trading mnoży liczbę opłat ×24 przy
   TEJ SAMEJ półce kosztowej. Fee drag rośnie liniowo z obrotem, edge nie.
3. **System 6 warstw niczego się nie nauczył** — audyt 2026-07-17
   (ANALIZA_6_WARSTW): etykiety cyrkularne („accuracy 0,9999" = odtwarzanie
   własnych reguł), przeciekowe splity, a jedyna uczciwa liczba: LSTM
   **AUC 0,519 = rzut monetą**. „Widzenie zmiany kierunku" było artefaktem
   pomiaru, nie umiejętnością. Werdykt D11 (retrain NOTHING) stoi.

## Uczciwa gwiazdka przy kontrolce

W tym przebiegu nawet `btc_1d_live` dostaje mechaniczny REJECT na checku DSR —
bo katastrofalne Sharpe'y RSI (−3,8…+1,1) rozdęły wariancję puli prób i
„oczekiwany najlepszy przypadkiem" skoczył do 3,06. To artefakt doboru puli
(poręcz, nie wyrocznia — zastrzeżenie wpisane w raport od początku), nie
unieważnienie werdyktu z 2026-08-06, gdzie kontrolka przeszła 4/4 na
jednorodnej puli. Checki 1–3 kontrolka przechodzi i tu (Sharpe 0,99–1,13,
bije B&H 4/4).

## Decyzja

- **Mean reversion / day trading na BTC: skreślone danymi.** Nie wracamy bez
  jakościowo nowej hipotezy (nie „a może jednak agresywniej").
- Do zamkniętej listy NIE ROBIMY dochodzą: kontra-trend RSI (każdy interwał),
  „agresywne" podnoszenie częstotliwości bez zmiany półki kosztowej.
- Bot ma grać rzadko nie dlatego, że jest „ostrożny", tylko dlatego, że
  **rzadkie granie to jedyny zmierzony sposób, w jaki cokolwiek tu zarabia**.

## Jak powtórzyć

```bash
.venv/bin/python scripts/research/scenario_lab.py \
  --only btc_1d_live --only btc_1d_rsi --only btc_1d_rsi_ls \
  --only btc_4h_rsi_ls --only btc_1h_rsi_ls
```
