# Analiza kalibracji i mocy bramki M5 — 2026-07-28

**Zakres:** czy konfiguracja, która handluje na produkcji, jest tą, którą
zwalidowaliśmy; czy parametry są przeuczone; czy bramka M5 ma moc statystyczną,
żeby cokolwiek rozstrzygnąć.

**Dyscyplina M5:** cała analiza liczona wyłącznie na `data/ml/historical/`
(bary `< 2026-07-16`, linia holdout). Zero podglądania wyników żywego okna.
**Żaden parametr strategii nie został zmieniony.**

**Reprodukcja:** `python scripts/research/calibration_audit.py`

---

## Werdykt w trzech zdaniach

1. **Konfiguracja produkcyjna (stałe EMA20/100) nigdy nie była zmierzona** —
   liczby z `M4_EDGE_VALIDATION.md` należą do wariantu przestrajanego co fold.
   Zmierzyłem ją teraz: **broni się** (OOS Sharpe 1.00–1.14, bije B&H w każdym
   layoucie). Luka zamknięta, wynik pozytywny.
2. **Nie ma przeuczenia** — 20/100 leży w środku szerokiego plateau, a in-sample
   plasuje się poniżej mediany. Edge siedzi w rodzinie „EMA trend-following
   long-only BTC 1d", nie w konkretnych liczbach.
3. **Bramka M5 w obecnej formie ma ~1% szans na rozstrzygnięcie** w 8 tygodni.
   To jest realny problem planu i wymaga rozdzielenia bramki (zrobione,
   `plan.md` §3).

---

## 1. Konfiguracja wdrożona ≠ konfiguracja zwalidowana

`walkforward.py` dobiera parametry z siatki `fast∈{10,20,30} × slow∈{50,100,200}`
**osobno na każdym foldzie**. Bot na Lambdzie handluje **stałe** EMA20/100
(`app/backend/paper_trading/run.py:22-27`). To są dwie różne strategie.

Co optymalizator faktycznie wybiera i jak wypada przy tym prod:

| layout foldów | adaptive (M4) | **stałe 20/100 = prod** | Buy&Hold | 20/100 wybrane | top pick |
|---|---|---|---|---|---|
| 730/180 | 1.11 | **1.01** | 0.87 | 0/13 | 10/50 ×13 |
| 500/125 | 1.14 | **1.00** | 0.97 | 0/21 | 10/50 ×21 |
| 1000/250 | 1.12 | **1.14** | 1.00 | 0/8 | 10/50 ×8 |
| 365/90 | 1.18 | **1.02** | 0.81 | 0/31 | 10/50 ×31 |

**EMA20/100 nie zostało wybrane ani razu — 0 na 73 foldy.** Optymalizator
konsekwentnie preferuje 10/50.

### Czy to znaczy, że wdrożyliśmy coś złego? Nie.

Stałe 20/100 na tych samych oknach OOS daje Sharpe **1.00–1.14** i **bije
buy&hold we wszystkich czterech layoutach**. Konfiguracja produkcyjna jest
obroniona — tyle że dowód powstał dziś, a nie w M4.

