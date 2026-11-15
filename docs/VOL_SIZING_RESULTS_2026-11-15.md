# Kandydat #12 — wielkość pozycji według zmienności, z pasmem — WYNIKI (2026-11-15)

Projekt: `docs/VOL_SIZING_DESIGN_2026-11-15.md` (commit `09c4968` przed pomiarem,
SHA-256 `6f3c7d18…b1c5aa`, wydrukowany przez skrypt).
Skrypt: `PYTHONPATH=. .venv/bin/python scripts/research/vol_sizing_study.py --cache <dir>`.
Dane: GBP 1d od 2018-01-01 do 2026-07-15 (3118 dni, 16 transakcji), opłata 0,80%,
konto £200, gotówka 0%.

## Werdykt: **ODRZUCONY (0 z 4 wariantów RV).** Zostaje `w = 0,5` z pasmem 0,15.

Harness przy stałym celu 0,5 odtwarza punkt odniesienia co do bitu, a punkt
odniesienia wyszedł identycznie jak 30.10 (−26,7%, +19,7%, 94% / 78%).

### Cała próba

| Wariant | maxDD | CAGR | Sharpe | 365 d DD ≤ 25% | 730 d DD ≤ 25% | korekty/rok | koszt/rok | średnie `w` |
|---|---|---|---|---|---|---|---|---|
| **punkt odniesienia** | **−26,7%** | **+19,7%** | **0,90** | **94%** | **78%** | **0,6** | **0,07%** | 0,50 |
| RV20, `b=0,10` | −28,1% | +18,8% | 0,89 | 93% | 73% | 5,9 | 0,58% | 0,569 |
| kontrola `w=0,569` | −29,4% | +22,1% | 0,94 | 80% | 50% | 1,3 | 0,11% | |
| RV20, `b=0,15` | −29,6% | +19,5% | 0,90 | 93% | 76% | 2,8 | 0,42% | 0,569 |
| kontrola `w=0,569` | −32,8% | +21,3% | 0,88 | 80% | 49% | 0,5 | 0,05% | |
| RV60, `b=0,10` | −27,5% | +20,7% | 0,93 | 86% | 53% | 2,6 | 0,21% | 0,575 |
| kontrola `w=0,575` | −29,1% | +22,5% | 0,94 | 80% | 50% | 1,3 | 0,11% | |
| RV60, `b=0,15` | −26,8% | +20,8% | 0,93 | 95% | 80% | 2,0 | 0,23% | 0,575 |
| kontrola `w=0,575` | −33,1% | +21,5% | 0,88 | 79% | 49% | 0,5 | 0,05% | |

Reguła, wariant po wariancie:

| Wariant | 1 spadki (≥ 2 pp płycej) | 2 Sharpe | 3 lepszy niż kontrola | 4 połowy | Wynik |
|---|---|---|---|---|---|
| RV20 `b=0,10` | nie (głębiej o 1,4 pp) | tak | nie (CAGR −3,3 pp) | nie | FAIL |
| RV20 `b=0,15` | nie (głębiej o 2,9 pp) | tak | nie (CAGR −1,8 pp) | nie | FAIL |
| RV60 `b=0,10` | nie (głębiej o 0,8 pp) | tak | nie (CAGR −1,8 pp) | nie | FAIL |
| RV60 `b=0,15` | nie (głębiej o 0,1 pp) | tak | nie (CAGR −0,7 pp) | nie | FAIL |

maxDD w połowach (2018–2021 / 2022–2026): punkt odniesienia −26,7% / −17,2%;
kandydaci −26,8…−29,6% / −18,3…−19,8%. Żaden wariant nie jest płytszy w żadnej połowie.

### Okres wspólny z DVOL (2021-05-23 → 2026-07-15, 1880 dni)

| Wariant | maxDD | CAGR | Sharpe | korekty/rok | koszt/rok | średnie `w` |
|---|---|---|---|---|---|---|
| punkt odniesienia | −21,7% | +11,3% | 0,65 | 0,2 | 0,03% | 0,50 |
| RV20 `b=0,10` / `0,15` | −23,6% / −22,5% | +11,2% / +12,9% | 0,62 / 0,70 | 4,7 / 2,3 | 0,47% / 0,34% | 0,599 |
| RV60 `b=0,10` / `0,15` | −21,0% / −20,9% | +13,6% / +14,1% | 0,71 / 0,73 | 1,6 / 1,0 | 0,14% / 0,14% | 0,608 |
| DVOL `b=0,10` / `0,15` | −23,0% / −23,0% | +12,1% / +12,7% | 0,66 / 0,69 | 2,5 / 1,2 | 0,28% / 0,18% | 0,601 |

**DVOL odrzucony jako wejście:** maxDD głębszy niż punktu odniesienia i głębszy niż
RV60. Nie spełnia warunku 1 ani przewagi 1 pp nad najlepszym RV.

## Co z tego wynika

- **Wyczucie zmienności działa, ale za mało i za drogo.** Wobec kontroli o tej samej
  średniej ekspozycji kandydat ma spadek płytszy o 1,3–6,3 pp, czyli sygnał zmienności
  niesie informację (zgodnie z przesłanką 0,49). Kosztuje to jednak 0,7–3,3 pp CAGR
  rocznie: 2–6 korekt na rok po 0,80% zamiast 0,6.
- **Wobec dzisiejszego ustawienia nie ma żadnej poprawy.** Najlepszy wariant (RV60,
  `b=0,15`) ma praktycznie ten sam spadek (−26,8% vs −26,7%) przy 3× większym koszcie
  korekt. Przewaga +1,1 pp CAGR bierze się z większej średniej ekspozycji (0,575),
  nie ze zmienności.
- **Czego projekt nie przewidział:** średni cel wyszedł 0,57–0,61, a nie 0,5. Bot
  jest LONG głównie w trendach wzrostowych, gdy zmienność bywa niższa od mediany
  historycznej, więc skalowanie częściej podnosi ekspozycję, niż ją obniża. Kontrola
  „sama ekspozycja” wyłapała to tak, jak miała. Reguły nie renegocjuję.
- **Dlaczego stałe 0,5 z pasmem jest trudne do pobicia:** pasmo już samo sprzedaje
  po rajdzie (udział > 0,65), czyli tnie ekspozycję przed największymi krachami, bez
  estymatora i przy 0,6 transakcji rocznie.
- Przy koszcie 0,536% (post-only) wynik by się nie odwrócił: warunek 1 nie zależy od
  opłat na tyle (różnica maxDD to nie koszt, tylko cel > 0,5 w złych momentach).
  To ocena, nie pomiar; projekt liczył wyłącznie 0,80%.

## Uwaga o danych

Kurs GBP/USD: serwer FRED (`DEXUSUK`) nie odpowiadał 2026-11-15. Plik zbudowany
z tabeli H.10 Rezerwy Federalnej (`federalreserve.gov/releases/h10/hist/dat00_uk.htm`),
czyli źródła, które FRED przedrukowuje. Dowód zgodności: punkt odniesienia wyszedł
co do cyfry jak w `KRAKEN_SIZING_RESULTS_2026-10-30.md`.

## Rejestr

12 kandydatów zmierzonych, **12 odrzuconych** (#12: 6 wariantów). Nie wracać do
skalowania pozycji zmiennością (zrealizowaną ani DVOL) bez nowego mechanizmu.
