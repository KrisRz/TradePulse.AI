# F7 — kontrole ryzyka na poziomie pozycji (projekt + pre-rejestracja, 2026-08-07)

> Kill-switch (T1/T2/T3) chroni KSIĘGĘ — zatrzymuje kanał, gdy maszyneria lub
> rynek robi coś katastroficznego, i wymaga ręcznego re-arm. F7 chroni POZYCJĘ:
> dwa automatyczne, węższe bezpieczniki, które spłaszczają i wracają do gry
> według z góry spisanych reguł. Budowane od zera (~150 linii z testami) —
> stop-lossy z `intelligent_exit_engine` mają próg ≈0 przez podwójne dzielenie
> ATR i NIE są reanimowane (D11, kwarantanna).

## Zmierzona przesłanka (PRZED wyborem progów; dane < 2026-07-16)

`scripts/research/f7_premise.py`, EMA20/100 long-only:

| | 1d (8,9 lat, 15 trejdów) | 4h (7,5 roku, 91 trejdów) |
|---|---|---|
| stop 5% — trafienia intrabar/close | 12 / 9 | 36 / 28 |
| stop 10% — trafienia intrabar/close | 7 / 6 | 7 / **2** |
| stop 15% — trafienia intrabar/close | 6 / 4 | 1 / 0 |
| Sharpe bez → ze stopem 10% (intrabar) | 0,71 → 0,89 | 1,14 → 1,10 |
| dni z −10% od otwarcia dnia | n/d (1 bar = 1 dzień) | 7 (0,93/rok) |
| dni z −5% od otwarcia dnia | n/d | 53 (**7/rok** — za często) |

Wnioski, z których wynikają progi:
- **5% to strojenie strategii, nie ochrona** (na 1d niszczy Sharpe'a 0,71→0,45;
  dzienny 5% odpalałby 7×/rok). Odrzucone.
- **10% jest ochronne i rzadkie**: stop close-evaluated ≈ 2 trafienia w 7,5
  roku na 4h; dzienny limit ≈ 1 dzień/rok. Wpływ na metryki strategii
  pomijalny (Sharpe 1,14→1,10 przy surowszej wersji intrabar).
- Na 4h stop 5% podniósł in-sample Sharpe'a (1,25) — celowo IGNORUJEMY:
  wybieranie progu bezpiecznika pod Sharpe'a = fitting. Bezpiecznik ma być
  rzadki i szeroki, nie zyskowny.

## Pre-rejestrowane progi i semantyka

| Kontrola | Próg | Semantyka |
|---|---|---|
| **SL. Stop-loss pozycji** | close ≤ `entry_fill` × (1 − **10%**) | Oceniany na ZAMKNIĘCIU bara (kanał 4h widzi tylko close'y — bez zleceń resting). Wyjście MARKET zwykłą ścieżką w tym samym przebiegu. **Re-entry zablokowane, aż target strategii sam wróci do 0** — dokładnie semantyka `blocked_side` silnika backtestu (engine.py), więc backtest i live mówią tym samym językiem. |
| **DL. Dzienny limit straty** | equity ≤ `day_start_equity` × (1 − **10%**) | `day_start_equity` = equity przy pierwszym przetworzonym barze doby UTC. Po przekroczeniu: spłaszcz + blokada NOWYCH wejść do końca doby UTC; o północy blokada znika automatycznie (bez ręcznego re-arm — od katastrof maszynerii jest kill-switch). |

- **Kolejność:** kill-switch (halt?) → F7 (target overlay) → reconcile.
  Kill-switch wygrywa zawsze.
- **Fail-closed:** wyjątek w ocenie F7 propaguje → Lambda error → alarm →
  brak transakcji w tym przebiegu (idempotentny retry).
- **Zakres:** kanał venue-4h teraz, M6 w przyszłości. Kanał 1d M5 NIETKNIĘTY
  (okno pomiarowe; zresztą dzienny limit na 1d nie ma sensu — 1 bar = 1 dzień).
- Stan (`stop_blocked`, `day`, `day_start_equity`, `daily_blocked`) persystowany
  w `extra.position_risk` obok kill-switcha, atomowo ze stanem bota.

## Znane ograniczenie, spisane z góry

Backtest modeluje stop intrabar (fill na poziomie stopu po `low`); żywy kanał
ocenia po close i wychodzi marketem kilkanaście minut po zamknięciu bara —
żywy stop jest GORSZY (późniejszy). Pomiar mówi, że przy 10% różnica to
7 vs 2 zdarzenia na 7,5 roku. Jeśli kiedyś zejdziemy niżej z progiem albo
zechcemy parytetu, właściwe narzędzie to zlecenie STOP na giełdzie — osobna
decyzja egzekucyjna, nie zmiana progu.