`M4_EDGE_VALIDATION.md` uczciwie opisuje metodę („params fitted in-sample per
fold"), ale kończy się zdaniem „Paper bot keeps trading EMA20/100 … exactly
what is deployed on Lambda", co sugeruje, że opublikowane 1.11 dotyczy prod.
**Nie dotyczy.** To jest luka w raportowaniu, nie w strategii.

### Skąd w ogóle wzięło się 20/100

Z domyślnych wartości w `run.py:22` — nie z żadnego pomiaru. Wybór był
arbitralny i, jak się okazuje, szczęśliwy.

---

## 2. Przeuczenie: nie ma go

Powierzchnia parametrów, 42 stałe kombinacje (`fast∈{5..40} × slow∈{50..200}`),
te same okna OOS (layout 730/180):

| | OOS Sharpe |
|---|---|
| najlepsza (5/100) | 1.17 |
| **20/100 (prod)** | **1.01 — ranga 16/42** |
| mediana rodziny | 0.99 |
| najgorsza | 0.65 |
| Buy&Hold na tym samym oknie | 0.87 |

Dwa wnioski:

- **Cała rodzina działa.** Rozrzut 0.65–1.17 przy B&H 0.87 znaczy, że edge jest
  własnością podejścia (long-only trend-following na dziennym BTC), nie
  konkretnej pary liczb. To najlepszy możliwy wynik dla wiarygodności.
- **20/100 nie jest cherry-pickiem.** In-sample plasuje się **28/42** — poniżej
  mediany. Przeuczony parametr siedziałby na szczycie in-sample i spadał OOS;
  tutaj jest odwrotnie. Ranking in-sample i OOS są wręcz słabo skorelowane
  (5/100: in-sample 0.79 → OOS 1.17), co samo w sobie jest ostrzeżeniem przed
  jakimkolwiek strojeniem na przeszłości.

**Konsekwencja: nie ma powodu ruszać parametrów.** Zmiana 20/100 → 5/100 na
podstawie tej tabeli byłaby dokładnie tym przeuczeniem, przed którym broni
reguła holdout — różnica 0.16 Sharpe’a mieści się w szumie doboru okien,
a w oknie M5 zmiana i tak jest zakazana.

---

## 3. Odporność konfiguracji produkcyjnej

### Koszty — lepiej niż zakładaliśmy

| fee/stronę | OOS Sharpe | zwrot |
|---|---|---|
| 0.075% | 1.02 | +839% |
| 0.100% (prod) | 1.01 | +830% |
| 0.200% | 1.00 | +793% |
| 0.300% | 0.98 | +758% |
| 0.500% | 0.96 | +692% |

Edge **przeżywa 0.5% na stronę**. Powód: tylko ~20 trejdów przez 6.5 roku OOS —
fee drag jest strukturalnie mały. Zapis w planie „umiera powyżej ~0.3% fee"
pochodził z wariantu krótkoterminowego i został poprawiony.

### Reżimy — to jest ochrona kapitału, nie drukarka

| okres | EMA20/100 | Buy&Hold |
|---|---|---|
| 2017–2020 | +119% (Sharpe 0.72) | +502% (Sharpe 1.08) |
| 2021–2022 | **+15%** (Sharpe 0.38) | **−44%** (Sharpe −0.03) |
| 2023–2024 | +185% (Sharpe 1.40) | +462% (Sharpe 2.01) |
| 2025–2026 | **−3%** (Sharpe 0.04) | **−32%** (Sharpe −0.34) |

Strategia systematycznie przegrywa w hossie i systematycznie chroni w bessie.
Dokładnie to obiecuje „uczciwa prawda" w §0 planu — i to się potwierdza
w bieżącym reżimie (2025-26: −3% vs −32%).

---

## 4. 🔴 Bramka M5 nie ma mocy statystycznej

To jest najważniejsze ustalenie tego audytu.

### Jak rzadko ta strategia handluje

- **15 zamkniętych round-tripów przez 8.9 roku = 1.69/rok**
- 51% czasu w rynku
- najdłuższy trejd 383 dni, najkrótszy 5 dni

(Nota w planie mówiła „~3.4 trejdy/rok" — liczyła nogi, nie round-tripy.)

### Co z tego wynika dla reguły aktywności

Reguła pre-rejestracji z 2026-07-25: progi oceniamy tylko przy **≥2 zamkniętych
round-tripach ORAZ ≥10 dniach w pozycji**. Policzone na wszystkich rolujących
oknach 2017-09 → 2026-07-15 (n=3184 dla okna 56-dniowego):

| długość okna | P(reguła aktywności spełniona) |
|---|---|
| **56 dni (8 tygodni — plan)** | **1%** |
| 84 dni | 2% |
| 112 dni | 5% |
| 168 dni | 14% |
| 252 dni | 33% |
| 365 dni | 59% |
| 547 dni (18 mies.) | 93% |
| 730 dni (24 mies.) | 100% |

Rozkład w oknie 56-dniowym: **P(0 round-tripów) = 74%**, P(1) = 25%, P(≥2) = 1%.

Okno M5 startowało dodatkowo w pozycji FLAT (ostatnie wyjście 2026-05-30),
a EMA20 jest 7.6% pod EMA100 na ostatnim barze danych — do wejścia potrzeba
crossu, więc realna szansa jest jeszcze niższa niż te 1%.

### Werdykt

**Ośmiotygodniowe okno nigdy nie miało mocy, żeby rozstrzygnąć rentowność.**
Werdykt `INCONCLUSIVE_EXTEND` 2026-09-10 jest praktycznie pewny i będzie się
powtarzał co 28 dni przez około rok. To nie jest awaria bramki — pre-rejestracja
słusznie przewidziała ten przypadek — ale plan mylnie zakładał, że po 8
tygodniach będziemy coś wiedzieć o pieniądzach.

---

## 5. Rozwiązanie: rozdzielenie bramki (wdrożone w planie)

Pre-rejestracja z 2026-07-28, **44 dni przed najwcześniejszą oceną**, oparta
wyłącznie na danych sprzed holdoutu. Pełna specyfikacja: `plan.md` §3.

**BRAMKA A — wierność wykonania.** Rozstrzygalna w oknie 8-tygodniowym.
Dowodzi, że maszyneria nie kłamie: kompletność logu, parytet sygnału z silnikiem,
parytet ceny z Binance, brak look-ahead na żywo, parytet księgowości, ciągłość
infrastruktury. Wszystkie 6 kryteriów liczone z danych, które już zapisujemy.
**Nie odblokowuje realnych pieniędzy.**

**BRAMKA B — rentowność.** Progi i reguła aktywności **bez żadnych zmian**.
Zmienia się wyłącznie oczekiwany horyzont: 12–18 miesięcy zamiast 8 tygodni.
**Tylko ta bramka otwiera M6.**

Kluczowa dyscyplina: **żaden próg nie został poluzowany.** Rozdzielenie oddziela
to, czego okno dowodzi, od tego, czego nie dowodzi — nie obniża poprzeczki.
Gdyby horyzont 12–18 miesięcy okazał się nie do przyjęcia, jedynym uczciwym
wyjściem jest zmiana strategii na częściej handlującą (i restart zegara), nigdy
obniżenie progów.

---

## 6. Ustalenia poboczne

**Paczka Lambdy nie była reprodukowalna.** `scripts/build_lambda_package.sh`
instalował `requests` bez wersji — każdy rebuild wciągał aktualne PyPI do bota,
który handluje. Prod miał `requests 2.34.2`, a `requirements.txt` deklarował
`2.31.0`. Naprawione: `app/backend/requirements-lambda.txt` z dokładnymi pinami
(zweryfikowane — rozwiązują się dokładnie do zestawu z działającego prod, więc
redeploy jest zbędny) + 11 testów w `test_lambda_package.py`.

**Dryf prod ↔ repo: funkcjonalnie zerowy.** Zdeployowany zip (2026-07-22, obie
Lambdy `CodeSha256 r8Luxno…tNq0=`) różni się od repo w `backtesting/data.py`
(fix ISO8601 z PR #17) i pustym `app/backend/__init__.py`; nowe narzędzia CLI
(`gate.py`, `bulk_download.py`, `integrity.py`) w zipie nie istnieją, ale
Lambda ich nie uruchamia.

> **Sprostowanie 2026-07-28 (cd.):** pierwotnie napisałem tu, że „bot nie
> importuje `data.py`". To było nieścisłe — `data.py` **jest** ładowany przy
> cold starcie przez `backtesting/__init__.py:18` (`from . import data,
> indicators`). Wniosek się nie zmienia, ale z innego powodu: zmieniona linia
> siedzi w `load_csv()`, a bot czyta rynek przez `feed.fetch_klines()` i
> `load_csv` nigdy nie wywołuje. Import bez wywołania = zero zmiany zachowania.
> Zweryfikowane przez zaimportowanie obu handlerów i wylistowanie
> `sys.modules`, nie przez czytanie nagłówków importów.

Redeploy nie jest potrzebny: kod ścieżki bota jest funkcjonalnie identyczny,
a przypięte zależności rozwiązują się dokładnie do zestawu, który już działa.
W oknie M5 `terraform apply` bez zysku funkcjonalnego = samo ryzyko.

**Zero ML na produkcji — potwierdzone.** Zip zawiera wyłącznie `paper_trading`
+ `backtesting` + `requests`. Żaden model z `models/enterprise/` nie jest
ładowany, żaden nie był trenowany od M4. Zgodne z ✅D9 / ✅D11.

**Stan produkcji 2026-07-28:** scheduler ENABLED, obie Lambdy `CodeSha256
r8Luxno…tNq0=`, 3 alarmy OK, log decyzji 2026-07-15 → 2026-07-27 **bez luk**
(13 rekordów), status URL 200, bot FLAT $10 000, suite testów zielony.

---

## Co dalej

1. **Zaimplementować `gate.py --fidelity`** (Bramka A) przed 2026-09-10 — M5.4.
   Bez tego okno zakończy się bez żadnego formalnego dorobku.
2. `tfstate` → S3 (nadal lokalny, otwarte od 2026-07-21).
3. Odnowić domenę przed 2026-09-10 (wygasa 2026-09-29).
4. Kwarantanna enterprise w monolicie — porządek, zero wpływu na prod.
