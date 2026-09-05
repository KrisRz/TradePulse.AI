# Zaostrzenie bramki B — PRE-REJESTRACJA z 2026-09-05

> **Status: WIĄŻĄCE.** Spisane 2026-09-05, **zanim** dane mogły którekolwiek z tych
> kryteriów spełnić (dowód liczbowy w §3). Obowiązuje **od oceny 2026-10-08**.
> Ocena **2026-09-10 biegnie kodem JAK JEST** — tamta pre-rejestracja zostaje
> nietknięta.
>
> Ten dokument wolno **zaostrzać** przed danymi. **Nie wolno go poluzować nigdy** —
> ani przez zmianę progu, ani przez zmianę definicji, ani przez „wyjątek ten jeden raz".

---

## 1. Co dokładnie dopisujemy

Bramka B ma dziś regułę aktywności (`round_trips ≥ 2` **i** `days_in_market ≥ 10`)
i cztery progi bezwzględne (`maxDD ≤ 25%`, `PF ≥ 1,3`, `net_pnl > 0`,
`fee_drag < 20%`, plus `tracking_error < 10%`, gdy jest podany). **Nic z tego nie
jest zmieniane ani usuwane.** Dochodzą trzy warunki; werdykt `PASS` wymaga
spełnienia **wszystkich** dotychczasowych **oraz wszystkich trzech nowych.**

### B5 — siła statystyczna: `psr_vs_zero ≥ 0,95`

Probabilistic Sharpe Ratio obserwowanego Sharpe'a **per-bar** przeciwko `SR* = 0`,
wzorem Baileya i López de Prado (2012), tym samym, który `gate.py` już liczy
(`probabilistic_sharpe`), na tej samej serii zwrotów bar-do-bara z logu decyzji
(**łącznie z barami flat**). Równoważnie: `min_trl_bars_remaining == 0` przy
`PSR_CONFIDENCE = 0,95`.

Jeśli PSR jest **nieokreślone** (okno bez wariancji zwrotów — bot cały czas flat),
B5 **nie jest spełnione**. Brak dowodu nigdy nie jest dowodem; to ta sama zasada,
którą bramka A stosuje przez `SKIPPED → INCOMPLETE`.

### B6 — sens ekonomiczny: `sharpe_ann(strategia) ≥ sharpe_ann(buy & hold)`

Obie liczby z **identycznej** serii barów, od `WINDOW_START` do dnia oceny, obie
annualizowane tym samym `√(barów w roku)`, obie wyceniane mark-to-market na dzień
oceny (otwarta pozycja liczy się po obu stronach tak samo).

**Definicja buy & hold jest wiążąca: TA Z KOSZTAMI** — jedno wejście na pierwszym
barze okna i jedno wyjście na barze oceny, po tym samym `fee_rate` i `slippage`,
którymi obciążana jest strategia (`walkforward.py:248-258`, nie
`metrics.py:99-101`). W repo istnieją dwie definicje B&H i audyt 2026-09-04 (L9)
ostrzega, żeby ich nie mylić — tutaj obowiązuje ta droższa dla B&H, czyli
**korzystniejsza dla bota**. Jeśli bot nie bije nawet tak liczonego B&H, nie bije go
w ogóle.

### B7 — długość okna: `window_days ≥ 365`

`window_days = (as_of − WINDOW_START).days`, dokładnie jak dziś w `gate.py:206`.

### Werdykt pośredni

Spełnione wszystkie stare kryteria, ale nie wszystkie nowe → werdykt
**`PROVISIONAL_PASS`**, nie `PASS`. `PROVISIONAL_PASS` **nie autoryzuje M6** i nie
uprawnia do wpłacenia ani jednego funta. Jest wyłącznie informacją: „stare progi
przeszły, dowód jeszcze nie".

---

## 2. Dlaczego akurat te trzy, a nie coś innego

**Każde z osobna ma dziurę; razem się domykają.**

- **Samo B5** nie wystarcza, bo PSR liczy się z **barów**, nie z transakcji. Jedna
  otwarta pozycja w silnym trendzie potrafi podnieść Sharpe'a i PSR bez ani jednej
  zamkniętej transakcji — a to jest dokładnie stan z dnia pisania tego dokumentu
  (Sharpe 1,29 przy **0 round-tripach**).
- **Samo B7** nie wystarcza, bo kalendarz nie jest dowodem. Po roku wciąż można mieć
  dwie zamknięte transakcje i `PF` z rzutu monetą.
- **Samo B6** nie wystarcza — i co ważniejsze, **byłoby niesprawiedliwe** w krótkim
  oknie. Trend-following z definicji przegrywa z B&H w czystej hossie (wchodzi po
  potwierdzeniu, siedzi flat w konsolidacji) i odrabia to dopiero w bessie, której
  ani razu jeszcze nie widzieliśmy. B6 **ma sens tylko z B7**: okno musi być na tyle
  długie, żeby mogło zawierać oba reżimy. To jest właściwy powód, dla którego te dwa
  chodzą w parze, a nie „na wszelki wypadek".

