# TradePulse.AI — MASTER PLAN (definitywny, wieloseryjny)

> **Po co to jest:** żeby „jutrzejszy ja / future Claude" po otwarciu tego pliku
> wiedział DOKŁADNIE gdzie jesteśmy, gdzie zaczynamy dziś i dokąd zmierzamy.
> To jest jedyne źródło prawdy o pracy. Plik lokalny (gitignored).
>
> **Zasada obsługi:** czytaj sekcję 0 → 1 → znajdź pierwszy niezaznaczony `[ ]`
> w ROADMAP → rób → odhacz → dopisz linię do „Log sesji" na końcu.
>
> Ostatnia aktualizacja: **2026-07-15**

---

# ⏯ WZNOWIENIE — CZYTAJ TO NAJPIERW (gdy user mówi „kontynuujemy z TradePulse")

> Trigger: user mówi „kontynuujemy / wracamy do TradePulse / co dalej z botem".
> Nie pytaj „od czego zacząć" — odpowiedź jest tu. Wykonaj protokół i ruszaj.

### 📍 STATUS TERAZ  (← tę linię AKTUALIZUJ na końcu każdej sesji)
- **Milestone:** M0 ✅ + M1 ✅ + M2 ✅ + M3 ✅ + M4 ✅ (decyzje na danych) → **M5 BIEGNIE**.
- **TRYB: CZEKAMY.** Okno M5 od 2026-07-16, oceny bramek ≥2026-09-10, ZERO zmian
  strategii w oknie. Health-check 2026-07-17: wszystko zielone (scheduler, Lambda,
  DynamoDB, SNS). Deep-audit 6 warstw zrobiony → docs/ANALIZA_6_WARSTW_2026-07-17.md
  (werdykt: enterprise nie naprawiać; ✅D11). Deep-audit E2E 2026-07-21 →
  docs/ANALIZA_E2E_2026-07-21.md (rdzeń solidny). Top-4 fixy M5-safe WDROŻONE
  2026-07-22 (PR #16 zmergowany do main + `terraform apply`): dashboard MTM
  equity (H1), heartbeat alarm+DLQ (M2), load-bearing log decyzji (M1), guard
  min-history (M3). Zweryfikowane na żywo: obie Lambdy CodeSha256 =
  r8Luxno...tNq0= (prod=repo), DLQ+alarm istnieją, dashboard renderuje MTM
  equity $10k FLAT. tfstate zbackupowany → ~/TradePulse_safety/tfstate-backups.
  OTWARTE M5-safe (jeszcze nie zrobione): kwarantanna enterprise w monolicie,
  tfstate→S3, domena → odnowić przed 09-10 (reminder ustawiony). Opcjonalne prace
  w oknie (nie dotykają strategii), KOLEJNOŚĆ: (1) ✅ ZROBIONE 2026-07-25 — dane
  historyczne kompletne i zwalidowane (1h dociągnięty, holdout wyegzekwowany,
  tooling w repo; branch feat/historical-data-prep, patrz §4);
  (2) ✅ ZROBIONE 2026-07-25 — skrypt bramki gate.py (PR #18) + PRE-REJESTRACJA
  reguły aktywności w §3 (0 trejdów ≠ FAIL, tylko INCONCLUSIVE_EXTEND);
  zweryfikowany na prod (dzień 9: WINDOW_RUNNING); (3) ✅ ZROBIONE 2026-07-25 —
  projekt kill-switcha max-DD pod M6 (PR #19, docs/KILL_SWITCH_DESIGN_2026-07-25.md;
  T1 25% od szczytu M6 / T2 rozjazd 10% / T3 dzień 15%, fail-closed, manual
  rearm; implementacja DOPIERO w M6). PR #17/#18/#19 **ZMERGOWANE** 2026-07-25.
  (4) ✅ ZROBIONE 2026-07-28 — audyt kalibracji
  (docs/ANALIZA_KALIBRACJI_2026-07-28.md, skrypt
  scripts/research/calibration_audit.py): konfiguracja PRODUKCYJNA (stałe
  EMA20/100) zmierzona PO RAZ PIERWSZY — broni się (OOS 1.00–1.14, bije B&H
  w każdym layoucie), brak przeuczenia (in-sample ranga 28/42), przeżywa
  0.5% fee. ⚠️ ODKRYCIE KRYTYCZNE: bramka M5 ma **1% szans** na spełnienie
  reguły aktywności w 56 dni (strategia robi 1.69 round-tripa/rok) → BRAMKA
  ROZDZIELONA (§3): A=wierność wykonania (rozstrzygalna teraz), B=rentowność
  (progi bez zmian, horyzont 12–18 mies., tylko ona otwiera M6). Naprawione
  też: paczka Lambdy nie była reprodukowalna (unpinned `requests`).
  Zostały porządki: kwarantanna enterprise, tfstate→S3.
- **NASTĘPNA AKCJA:** zaimplementować `gate.py --fidelity` (Bramka A, M5.4)
  PRZED 2026-09-10 — inaczej okno skończy się bez formalnego dorobku.
  Poza tym M5 — bot zbiera żywe decyzje. Otwarta decyzja:
  hosting frontendu na tradepulseai.co.uk (domena wykupiona do 2026-09-29,
  strefa DNS skasowana — trzeba nową + NS; pełny front wymaga backendu w
  chmurze ~$5-25/mo, alternatywa: tylko bot-status pod subdomeną ~$0).
  Status bota LIVE: https://xwibtclmvzlqtz2xtgrnm7l3tm0hzqbs.lambda-url.eu-west-2.on.aws/
- **Branch:** PR #2 ZMERGOWANY do main (2026-07-16 rano, CI zielone: pytest + gitleaks).
  Nową pracę zaczynaj z main (nowy feature branch).
- **Ostatnio zrobione:** nocna sesja 2026-07-16 — cała SESJA A (A1–A7), M1, M2
  (Lambda+DynamoDB+Scheduler na AWS, ~$0/mo, smoke-test OK), duża część M3.
- **WAŻNE ODKRYCIA:** (1) konto AWS było CZYSTE — stary App Runner stack już
  nie istniał; infra-serverless/ to jedyna żywa infra (stan TF lokalny!).
  (2) Commit 9665f59 cofnął fixy z 596d277 (normalizacja MACD, regime override)
  — przywrócone. (3) L5 dostawał cechy w złych jednostkach (wolumen 24h vs
  per-bar, USD vs %) — naprawione przez ml/l5_features.py (training parity).
  (4) Potwierdź subskrypcję SNS e-mail (alert Lambdy) — mail do krisgrzepka@gmail.com.

### Protokół wznowienia (5 kroków — rób po kolei)
1. **Przeczytaj** ten plik: sekcja `0` (cel) → `📍 STATUS TERAZ` → pierwszy
   niezaznaczony `[ ]` w `ROADMAP SZCZEGÓŁOWA`.
2. **Sprawdź branch:** `git -C /Applications/TradePuls branch --show-current`
   → ma być `improvements/security-and-strategies`. Jeśli nie — przełącz.
3. **Zweryfikuj** że cytowane `plik:linia` z danego kroku nadal istnieją
   (kod mógł się zmienić) — grep zanim zaczniesz edytować.
4. **Zrób** najbliższy `[ ]`. Napotkasz `❓` (punkt decyzyjny)? → analiza TU
   i teraz, potem decyzja (patrz sekcja PUNKTY DECYZYJNE). Odhacz `[x]`.
5. **Testy przed końcem sesji** (muszą być zielone):
   ```bash
   cd /Applications/TradePuls && pytest \
     app/backend/tests/test_backtesting.py \
     app/backend/tests/test_paper_trading.py -q
   ```
   Na końcu: dopisz 1 linię do `Log sesji` + zaktualizuj `📍 STATUS TERAZ`.

### Przydatne
- Cały lokalny stack (backend+frontend+DynamoDB): `./start_local.sh`
- Krok paper bota ręcznie: `python -m app.backend.paper_trading.run step`
- Archiwum (modularny TF, .env): `~/TradePulse_safety/` (NIE kasować).

---

# 💡 KONCEPT — o co chodzi w tej apce (zrozum TO najpierw)

TradePulse.AI to **mała, best-in-class aplikacja tradingowa dla 1 usera (mnie)**,
która handluje BTC z jedną żelazną dyscypliną: **żadnemu sygnałowi nie ufamy,
dopóki nie udowodni edge na rygorystycznym backtesterze — a to, co backtestujemy,
MUSI być identyczne z tym, co gra na żywo** (wspólny kod sygnału + kosztów).
Budujemy od bezpiecznej strony: najpierw paper trading (wirtualny portfel), mierzymy
wszystko, i dopiero po tygodniach dowodów przechodzimy na małe realne kwoty.

- **CO:** bot day-trading na BTCUSDT — strategie rule-based (zwalidowane) + ML jako
  *filtr* nad nimi (nie samodzielny wyrocznia).
- **JAK:** dane Binance → indykatory → strategia daje sygnał → ML filtruje →
  risk/sizing → egzekucja (backtest ↔ paper ↔ live, ten sam kod).
- **GDZIE:** serverless AWS (~$0/mo, Lambda+cron), bo 1 user + strategia dzienna.
- **KIEDY realne pieniądze:** dopiero po ≥8 tyg. paper spełniającego twarde progi.
- **STRATEGIA (dziś):** long-only EMA trend-following 1d — zwalidowana, redukuje
  drawdown, bije risk-adjusted. Więcej edge = przyszłość (ML filtr, sizing, rynki).
- **DLACZEGO:** ma się opłacać — minimum zarobić na własne koszty. Uczciwie, powoli.

> Jednym zdaniem: **„backtest = live, paper first, dowody przed pieniędzmi,
> tanio i dla jednego."**

---

# 0. GWIAZDA POLARNA (north star) — po co w ogóle to robimy

**Cel nadrzędny:** zbudować bota, który realnie zarabia — najpierw na paper
tradingu, potem na małych realnych kwotach. **Minimum sukcesu: bot zarabia na
siebie** (pokrywa koszty infra + abonament narzędzi). To nie jest hobby-toy,
to ma być *best-in-class* mała aplikacja tradingowa dla jednego użytkownika (ja).

**Uczciwa prawda na dziś (nie oszukujmy się):**
- Zwalidowany edge (EMA trend-following 1d) **redukuje ryzyko/drawdown** i bije
  buy&hold *risk-adjusted* (OOS Sharpe 1.00–1.14 vs B&H 0.81–1.00), ale **NIE
  bije** absolutnego zwrotu. Odporność na koszty jest LEPSZA niż sądziliśmy:
  przy 0.5%/stronę Sharpe wciąż 0.96 (tylko ~20 trejdów na 6.5 roku OOS) —
  stara nota „umiera >0.3% fee" pochodziła z wariantu krótkoterminowego
  i jest NIEAKTUALNA (zmierzone 2026-07-28,
  docs/ANALIZA_KALIBRACJI_2026-07-28.md).
- To znaczy: „zarobek" na starcie = **lepszy risk-adjusted + ochrona kapitału**,
  a nie drukarka. Żeby był realny zarobek netto, musimy zrobić 3 rzeczy:
  1. **Minimalizować koszty** (mało transakcji = 1d timeframe, maker fees).
  2. **Dodać edge** (ML jako filtr nad strategią, może kilka rynków).
  3. **Sizing** (volatility targeting) — więcej ryzyka gdy edge jest silny.
- **Nie ma gwarancji** że pobijemy rynek. Dlatego: paper first, mierzymy
  wszystko, realne pieniądze dopiero po dowodach, i to małe.

**Definicja „skończone" (koniec drogi):**
> Bot lata w chmurze serverless (~$0/mo), na paper tradingu przez ≥8 tygodni
> osiąga zdefiniowane progi metryk (niżej), live-tracking zgadza się z paper,
> i wtedy przechodzimy na małe realne kwoty z twardymi limitami ryzyka.

---

# 1. GDZIE ZACZĄĆ / GDZIE SKOŃCZYĆ (mapa 30 000 stóp)

```
START ──► [M0] Zaufanie do rdzenia    ► silnik nie kłamie, testy zielone
      ──► [M1] Paper bot na żywo       ► zwalidowana strategia EMA lata co dzień
      ──► [M2] Serverless deploy       ► w chmurze, ~$0/mo, bez laptopa
      ──► [M3] Aplikacja spójna E2E     ► frontend↔backend, admin, dashboard OK
      ──► [M4] Więcej edge (ML filtr)   ► udowodnione na walk-forward, nie na oko
      ──► [M5] 8+ tygodni paper OK      ► metryki ≥ progi, live=paper
      ──► [M6] Małe realne kwoty        ► $50–100, twarde limity, powoli
KONIEC ─► bot zarabia na siebie, skalujemy TYLKO jeśli live potwierdza paper
```

Każdy kamień milowy = 1–kilka sesji. **Dziś zaczynamy od M0.** Dlaczego M0 a nie
od razu deploy: jeśli silnik generuje sygnały, którym nie ufamy (a teraz tak
jest — patrz werdykt), to deploy = automatyzacja błędów. Najpierw prawda, potem
skala.

---

# 2. ZASADY (best practices — obowiązują ZAWSZE)

1. **backtest = live.** Sygnał i model kosztów są WSPÓLNE
   (`backtesting/costs.py` + klasy strategii). Paper bot i backtest nie mogą się
   rozjechać. To jest święte.
2. **Zero look-ahead.** Egzekucja po cenie następnego bara (next-bar-open).
   Nigdy nie decyduj na barze, którego jeszcze nie ma (feed dropuje otwarty bar).
3. **Waliduj out-of-sample.** Nic nie „działa" dopóki nie przeszło walk-forward.
   In-sample wyniki = zero wartości.
4. **Mierz wszystko.** Każda zmiana strategii/modelu → przelicz Sharpe, max DD,
   profit factor, fee drag PRZED i PO. Bez liczby = nie ma zmiany.
5. **Prod code, zero mocków.** Realne Binance, realne DynamoDB, realny Lambda.
   Wyjątki: `*.env.example` i dane syntetyczne w testach jednostkowych.
6. **Małe, odwracalne kroki.** Jeden fix = jeden commit z liczbą w opisie.
7. **Sekrety poza git.** Rotacja: patrz M6. Nigdy nie commituj kluczy.
8. **Branch teraz, PR na końcu.** `improvements/security-and-strategies`.
   PR dopiero gdy M0–M3 stabilne i CI zielone.
9. **Koszt > 0 jest wrogiem.** Każda transakcja i każdy zasób AWS kosztuje.
   Projektuj pod „1 user + cron dzienny", nie pod „always-on enterprise".

---

# 3. JAK TESTOWAĆ (strategia testów — co znaczy „happy from tests")

Trzy poziomy, każdy jest bramką (gate). Nie idziemy dalej dopóki poziom niżej
nie jest zielony.

### Poziom 1 — testy jednostkowe (szybkie, w CI na każdy push)
```bash
pytest app/backend/tests/test_backtesting.py \
       app/backend/tests/test_paper_trading.py -q   # muszą być ZIELONE
```
- `test_backtesting.py` — indykatory, brak look-ahead, koszty, metryki.
- `test_paper_trading.py` — **equivalence test**: paper == engine do 1e-6.
  To jest dowód backtest=live. Jeśli padnie → STOP, to najważniejszy test.
- Dodać: `test_fast_diagnostics.py` (legacy) + kontraktowy test API (SESJA B).

### Poziom 2 — walidacja strategii (walk-forward, out-of-sample)
```bash
python -m app.backend.backtesting.walkforward \
       --data 'data/ml/historical/*.csv' --timeframe 1d
```
- To jest bramka „czy strategia ma edge". Patrzymy na OOS Sharpe, DD, fee drag.
- Zmiana strategii/parametrów wchodzi TYLKO jeśli poprawia OOS, nie in-sample.

### Poziom 3 — paper trading na żywo (prawdziwy test)
- Bot lata co dzień, zapisuje realne decyzje + wirtualne P&L.
- **To jest ostateczny test.** Backtest może kłamać; żywy paper nie.
- ⚠️ ALE: żywy paper dowodzi rentowności dopiero gdy ZDĄŻY zebrać trejdy.
  Przy 1.69 round-tripa/rok 8 tygodni to za mało — patrz ROZDZIELENIE BRAMKI.

### PROGI „HAPPY" (kiedy uznajemy że działa — twarde liczby)
Progi rentowności (= **Bramka B** niżej). Niezmienione od 2026-07-25:

| Metryka | Próg |
|---|---|
| OOS Sharpe (walk-forward) | ≥ 1.0 |
| Max drawdown (paper, żywo) | ≤ 25% |
| Profit factor | ≥ 1.3 |
| Net P&L po kosztach (paper) | **> 0** (dodatni!) |
| Live tracking error vs paper | < 10% odchylenia P&L |
| Liczba transakcji / mies. | niska (fee drag < 20% zysku) |

Jeśli któryś próg nie spełniony → zostajemy na paper i szukamy edge (M4).
**Nie ma „prawie". Progi albo spełnione, albo nie.**

### PRE-REJESTRACJA oceny okna (ustalona 2026-07-25, PRZED pierwszą oceną)
> Narzędzie: `python -m app.backend.paper_trading.gate --source dynamodb`
> (PR #18; PSR/DSR/MinTRL wg Bailey & López de Prado, N=30 prób, var 0.3).
- **Reguła aktywności:** progi z tabeli oceniamy TYLKO przy ≥2 zamkniętych
  round-tripach ORAZ ≥10 dniach w pozycji. Inaczej werdykt =
  **INCONCLUSIVE_EXTEND** (okno FLAT w bessie = brak dowodów, nie porażka;
  EMA20/100 1d robi **1.69 round-tripa/rok** — zmierzone 2026-07-28, stara
  nota „~3.4/rok" liczyła nogi, nie round-tripy) → paper trwa dalej, re-ocena
  co 28 dni. NIE przechodzimy na realne pieniądze i NIE zmieniamy strategii.
- **Zakaz zmiany reguł w dniu oceny** — kryteria ustalone tu i teraz;
  zmiana po obejrzeniu wyników = fitting kryteriów do wyniku.

### ⚖️ ROZDZIELENIE BRAMKI (pre-rejestracja 2026-07-28, 44 dni PRZED oceną)

> **Dlaczego teraz i na jakiej podstawie.** Analiza mocy statystycznej na
> danych sprzed linii holdout (`< 2026-07-16`, zero podglądania wyniku okna
> M5) pokazała, że reguła aktywności jest praktycznie nieosiągalna w 8 tygodni:
>
> | długość okna | P(≥2 round-tripy ORAZ ≥10 dni w rynku) |
> |---|---|
> | 56 dni (8 tyg. — plan) | **1%** |
> | 112 dni (3.7 mies.) | 5% |
> | 168 dni (5.5 mies.) | 14% |
> | 252 dni (8.3 mies.) | 33% |
> | 365 dni (12 mies.) | 59% |
> | 547 dni (18 mies.) | **93%** |
>
> (n=3184 rolujących okien, 2017-09→2026-07-15; P(0 round-tripów w 56 dni)=74%.)
> Okno M5 startowało dodatkowo w pozycji FLAT, więc 1% to oszacowanie
> optymistyczne. **Wniosek: „8 tygodni" nigdy nie miało mocy, żeby cokolwiek
> rozstrzygnąć.** Dlatego rozdzielamy to, co okno DA SIĘ udowodnić, od tego,
> co wymaga czasu — ZANIM zobaczymy wynik.

**BRAMKA A — WIERNOŚĆ WYKONANIA** (rozstrzygalna w oknie 8-tyg.)
Dowodzi, że *maszyneria* jest prawdziwa: to, co bot robi na żywo, jest
dokładnie tym, co policzył backtest. Kryteria (wszystkie muszą przejść):
1. **Kompletność logu:** dokładnie 1 rekord na każdy zamknięty bar w oknie,
   zero luk, zero duplikatów per bar.
2. **Parytet sygnału:** dla każdego bara żywy `target` == target policzony
   przez `EmaCrossover(20,100)` na tych samych barach (dokładna równość).
3. **Parytet ceny:** żywy `price` == close bara z Binance (do 1e-6 względnie).
4. **Zero look-ahead na żywo:** `processed_at` > zamknięcie bara dla każdego
   rekordu; żaden otwarty bar nie został przetworzony.
5. **Parytet księgowości:** replay `PaperPortfolio` po logu decyzji odtwarza
   zapisane `equity`/`realized` do 1e-6.
6. **Ciągłość infrastruktury:** zero pominiętych dni cronu, zero wiadomości
   w DLQ, alarmy `errors`/`no-invocation` nie odpaliły.
- Wszystkie 6 liczone WYŁĄCZNIE z danych, które już zapisujemy → kryteria są
  implementowalne (tryb `gate.py --fidelity`, do dopisania).
- **Bramka A NIE odblokowuje realnych pieniędzy.** PASS znaczy tylko:
  „paper==backtest, infrastruktura nie kłamie". To zamyka M5.3.

**BRAMKA B — RENTOWNOŚĆ** (progi z tabeli wyżej, **BEZ ŻADNYCH ZMIAN**)
- Progi, reguła aktywności, DSR/MinTRL — **identyczne** jak w pre-rejestracji
  z 2026-07-25. Nic nie zostało poluzowane; zmienia się WYŁĄCZNIE oczekiwany
  horyzont: nie 8 tygodni, tylko tyle, ile zajmie zebranie ≥2 round-tripów
  (empirycznie: 12–18 miesięcy dla 60–93% szans).
- Re-ocena co 28 dni, werdykt `INCONCLUSIVE_EXTEND` do skutku.
- Wiersz „Live tracking error vs paper" z tabeli progów przechodzi do Bramki A
  (kryteria 2/3/5 — to ten sam pomiar, tylko rozstrzygalny bez trejdów).
  W `gate.py` pozostaje SKIPPED i nie blokuje Bramki B.
- **Tylko Bramka B otwiera M6.** Bramka A jest warunkiem koniecznym, nie
  wystarczającym.

**Konsekwencja, którą przyjmujemy świadomie:** M6 (realne pieniądze) jest
realnie odległe o ~12–18 miesięcy od startu okna, a nie o 8 tygodni. Jeśli
kiedyś uznamy ten horyzont za nie do przyjęcia, jedynym uczciwym wyjściem
jest **zmiana strategii na częściej handlującą** (i restart zegara) — NIE
poluzowanie progów. Ta decyzja należy do post-M5.

---

# 4. DANE HISTORYCZNE (fundament wszystkiego)

> **REGUŁA NADRZĘDNA (dyscyplina M5):** historyczna służy do BADAŃ i NARZĘDZI
> (skrypt bramki DSR/MinTRL, prototypy post-M5 na walk-forward), **NIGDY do
> dostrajania żywej strategii w oknie M5**. Przekręcanie parametrów na przeszłości
> = przeuczenie (in-sample backtest kłamie) + reset 8-tyg. zegara forward-testu.
> Powód, dla którego robimy paper forward, to właśnie to, że optymalizacja na
> historii jest niewiarygodna. Kandydaci ML → tylko purged walk-forward + embargo,
> promocja PO bramce i tylko jeśli biją czystą EMA (✅D9/✅D11,
> docs/ANALIZA_6_WARSTW_2026-07-17.md).

### Co mamy TERAZ (stan 2026-07-25 — komplet, ZWALIDOWANE)

| Plik (`data/ml/historical/`) | Interwał | Wierszy | Zakres | Rola |
|---|---|---|---|---|
| `BTCUSDT_1d.csv` | 1d | 3240 | 2017-09-01 → 2026-07-15 | główna strategia (EMA 20/100) |
| `ETHUSDT_1d.csv` | 1d | 3240 | 2017-09-01 → 2026-07-15 | 2. symbol (✅D10 marginalny) |
| `BTCUSDT_4h.csv` | 4h | 16513 | 2019-01-01 → 2026-07-15 | research |
| `BTCUSDT_1h.csv` | 1h | 77989 | 2017-08-17 → 2026-07-15 | research/ML (dociągnięty 2026-07-25) |

- **Czyste cięcie:** wszystkie pliki kończą się na barach **< 2026-07-16**
  (= linia holdout). UWAGA odkrycie 2026-07-25: stare końcówki 1d/4h z datą
  07-16 były NIEDOKOŃCZONYMI barami (pobrane w połowie dnia 16.07 — close 1d
  64700 vs prawdziwe 63830) i łamały regułę holdout → PRZYCIĘTE.
- **Walidacja integralności:** `python -m app.backend.backtesting.integrity
  data/ml/historical/*.csv` — zero twardych defektów (duplikaty/NaN/OHLC/
  monotoniczność); luki w 1h/4h = realne przerwy techniczne Binance
  (28 zdarzeń, ~128/78k barów, wszystkie ≤2023-03, spójne 1h↔4h), NIE fabrykujemy.
  Cross-check źródeł: 1h→resample→1d vs API-1d: 3240/3240 dni, 6 rozbieżnych
  barów (tylko luty 2018 — artefakt przesuniętej siatki po przerwie, patrz niżej).
- **Poza git:** dane wyrzucone z gita w `2c7e5a2` (Faza 2 — odchudzenie).
  Git = tylko KOD; dane regenerowalne na żądanie (komendy niżej).

### Źródła (dwa, do różnych zadań)

1. **API Binance — `app/backend/backtesting/download.py`** (czysty tool w repo).
   Paginuje `api.binance.com/api/v3/klines`, zapisuje CSV w układzie czytanym przez
   backtester. Dobre do 1d/4h i umiarkowanych zakresów. UWAGA: NIE dropuje
   otwartego bara — końcówkę pobraną w trakcie dnia zawsze przyciąć/zweryfikować
   (stąd wpadka z 07-16).
2. **Bulk dumpy Binance — `app/backend/backtesting/bulk_download.py`** (NOWY tool
   2026-07-25, nad `data.binance.vision` / repo `github.com/binance/binance-public-data`).
   Miesięczne+dzienne zipy, SHA-256 weryfikowane, obsługa pułapek formatu
   (µs timestampy od 2025, nagłówki w nowych plikach, bary spoza siatki po
   przerwie 2018-02 → floor na siatkę). Właściwe do MASOWEGO 1h/1m:
   ```bash
   python -m app.backend.backtesting.bulk_download --symbol BTCUSDT \
          --interval 1h --start 2017-08 --end 2026-07-15 \
          --out data/ml/historical/BTCUSDT_1h.csv
   ```
3. **Walidator — `app/backend/backtesting/integrity.py`** (NOWY 2026-07-25):
   twarde defekty (duplikaty/NaN/OHLC/monotoniczność/tz) = FAIL, luki = raport
   (realne przerwy giełdy; `--strict` gdy wymagamy ciągłości). 11 testów.

- **NIE używać do prep backtestu:** `scripts/fetch_fresh_historical_data.py` oraz
  `app/backend/scripts/ml/download_binance_3months.py` — legacy monolitu (90d 1m →
  DynamoDB cache, RSI/MACD), skazane wraz ze stackiem enterprise.

### ✅ ZROBIONE 2026-07-25: dane przygotowane (prerequisite spełniony)

1. ✅ **1h dociągnięty** — 77 989 barów 2017-08-17→2026-07-15, bulk z
   `data.binance.vision` (SHA-256 OK), zwalidowany + cross-check z 1d/4h.
2. ✅ **Holdout wyegzekwowany:** wszystkie pliki przycięte do `< 2026-07-16`
   (stare końcówki 07-16 były partial barami — naprawione).
3. ✅ **Walidacja integralności** — `integrity.py` w repo + w testach; wszystkie
   4 pliki przechodzą; luki = udokumentowane przerwy Binance.
4. (opcjonalnie, na żądanie researchu) więcej symboli/interwałów: ETH 4h/1h —
   `bulk_download.py` gotowy.

**Następny krok w kolejce:** ✅ skrypt bramki ZROBIONY (PR #18, patrz §3
PRE-REJESTRACJA). Dalej: projekt kill-switcha max-DD pod M6.

### Zasada rozdziału (holdout)

Dane do BACKTESTU/treningu i dane forward MUSZĄ być rozdzielone czasowo. Linia
podziału = **2026-07-16** (start M5). Nic z tej daty i późniejsze nie wchodzi do
dostrajania — inaczej model/parametry „widzą przyszłość".

---

# 5. TRENING MODELI (długi proces — wiele sesji, robimy MĄDRZE)

**Kontekst uczciwie:** mamy już 20 wytrenowanych modeli (`models/enterprise/`),
6 warstw. ALE nie udowodniliśmy, że ML bije prostą EMA. Dlatego trening jest
**gated na dowodach** — nie trenujemy „bo można", tylko gdy walk-forward pokaże
że warstwa realnie dokłada edge.

### Pipeline treningu (kolejność)
1. **Dane** → `data/ml/historical/` (sekcja 4), rozdzielone train/holdout.
2. **Feature engineering** → `scripts/ml/generate_feature_scalers.py` +
   indykatory z `backtesting/indicators.py` (spójne z runtime!).
3. **Trening warstw** → `scripts/ml/6layer_enterprise_trainer.py` i pochodne
   (`retrain_exit_layer3*.py`, `retrain_layer5_enhanced.py`,
   `train_short_lstm.py`). Każda warstwa osobno.
4. **Walidacja** → model NIE wchodzi do prod dopóki:
   - nie bije baseline (EMA) na holdout **out-of-sample**,
   - `n_features_in_` scalera == liczba cech w runtime (patrz bug L5!),
   - nie overfituje (train vs holdout gap rozsądny).
5. **Deploy modelu** → `models/enterprise/*.pkl,*.h5` (commitowane, <5MB).

### Kolejność warstw wg wartości (co trenować najpierw)
- **L1 regime** (bull/bear/range) — najprostszy, największy wpływ na filtr.
- **L5 confidence** — ale najpierw NAPRAW bug (scaler + wektor 15/6), inaczej
  trenujemy śmieci.
- **L2 LSTM ensemble** — najdroższy (1m data, GPU-hungry), najmniej pewny ROI.
  Trenować OSTATNI, tylko jeśli L1/L4/L5 jako filtr już dają edge.
- **L3 reversal, L4 filters, L6 timing** — pomiędzy.

### Uczciwa strategia ML (kluczowa decyzja projektowa)
> **ML jako FILTR nad zwalidowaną strategią, NIE jako samodzielny generator.**
> Strategia EMA generuje sygnał → warstwy ML mówią „bierz / odpuść / zmniejsz
> size". Tak ML może tylko poprawić (odsiać złe trejdy), a nie zepsuć od zera.
> To jest droga do edge, którą DA SIĘ zwalidować na walk-forward.

---

# 6. DEPLOY — NAJTANIEJ SERVERLESS (1 user = ja)

**Kluczowy insight:** obecny backend to App Runner *always-on* (~$5–25/mo za
24/7 kontener + WebSocket streaming). Dla **1 usera + strategii dziennej (1d)
NIE potrzebujesz always-on.** Potrzebujesz **jednej inwokacji dziennie**.

### Docelowa architektura (near-zero cost)
```
EventBridge (cron 1x/dzień)  ──►  Lambda: paper_trading/run step
                                      │  (pobiera bar, liczy sygnał, P&L)
                                      ▼
                                  DynamoDB (on-demand)  ← stan bota + trejdy
Frontend: S3 + CloudFront (statyczny Astro build)  ← dashboard read-only
```

### Koszt realny (1 user, cron dzienny)
| Zasób | Free tier | Realny koszt/mo |
|---|---|---|
| Lambda | 1M req + 400k GB-s | ~30 inwokacji → **$0** |
| DynamoDB on-demand | 25 GB + limity | garść zapisów → **~$0** |
| S3 + CloudFront | free tier | statyk → **~$0** |
| Route53 hosted zone | — | **$0.50** (jedyny realny koszt) |
| ACM cert (TLS) | darmowy | **$0** |
| **RAZEM** | | **~$0.50–2/mo** |

→ **Porzucamy App Runner** dla ścieżki bota. (Opcjonalny always-on backend z
live-dashboardem to osobna, droższa decyzja — nie na ścieżce krytycznej.)

### Head-start: gotowy modularny Terraform
`~/TradePulse_safety/terraform_modular/terraform/modules/` ma:
`api_lambda`, `eventbridge`, `dynamodb`, `lambda_layers`, `step_functions`,
`websocket_api`, `dns_acm`, `frontend_static_site`, `monitoring`, `ssm_params`.
→ **Adaptować, nie budować od zera.**

---

# 7. DROGA DO REALNYCH PIENIĘDZY (powoli, z bramkami)

Nigdy „na czuja". Twarde bramki:

- **Bramka 1 → paper:** M0–M3 zrobione, testy zielone, bot lata serverless.
- **Bramka 2 → dłuższy paper:** ≥8 tygodni żywego paper, wszystkie PROGI z sekcji
  3 spełnione (Sharpe ≥1, DD ≤25%, net P&L >0, live=paper).
- **Bramka 3 → mikro-realne:** $50–100 realne, na Binance z:
  - maker orders (niskie fee), stop-loss twardy, dzienny limit straty,
  - kill-switch (jeśli live odjeżdża od paper > próg → stop, wróć do paper),
  - te same `costs.py` co backtest (spójność).
- **Bramka 4 → skalowanie:** dokładać kapitał TYLKO jeśli live P&L przez kolejne
  tygodnie zgadza się z paper. Każde odchylenie = cofnij się o bramkę.

**Zarobek na paper vs live:** paper P&L to dowód konceptu; live P&L (nawet na
$50) to dowód że model kosztów i egzekucja są realne. Dopiero live P&L > koszty
= „bot zarabia na siebie" = cel minimum osiągnięty.

---

# PUNKTY DECYZYJNE (❓ — analiza gdy DOJDZIEMY, nie z góry)

Otwarte pytania są OK. Nie rozstrzygamy ich teraz — każde ma przypisany kamień
milowy. Gdy praca dojdzie do danego punktu: **robimy analizę na świeżych danych
i wtedy odpowiadamy**. To index, żeby żadna decyzja się nie zgubiła.

| # | Milestone | Otwarte pytanie |
|---|---|---|
| ❓D1 | M0/A5 | Emergency mode: dopisać realny performance-trigger (win-rate) czy skreślić obietnicę z NAPRAWA.md? |
| ❓D2 | M0/A6 | Brain vs Engine: rozdzielić świadomie (monitor + exec) czy scalić w jedno? |
| ❓D3 | M3/B6 | `/api/ai/confidence`: dodać endpoint w backendzie czy usunąć z UI? |
| ❓D4 | M3/B7 | Martwa warstwa `lib/api/*.ts` (`/api/v1/*`): usunąć czy dorobić aliasy w backendzie? |
| ❓D5 | M3/B8 | Niezarejestrowane routery (`showcase/performance/audit/communications`): zarejestrować czy usunąć? |
| ❓D6 | M3/C6 | Martwe pliki `logger.ts`/`token-utils.ts`: podłączyć czy usunąć? |
| ✅D7 | M2 | ROZSTRZYGNIĘTE 2026-07-16: read-only status Lambda z publicznym function URL (HTML+JSON, ~$0). Always-on backend NIE — decyzja o pełnym froncie na domenie = osobno (hosting + koszt backendu). |
| ❓D8 | M2/E5 | `api.` CNAME: dodać App Runner domain association czy usunąć rekord? |
| ✅D9 | M4/F1 | ROZSTRZYGNIĘTE 2026-07-16: **czysta EMA**. Modele enterprise = intraday horizon (mismatch dla 1d); proste filtry reżimowe niestabilne między okresami. Szczegóły: docs/M4_EDGE_VALIDATION.md |
| ✅D10 | M4/F3 | ROZSTRZYGNIĘTE 2026-07-16: **tylko BTC 1d** (ETH 1d marginalne 1.01 vs 0.96; 4h gorsze). Wrócić po bramce 8-tyg. paper. |
| ✅D11 | M4/F4 | ROZSTRZYGNIĘTE 2026-07-17 (deep-audit, docs/ANALIZA_6_WARSTW_2026-07-17.md): **żadnej istniejącej warstwy nie retrenować** — etykiety cyrkularne, splity przeciekowe, bug jednostek w L1/L3/L4/L6. Jeśli ML wróci po M5 → JEDEN meta-labeler nad EMA (cechy 1d, target „czy sygnał EMA zarobi", purged walk-forward + embargo) + HMM regime jako cecha; promocja tylko jeśli bije czystą EMA na harnessie M4. |
| ❓D12 | M6/F7 | Realne pieniądze: kwota startowa, broker, typ zleceń (maker), limity — gdy przejdziemy bramkę 8-tyg. paper. |

---

# ROADMAP SZCZEGÓŁOWA (checklista — TU pracujemy)

## ▶ M0 — Zaufanie do rdzenia (SESJA A)  🔴 ZACZNIJ TU
Cel: silnik nie kłamie, sygnały wiarygodne, testy zielone.
- [x] **A1. DI container** — `core/container.py:23,73` wykrywa fabryki przez
      `callable(x) and not hasattr(x,"__dict__")` → zawsze puste `_factories`,
      `get()` zwraca niewywołaną lambdę. Fix: `register_factory` vs
      `register_instance`, wołać fabrykę w `get()`.
- [x] **A2. Jeden startup** — `application.py:21` importuje lifespan, `:57-58`
      tworzy `FastAPI()` BEZ `lifespan=`, `:87` `on_event("startup")`;
      `singleton_app.py:363` = DRUGI startup → modele 2×. Wybierz jeden, usuń
      martwy `lifespan.py`/`bootstrap.py`, zabij dubel (`singleton_app.py:220`).
- [x] **A3. L5 scaler + wektor** — `enterprise_trading_engine.py:~402` pomija
      scaler; wektor 15 cech (`ml/infer.py:147`) vs 6 (`:118`). Włącz scaler,
      jeden kształt, zweryfikuj `n_features_in_`.
- [x] **A4. Clamp 0.05** — `utils/model_io.py:89` podłoguje predykcje. Zdejmij /
      zastąp kalibracją.
- [x] **A5. Emergency mode** — obiecany w NAPRAWA.md trigger win-rate nie
      istnieje. Zaimplementuj realny performance-trigger ALBO skreśl z docs.
- [x] **A6. Brain vs Engine** — `brain_controller._generate_unified_signal`
      zwraca None (`:612`); realny sygnał w `day_trading_engine.py:972`.
      Nazwij świadomie (monitor vs exec) albo scal.
- [x] **A7. Test startu/DI** — test łapiący zepsute DI + dubel startup.
- **Done gdy:** backend startuje raz, DI zwraca instancje, L5 na scaled features,
  brak clamp 0.05, `pytest` zielony.

## ▶ M1 — Paper bot na żywo (część A/D już zrobiona)
Cel: zwalidowana strategia EMA lata co dzień, zapisuje decyzje + P&L.
- [x] **M1.1** Uruchom `python -m app.backend.paper_trading.run step` na realnych
      danych, potwierdź idempotencję (2× ten sam bar = brak dubla).
- [x] **M1.2** Potwierdź equivalence test zielony (paper==engine).
- [x] **M1.3** Cron lokalny (`scripts/run_paper_bot.sh`) jako tymczasowy most do
      czasu M2 (serverless).
- [x] **M1.4** Zdefiniuj co dokładnie logujemy (decyzja, cena, size, P&L, koszty)
      — to będą dane do PROGÓW z sekcji 3.

## ▶ M2 — Serverless deploy (SESJA E)  🟢 near-zero cost
- [x] **E1. DynamoDB naming** — `production.env` prefix `tradepulse_` vs tabele
      bez prefiksu w TF (`runtime`, `live_candles`...). Zsynchronizuj
      env↔kod↔`infra/dynamodb*.tf`.
- [x] **E2. DynamoDB Local TTL fix** — `core/database.py` wysyła
      `TimeToLiveSpecification` w `CreateTable` (DynamoDB Local nie zna) → osobny
      `UpdateTimeToLive`. Działa lokalnie i na AWS.
- [x] **E3. Adaptuj modularny TF** z archiwum do `infra/` (Lambda+EventBridge+
      DynamoDB on-demand + S3/CloudFront). Porzuć App Runner na ścieżce bota.
- [x] **E4. Lambda handler** — `paper_trading/run step`, EventBridge cron 1×/dzień,
      stan w DynamoDB (nie plik JSON).
- [x] **E5. `api.` CNAME/TLS** — `main.tf backend_alias` bez domain association →
      TLS mismatch. Dodaj association albo usuń rekord.
- [x] **E6. Smoke-test tabel** po deployu + CloudWatch alarm na błąd Lambdy.
- **Done gdy:** bot lata w chmurze bez laptopa, koszt < $2/mo, alarm działa.

## ▶ M3 — Aplikacja spójna E2E (SESJA B + C)  🟠
### B — Integracja API (front↔backend 404)
- [x] **B1. real_trading** — front `/api/real-trading/` vs backend
      `/api/real_trading/` (`OpenPositionsManager.tsx`, `WalletManagement.tsx`).
- [x] **B2. Komunikaty** — `/api/communication/` vs `/api/admin/communications/`.
- [x] **B3. Analityka** — `/api/user-analytics/` vs `/api/analytics/admin/`.
- [x] **B4. AI models** — `/api/admin/ai/models` vs `/api/admin/ai-models`.
- [x] **B5. System actions** — `/api/system/action` vs `/system/maintenance`.
- [x] **B6. AI confidence** — `/api/ai/confidence` nie istnieje. Dodaj/usuń.
- [x] **B7. Martwa warstwa `lib/api/*.ts`** (`/api/v1/*`) — usuń/aliasuj.
- [x] **B8. Niezarejestrowane routery** (`showcase/performance/audit_compliance/
      communications`) — zarejestruj lub usuń.
- [x] **B9. Kontraktowy test CI** — OpenAPI backendu vs ścieżki frontendu.
### C — Frontend security + E2E
- [x] **C1. Admin bez ochrony** — `pages/admin/dashboard.astro:20 isAdmin=true`
      + `prerender=true`. Realny auth, wyłącz prerender dla chronionych.
- [x] **C2. `enterprise_admin_token` w 7 plikach** → token z sesji.
- [x] **C3. Klucz tokenu `'token'` vs `'auth_token'`** — ujednolić.
- [x] **C4. `user_dashboard/index.astro:23`** zawsze rzuca (null) — realne dane.
- [x] **C5. Dwa prod-URL-e** (`lib/config.ts:14` vs `environments.ts:150`) — jedno.
- [x] **C6. Martwe pliki** `logger.ts`, `token-utils.ts` — podłącz/usuń.
- **Done gdy:** admin chroniony, zero 404 w UI, jeden klient API, dashboard żyje.

## ▶ M3b — Odchudzenie / Faza 2 (SESJA D)  🟡 (może iść równolegle)
- [ ] **D1. Persistence 3×** → jeden (`enhanced_market_persistence` +
      `market_data_persistence` + `market_data_persistence_service`).
- [ ] **D2. Emergency 2×** → jeden.
- [x] **D3. Ciche `except Exception`** (L5 `:1509,1514`, L4 `:1429` → 0.3/0.5)
      → loguj/podnoś krytyczne.
- [ ] **D4. Legacy testy** `test_fast_diagnostics.py` — napraw/oznacz.
- [ ] **D5. Usuń „TEMPORARILY SKIP VALIDATION"** (`lifespan.py:76-83`).

## ▶ M4 — Więcej edge: ML jako filtr (SESJA F, część 1)
- [x] **F1. ML filtr nad EMA** — 6-warstwowy mózg jako filtr confidence nad
      strategią EMA (nie generator). Zmierz walk-forward: podnosi Sharpe /
      obniża DD? Jeśli TAK → zostaje. Jeśli NIE → zostajemy przy czystej EMA.
- [x] **F2. Sizing** — volatility targeting (większy size gdy edge silny).
- [x] **F3. Więcej rynków/timeframe** — sprawdź czy edge się przenosi (ETH? 4h?).
- [ ] **F4. Trening modeli** (sekcja 5) — TYLKO warstwy, które F1 pokazał że
      dokładają edge. Kolejność: L1 → (napraw L5) → reszta → L2 LSTM ostatnie.
- **Done gdy:** mamy udowodniony na OOS edge lepszy niż czysta EMA, albo świadomą
  decyzję że zostajemy przy EMA.

## ▶ M5 — 8+ tygodni paper (bramka do realnych pieniędzy)
> **🕐 ZEGAR M5 WYSTARTOWAŁ: 2026-07-16** (pierwszy bar przetworzony w chmurze:
> 2026-07-15, zapis w DynamoDB `tradepulse_paper_bot`). Minimum 8 tygodni →
> **ocena progów NIE WCZEŚNIEJ niż 2026-09-10**. Do tego czasu: NIE zmieniać
> strategii/parametrów (unieważnia pomiar!), bot działa sam (cron 00:10 UTC).
> Po drodze: ~2026-09-29 wygasa domena tradepulseai.co.uk (decyzja o odnowieniu).
- [ ] **M5.1** Zbieraj żywe metryki ≥8 tygodni (start 2026-07-16, koniec ≥2026-09-10).
- [ ] **M5.2** BRAMKA B (rentowność) — progi z sekcji 3. Raport.
      ⚠️ Oczekiwany werdykt 2026-09-10: `INCONCLUSIVE_EXTEND` (P(rozstrzygalna
      w 56 dni) = 1%). Re-ocena co 28 dni; realny horyzont 12–18 mies.
- [ ] **M5.3** BRAMKA A (wierność wykonania) — 6 kryteriów z sekcji 3.
      TO jest rozstrzygalne 2026-09-10 i to jest realny dorobek okna.
- [ ] **M5.4** Zaimplementuj `gate.py --fidelity` (Bramka A) — musi być gotowe
      i przetestowane PRZED 2026-09-10.

## ▶ M6 — Małe realne kwoty + PR (SESJA F, część 2)
- [ ] **F5. Rotacja sekretów** (user): AWS key, Binance key, SECRET_KEY.
- [ ] **F6. PR** — dopiero gdy M0–M3 stabilne, CI zielone.
- [ ] **F7. Realne $50–100** — maker orders, stop-loss, dzienny limit straty,
      kill-switch (live≠paper → stop). Bramka 3 z sekcji 7.
- [ ] **F8. Skalowanie** — tylko jeśli live potwierdza paper. Powoli.

---

# Zwalidowany edge (przypomnienie — bądź uczciwy)
Walk-forward, OOS, BTCUSDT, realne koszty:
- Naive long/short (EMA/RSI/regime) → ❌ przegrywa z buy&hold w każdym reżimie.
- Krótkie TF (15m) → ❌ zabite przez fee (+146% fee drag).
- **Long-only EMA trend-following (1d) → ✅ edge potwierdzony.**
  Redukuje DD (−49% vs −77%), bije risk-adjusted; NIE bije absolutnego zwrotu.

**Liczby dla TEGO, CO LATA NA ŻYWO** (stałe EMA20/100, zmierzone 2026-07-28 —
wcześniej raportowaliśmy tylko wariant przestrajany co fold, patrz niżej):

| layout foldów | adaptive (przestrajany) | **stałe 20/100 = prod** | Buy&Hold |
|---|---|---|---|
| 730/180 | 1.11 | **1.01** | 0.87 |
| 500/125 | 1.14 | **1.00** | 0.97 |
| 1000/250 | 1.12 | **1.14** | 1.00 |
| 365/90 | 1.18 | **1.02** | 0.81 |

- Stałe 20/100 bije B&H w KAŻDYM layoucie → konfiguracja produkcyjna obroniona.
- ⚠️ Optymalizator walk-forward NIGDY nie wybrał 20/100 (0/73 foldów — zawsze
  10/50). Liczby „1.11–1.18" należą do strategii przestrajanej, nie do prod.
- Edge siedzi w RODZINIE, nie w liczbach: 42 stałe kombinacje dają OOS Sharpe
  0.65–1.17 (mediana 0.99) przy B&H 0.87. 20/100 = 16/42, środek plateau.
  In-sample 20/100 jest 30/47 → **nie jest cherry-pickiem** (przeuczony parametr
  siedziałby na szczycie in-sample).
- Koszty: przeżywa 0.5%/stronę (Sharpe 0.96). Reżimy: chroni w bessie
  (2021-22 +15% vs B&H −44%; 2025-26 −3% vs B&H −32%), przegrywa w hossie.
- **Częstotliwość: 15 round-tripów przez 8.9 roku = 1.69/rok, 51% czasu
  w rynku.** To jest twarde ograniczenie mocy statystycznej bramki — patrz §3.
- Reprodukcja: `python scripts/research/calibration_audit.py`.
  Pełny raport: docs/ANALIZA_KALIBRACJI_2026-07-28.md.

---

# Stan faktyczny (werdykt 2026-07-15)
Dwa systemy: ✅ zdrowy nowy rdzeń (`backtesting/`+`paper_trading/`, 12 testów,
backtest=live) i ⚠️ stary „enterprise" 6-layer + demo-frontend (wstaje i żyje,
ale inteligencja częściowo zneutralizowana + integracja dziurawa). Backend
POTWIERDZONY na żywo: `/health` healthy, mózg liczy L1..L6, Binance streamuje,
frontend się builduje. Problem = wykonanie, nie koncept.

---

# Log sesji (dopisuj 1 linię na końcu każdej)
- 2026-07-15 — Deep-review (3 agenty) + test na żywo + napisany ten master plan.
  Werdykt: koncept OK, wykonanie kruche. **Następny krok: M0 / SESJA A1 (DI
  container)** — to odblokowuje najwięcej i jest warunkiem zaufania do sygnałów.
- 2026-07-16 (sesja nocna, autonomiczna) — M0 CAŁY (A1–A7: DI container,
  jeden startup, L5 training-parity + scaler, clamp off, PERFORMANCE breaker,
  brain/engine split świadomy, testy DI/startup), M1 (decision log, state
  store local/DynamoDB, lambda_handler), M2 DEPLOYED (infra-serverless/:
  Lambda+DynamoDB+Scheduler 00:10 UTC+alarm SNS; smoke-test w chmurze OK,
  idempotencja E2E), M3 (wszystkie B1–B9 + C1–C6: zero 404, guard admina,
  jeden klucz tokenu, kontrakt API w testach, martwe pliki out). Odkrycia:
  konto AWS było puste (App Runner dawno zburzony); 9665f59 cofnął fixy
  596d277 (przywrócone); L5 karmiony złymi jednostkami (naprawione
  ml/l5_features.py). Decyzje: D1=zaimplementowany breaker, D2=split,
  D4/D5/D6=delete, D3=allowlist (mock, czeka na endpoint). 45 testów
  zielonych. Deploy workflows → manual-only (infra nie istnieje). Security:
  gitleaks nigdy nie działał (zepsuty TOML) — naprawiony; 421 szumu z 2
  bezsensownych reguł usunięte; 27 historycznych findingów zbaselinowane
  (zgoda usera); wyciekły AKTYWNY klucz AWS (user Kris) ZROTOWANY (nowy w
  ~/tradepulse_new_aws_key.json — podmień i skasuj plik; stary Inactive).
  PR #2 ZMERGOWANY do main.
- 2026-07-17 — Health-check produkcji: scheduler ENABLED, Lambda 00:10 UTC
  czysta, decyzje 15/16.07 w DynamoDB, SNS potwierdzony, logi bez błędów.
  Deep-audit 6 warstw (4 agenty, raport: docs/ANALIZA_6_WARSTW_2026-07-17.md):
  system enterprise NIE działa uczciwie e2e — etykiety cyrkularne (5/6 warstw),
  splity przeciekowe, LSTM AUC 0.519 karmiony 200× powieloną świecą, trailing
  stop w exit ODŁĄCZONY (bug merge słownika IEE:606), próg SL≈0 (podwójne
  dzielenie ATR), finalna pewność entry ignoruje warstwy (:2546), bug jednostek
  L5 żyje w L1/L3/L4/L6. Werdykt: nie naprawiać — po M5 ewentualnie meta-labeling
  nad EMA (1 model, cechy 1d, purged walk-forward) + HMM regime jako cecha.
  ❓D11 de facto rozstrzygnięte: ŻADNEJ istniejącej warstwy nie retrenować.
  Audyt brain (docs/ANALIZA_BRAIN_2026-07-17.md): fasada — realny cykl to ~50
  linii logowania statusu w 1300 liniach ceremonii; pipeline 7-krokowy martwy,
  io/ osierocone (0 importerów), eventy ceremonialne; stany HALT/ERROR bez
  wyjścia. Do zachowania: BrainStateStore (bug zapisu NAPRAWIONY — patrz
  wpis 2026-07-17 cd., PR #15),
  modele Pydantic decyzji, koncept FSM, schemat audytu. Reszta do kasacji po M5.
  Status: CZEKAMY — okno M5 biegnie, oceny bramek ≥2026-09-10.
- 2026-07-17 (cd.) — Fix BrainStateStore (jedyny „brainowy" kod używany dziś
  i wart zachowania): P1 zapis env-aware zamiast hardcoded local DynamoDB,
  P2 cache mutowany dopiero PO udanym zapisie DB, P3 tz-aware timestampy.
  +3 testy kontraktowe, cały suite 48 zielonych. **PR #15 ZMERGOWANY do main**
  (CI zielone: pytest + gitleaks), branch skasowany. Żywy bot/M5 nietknięte.
- 2026-07-16 (sesja dzienna) — M4 CAŁE zamknięte decyzjami na danych (PR #4,
  docs/M4_EDGE_VALIDATION.md): EMA robust (Sharpe 1.11-1.18 każdy fold, edge
  przeżywa 0.3% fee), sizing NIE, ETH/4h NIE, ML-filtr NIE (mismatch horyzontu).
  E2E test brain+engine na modelach: 7 faz OK, L5 scaler aktywny, sygnał
  6-warstwowy na żywo (HOLD 63.6%), metryka candles_parity=100%. Frontend
  audyt + naprawa (PR #5): user_dashboard/portfolio na realnych danych,
  landing z prawdziwymi metrykami, ~16 mocków usuniętych. Auth: użytkownicy
  do DynamoDB (przeżywają restart), admin z env, kredki wyjęte ze źródeł.
  ✅D7: status-Lambda z publicznym URL (fix podwójnej permisji AWS X/2025,
  PR #6). Domena tradepulseai.co.uk wykupiona, strefa DNS do odtworzenia.
- 2026-07-21 — Deep-audit E2E żywej ścieżki (4 agenty) → docs/ANALIZA_E2E_2026-07-21.md.
  Rdzeń solidny (parytet sygnał+koszty realny, brak lookahead, idempotencja,
  zip prod = repo wg hash). Fixy PR #12–15 zweryfikowane: P1/P2/P3 FIXED.
  Do zrobienia (M5-safe): H1 dashboard MTM equity, M1 cichy log decyzji
  (zweryfikować kompletność w DDB przed bramką!), M2 heartbeat alarm + DLQ,
  M3 guard min-history, kwarantanna enterprise NADAL niewykonana w monolicie,
  tfstate→S3, pin requests + CI smoke paczki, DSR/MinTRL + 1h + kill-switch
  wciąż otwarte. Domena wygasa 2026-09-29 — odnowić PRZED bramką 2026-09-10.
  Żywy bot nietknięty; health-check 2026-07-21 00:10 UTC zielony (FLAT, $10k).
- 2026-07-21 (cd.) — Fixy top-4 z audytu E2E na branchu fix/m5-safe-hardening →
  **PR #16**: (1) dashboard equity mark-to-market (ta sama księgowość
  PaperPortfolio co bot), (2) log decyzji nośny — rekord w stanie atomowo
  z last_bar, append głośny (→ alarm), samo-naprawa luki na ścieżce skipped,
  (3) heartbeat alarm Invocations<1/25h + DLQ schedulera + alarm DLQ,
  (4) guard min-history w feedzie. Pierwsze testy PaperBot.step (23/23
  zielone), terraform validate OK, smoke lokalnego step OK. Strategia
  NIETKNIĘTA (M5 respektowane). Po merge: rebuild zip + terraform apply.
- 2026-07-22 — Deploy + planning (bez kodu strategii). (1) DEPLOY domknięty:
  PR #16 był zmergowany (0b2077e) ale NIEzdeployowany — prod stał na kodzie
  16.07. Sync main, rebuild zip (hash Uxz09Wt→r8Luxno), `terraform apply`
  (4 add/3 change/0 destroy). Zweryfikowane NA ŻYWO: obie Lambdy CodeSha256=
  r8Luxno...tNq0= (prod=repo), heartbeat alarm+DLQ istnieją (alarm przeszedł do
  OK, mail SNS dotarł — potwierdzenie że alerty działają e2e), dashboard renderuje
  MTM equity $10k FLAT. tfstate zbackupowany → ~/TradePulse_safety/tfstate-backups.
  (2) Domena: reminder macOS na 2026-08-24 (odnowienie = akcja u rejestratora).
  (3) Weryfikacja danych Binance: cena bota = Binance co do grosza (07-21 close
  66556.16), log decyzji bez luk 07-15→07-21, świeca otwarta słusznie pomijana,
  guard M3 aktywny. (4) PLANOWANIE danych: rozbudowana §4 DANE HISTORYCZNE —
  inwentarz (1d/4h mamy, 1h BRAK), źródła (data.binance.vision/github binance-public-data
  = „ten z GitHuba" + in-repo download.py), reguła holdout 2026-07-16 i zakaz
  dostrajania w oknie M5. **NASTĘPNA SESJA zaczyna pracę od przygotowania danych:
  dociągnąć 1h + walidacja integralności, POTEM skrypt bramki DSR/MinTRL.**
  Niezacommitowane: plan.md + docs/ANALIZA_*.md (czekają na decyzję o commicie).
- 2026-07-25 — DANE HISTORYCZNE ZROBIONE (branch feat/historical-data-prep,
  commit 40b8ab4, wypchnięty). Health-check M5: zielony, log decyzji 07-15→07-24
  bez luk, FLAT $10k (0 trejdów — EMA gap −5.3%, ostatni long 2026-05-28; do
  crossu potrzeba BTC ~70k utrzymane ~2 tyg.; historycznie FLAT to 53% czasu,
  mediana 70 dni — zachowanie poprawne). Nowe tooling: bulk_download.py
  (data.binance.vision, SHA-256, µs-timestampy, floor barów spoza siatki po
  przerwie 2018-02), integrity.py (twarde defekty vs raportowane luki), fix
  ISO8601 w data.py, 11 testów (suite 66 zielonych). 1h dociągnięty: 77 989
  barów 2017-08-17→2026-07-15. ODKRYCIE: końcówki 1d/4h z datą 07-16 były
  PARTIAL barami (pobrane w połowie dnia; close 1d 64700 vs realne 63830) i
  łamały holdout → wszystkie pliki przycięte do <2026-07-16, backup w
  scratchpadzie sesji. Cross-check źródeł: 1h→1d = 3240/3240 dni zgodnych
  (6 barów z lutego 2018 = artefakt siatki, udokumentowany w toolu);
  1h→4h = 1/16513 rozbieżny. Luki 1h: 28 zdarzeń ~128 barów, wszystkie =
  realne przerwy Binance, spójne z 4h. NASTĘPNY KROK: skrypt bramki DSR/MinTRL
  + PRE-REJESTRACJA kryterium min. liczby transakcji przed oceną 09-10.
- 2026-07-25 (cd.) — SKRYPT BRAMKI M5 ZROBIONY (branch feat/m5-gate-script,
  commit e6fdfc1 → **PR #18**; osobny od PR #17 z danymi). gate.py: pełny log
  decyzji z DynamoDB (read-only, paginowane query) lub lokalny JSONL → progi
  §3 + PSR/DSR/MinTRL (Bailey & López de Prado, bez scipy). PRE-REJESTRACJA
  w §3: najwcz. ocena 2026-09-10; reguła aktywności ≥2 round-tripy AND ≥10 dni
  w pozycji, inaczej INCONCLUSIVE_EXTEND z re-oceną co 28 dni (0 trejdów w
  bessie = brak dowodów, nie FAIL); DSR deflowany N=30/var 0.3; MinTRL@95%.
  Zweryfikowane na prod: dzień 9, FLAT → WINDOW_RUNNING (47 dni do oceny);
  symulacja --as-of 2026-09-10 przy 0 trejdów → INCONCLUSIVE_EXTEND. 18 testów
  (matematyka + precedencja werdyktów), suite 84 zielone. Analiza sygnału przy
  okazji: BUY wymaga EMA20>EMA100 — dziś gap −5.3%, potrzeba BTC ~70k przez
  ~2 tyg. (cross „jutro" wymagałby 111k); FLAT od 2026-05-28 = 57 dni, mediana
  historyczna FLAT 70 dni — norma. OTWARTE PR-y: #17 (dane), #18 (bramka).
- 2026-07-25 (cd.2) — PROJEKT KILL-SWITCHA M6 (branch docs/kill-switch-design
  → **PR #19**, dokument docs/KILL_SWITCH_DESIGN_2026-07-25.md). Ewidencja
  z silnika na zwalidowanych danych: max DD strategii −64.3% (2018, 1066 dni
  underwater), 4 epizody >25%/9 lat, worst day −19.5% ⇒ kill @25% = detektor
  złamania koperty bramki, NIE ochrona kapitału. Triggery: T1 maxDD>25% od
  szczytu M6, T2 rozjazd live/paper>10%, T3 strata dzienna>15%; fail-closed;
  rearm tylko manualny z auditem; zero nowych zasobów AWS; plan testów w doc;
  świadomie BEZ vol targetingu (F2). NIE wdrażać w M5. Otwarta konsekwencja
  dla Bramki 4/❓D12: pełnocyklowe DD strategii >> 25% — próg lub ekspozycję
  trzeba zrewidować przy skalowaniu. SESJA ZAKOŃCZONA: 3 otwarte PR-y
  #17/#18/#19 (CI zielone na #17/#18), suite 84 testów zielonych, M5 dzień 9,
  bot FLAT $10k zdrowy. NASTĘPNA SESJA: merge PR-ów (decyzja usera), potem
  TRYB CZEKANIA (health-check na żądanie); ewentualne porządki: kwarantanna
  enterprise w monolicie, tfstate→S3. Bramka: ≥2026-09-10 (gate.py gotowy).
  Domena: odnowić przed 09-10 (reminder 08-24).
- 2026-07-28 — AUDYT KALIBRACJI (branch docs/calibration-audit-and-gate-split,
  docs/ANALIZA_KALIBRACJI_2026-07-28.md + scripts/research/calibration_audit.py).
  Health-check prod: scheduler ENABLED, obie Lambdy r8Luxno…tNq0=, 3 alarmy OK,
  log decyzji 07-15→07-27 BEZ LUK (13 rekordów), status URL 200, FLAT $10k,
  gate.py = WINDOW_RUNNING dzień 12. Lokalny main był 6 commitów za origin
  (PR #17/#18/#19 dawno zmergowane) — dociągnięty.
  **ODKRYCIE 1:** walk-forward z M4 przestraja parametry co fold i NIGDY nie
  wybrał 20/100 (0/73 foldów, zawsze 10/50) — publikowane 1.11–1.18 nie
  dotyczyło produkcji. Zmierzone stałe 20/100: OOS 1.00/1.01/1.02/1.14, bije
  B&H (0.81–1.00) w KAŻDYM layoucie → prod obroniony. Brak przeuczenia:
  ranga OOS 16/42, in-sample 28/42 (przeuczony byłby na szczycie in-sample);
  rodzina 42 kombinacji daje 0.65–1.17 przy B&H 0.87 → edge jest własnością
  podejścia, nie liczb. Fee: przeżywa 0.5%/stronę (Sharpe 0.96).
  **ODKRYCIE 2 (krytyczne):** strategia robi 1.69 round-tripa/rok, 51% czasu
  w rynku → P(reguła aktywności spełniona w 56 dni) = **1%** (P(0 trejdów)=74%);
  59% przy 12 mies., 93% przy 18 mies. Okno 8-tyg. NIGDY nie miało mocy na
  rozstrzygnięcie rentowności. → BRAMKA ROZDZIELONA w §3 (pre-rejestracja
  44 dni przed oceną, na danych sprzed holdoutu): A = wierność wykonania
  (6 kryteriów, rozstrzygalna 09-10, NIE odblokowuje pieniędzy),
  B = rentowność (progi BEZ ZMIAN, horyzont 12–18 mies., tylko ona otwiera M6).
  Żaden próg nie poluzowany. **ODKRYCIE 3:** build Lambdy instalował `requests`
  bez wersji (prod 2.34.2 vs requirements 2.31.0) → requirements-lambda.txt
  z dokładnymi pinami (rozwiązują się DOKŁADNIE do zestawu z prod, redeploy
  zbędny) + test_lambda_package.py. Dryf prod↔repo funkcjonalnie zerowy
  (bot nie importuje data.py). Zero ML na prodzie potwierdzone. Poprawione
  nieaktualne zapisy planu (fee >0.3%, „3.4 trejdy/rok", PR-y do zmergowania).
  Suite 95 testów zielonych. NASTĘPNY KROK: `gate.py --fidelity` (M5.4).
