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
- **Milestone:** M0 ✅ + M1 ✅ + M2 ✅ (bot LATA w chmurze!) + M3 w toku.
- **NASTĘPNA AKCJA:** M5 — bot zbiera ≥8 tyg. żywych decyzji. Otwarta decyzja:
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
  buy&hold *risk-adjusted* (Sharpe 1.27 vs 1.12), ale **NIE bije** absolutnego
  zwrotu i **umiera powyżej ~0.3% fee**.
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
- **To jest ostateczny test.** Backtest może kłamać; 8 tygodni żywego paper nie.

### PROGI „HAPPY" (kiedy uznajemy że działa — twarde liczby)
Zanim dotkniemy realnych pieniędzy, na ≥8 tygodni paper MUSI być:

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

---

# 4. DANE HISTORYCZNE (fundament wszystkiego)

- **Skąd:** Binance public API (za darmo), regeneracja skryptem:
  ```bash
  python -m app.backend.backtesting.download --interval 1d \
         --start 2020-01-01 --out data/ml/historical/BTCUSDT_1d.csv
  ```
- **Co pobrać:** 1d (główna strategia), 1h/4h (potem, do ML), 1m (tylko jeśli
  potrzebne do treningu LSTM — ciężkie, ~556MB).
- **Gdzie trzymać:** `data/ml/historical/` — **poza git** (gitignored,
  regenerowalne na żądanie). Git trzyma tylko KOD, nie dane.
- **Jakość:** sprawdzaj luki (missing bars), duplikaty, splity czasu. Zły data
  = zły backtest = złe decyzje. Data quality to nie formalność.
- **Zasada:** dane do TRENINGU i dane do BACKTESTU muszą być rozdzielone czasowo
  (holdout), inaczej model „widzi przyszłość".

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
| ❓D11 | M4/F4 | Które warstwy ML trenować (koszt vs ROI): gated na tym, co pokaże ❓D9. |
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
- [ ] **M5.2** Sprawdź wszystkie PROGI (sekcja 3). Raport.
- [ ] **M5.3** Live tracking: paper == to co byłoby realnie (< 10% odchylenia).

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
- **Long-only EMA trend-following (1d) → ✅ Sharpe 1.27 vs 1.12, DD −50% vs −77%.**
  Redukuje DD, bije risk-adjusted; NIE bije absolutnego zwrotu; umiera >0.3% fee.

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