**Czego świadomie NIE robimy: nie podnosimy `MIN_ROUND_TRIPS` z 2.** Kusi, bo `PF`
przy `n = 2` to rzut monetą (audyt §3 HIGH-2). Ale EMA20/100 zamyka **1,69
round-tripu rocznie** na 1d — próg 10 transakcji czyniłby bramkę nierozstrzygalną
przez sześć lat. To nie byłby rygor, tylko przeniesienie decyzji na „nigdy". Ciężar
dowodu biorą na siebie B5 (siła statystyczna z barów, których jest dużo) i B6 (sens
ekonomiczny), a nie liczba transakcji, których z konstrukcji strategii nie będzie.

Zakres: bramka B dotyczy **kanału 1d** (mierzony kanał M5). Kanał 4h ma własną
bramkę C. Porównanie do B&H należy jednak **raportować jako diagnostykę także dla
4h** — dziś jest 1,43 pp za rynkiem i to musi być widoczne, nawet jeśli nie jest
progiem.

---

## 3. Dowód, że to nie jest dopasowanie kryteriów do wyniku

Stan **w chwili pisania**, odczytany z produkcji (`gate --source dynamodb` oraz
log decyzji w DynamoDB):

| | kanał 1d (mierzony) | kanał 4h (giełdowy) |
|---|---|---|
| bary w oknie | 52 | 180 |
| zamknięte round-tripy | **0** | 1 |
| zwrot strategii | +3,23% | +22,45% |
| zwrot buy & hold | **+23,02%** | **+23,83%** |
| Sharpe strategii (ann.) | 1,293 | 6,401 |
| Sharpe B&H (ann.) | **3,887** | **6,657** |
| maxDD strategii | −3,63% | −4,58% |
| maxDD B&H | −5,61% | −4,55% |
| `psr_vs_zero` | **0,695** | — |
| `window_days` | **51** | — |
| MinTRL | 523 bary (472 więcej ≈ 15–16 mies.) | — |

**Żadne z trzech nowych kryteriów nie jest dziś spełnione, a B6 nie jest spełnione
z dużym zapasem na obu kanałach.** Kierunek zmiany jest jednoznacznie
zaostrzający: te warunki mogą wyłącznie **opóźnić** `PASS`, nigdy go wyprodukować.
Fałszywy negatyw kosztuje czas; fałszywy pozytyw kosztuje pieniądze — i to jest cała
asymetria, na której ta decyzja stoi.

Dla porządku odnotowane: werdykt oceny **2026-09-10 jest już przesądzony** i wynosi
`INCONCLUSIVE_EXTEND`, bo reguła aktywności (`round_trips 0 < 2`) odpala przed
progami. Nie ma więc żadnego wyniku, pod który można by te kryteria stroić — piszemy
je, gdy licznik transakcji stoi na zerze.

---

## 4. Kiedy i jak to wchodzi do kodu

- **2026-09-10:** ocena uruchomiona `gate.py` **bez żadnej zmiany**. Raport do `docs/`.
- **Po tej ocenie** (audyt §10 KROK 2): implementacja B5/B6/B7 w `gate.py` wraz z
  `PROVISIONAL_PASS`, plus poprawki jednostek DSR (`0,3/365`) i diagnostyki. Testy
  muszą pokrywać przypadek „stare progi przeszły, nowe nie" → `PROVISIONAL_PASS`.
- **Od oceny 2026-10-08** (pierwsza kolejna w cyklu 28-dniowym) obowiązuje pełny
  zestaw.

Gdyby implementacja nie zdążyła przed 2026-10-08, ocena z tamtego dnia i tak **nie
może** wydrukować `PASS` — obowiązuje ten dokument, nie stan kodu. Werdykt liczony
starym kodem należy wtedy odczytać ręcznie przez pryzmat B5/B6/B7 i zapisać jako
`PROVISIONAL_PASS`.

---

## 5. Źródła

- `docs/AUDIT_2026-09-04.md` §3 HIGH-2 (bramka B może wydrukować `PASS` przy 2
  round-tripach; brak kryterium względem B&H), MEDIUM-4 (jednostki DSR), L9 (dwie
  definicje B&H)
- `docs/ANALIZA_KALIBRACJI_2026-07-28.md` (moc bramki ~1% w 56 dni; horyzont 12–18
  mies.)
- Bailey & López de Prado (2012), *The Sharpe Ratio Efficient Frontier* — PSR, MinTRL
- `gate.py:73-82` (pre-rejestrowane stałe), `:206` (`window_days`), `:236-251`
  (PSR/DSR dziś doradcze), `:264-286` (precedencja werdyktów)
