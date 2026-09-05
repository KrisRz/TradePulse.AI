# TradePulse.AI — MASTER PLAN (definitywny, wieloseryjny)

> **Po co to jest:** żeby „jutrzejszy ja / future Claude" po otwarciu tego pliku
> wiedział DOKŁADNIE gdzie jesteśmy, gdzie zaczynamy dziś i dokąd zmierzamy.
> To jest jedyne źródło prawdy o pracy.
> **UWAGA (sprostowanie 2026-08-05):** ten plik JEST śledzony przez git i był
> commitowany w poprzednich sesjach (np. 0cede30, 3cc9c1e, 4c86d9e). Stary
> zapis „plik lokalny (gitignored)" był NIEPRAWDZIWY — nie ma dla niego żadnej
> reguły w .gitignore. Traktuj go jak każdy inny plik repo.
>
> **Zasada obsługi:** czytaj sekcję 0 → 1 → znajdź pierwszy niezaznaczony `[ ]`
> w ROADMAP → rób → odhacz → dopisz linię do „Log sesji" na końcu.
>
> Ostatnia aktualizacja: **2026-09-04**

---

# ⏯ WZNOWIENIE — CZYTAJ TO NAJPIERW (gdy user mówi „kontynuujemy z TradePulse")

> Trigger: user mówi „kontynuujemy / wracamy do TradePulse / co dalej z botem".
> Nie pytaj „od czego zacząć" — odpowiedź jest tu. Wykonaj protokół i ruszaj.

### 📍 STATUS TERAZ  (← tę linię AKTUALIZUJ na końcu każdej sesji)

**Stan na 2026-09-05 (sesja: BEZPIECZEŃSTWO EGZEKUCJI — dzień 51/56 okna M5).**
Check-up przed pracą: sha M5 `r8Luxno…tNq0=` nietknięte, 9/9 alarmów OK, 0 błędów
przez 14 dni, 7/7 + 42/42 + 7/7 wywołań, 3/3 harmonogramy ENABLED. Kanał 4h wciąż
LONG od 18.08 (mark 79 806, equity **244,79** = +22,4%, z czego −1,03%
zaksięgowane), bot 1d LONG od 22.08 (equity 10 323,10 = +3,23%), bramka C 3/20.

Zrobione 2026-09-05 — **`docs/EXECUTION_SAFETY_2026-09-05.md`** (audyt §10
KROK 1, branch `session/exec-safety-20260905`). Zamknięte 2× CRITICAL + 3× HIGH
+ MEDIUM-3/4 + E3, **zero zmian księgowania, zero zasobów M5 w planie**:
- **CRITICAL-1**: deterministyczny `newClientOrderId` z (symbol, strona, decyzja)
  → giełda sama odrzuca duplikat. `POST /order` nie jest już ślepo powtarzany —
  po timeoucie/5xx pytamy przez `origClientOrderId`, resend tylko po odpowiedzi
  „nie ma takiego zlecenia", dwa razy bez odpowiedzi → `OrderSubmissionUncertain`.
  Duplikat rozpoznajemy pytaniem, nie treścią błędu (−2010 = i duplikat, i brak
  środków). Odzyskany fill dociąga prowizje z `myTrades`.
- **CRITICAL-2**: skan sierot przed decyzją — nasze wykonane zlecenie, którego
  księga nie zapisała, zatrzymuje run (`BookOutOfSync`). „Wytłumaczone" = id dla
  ostatniego zapisanego bara, bo `step()` zapisuje księgę i bar jednym zapisem PO
  fillu. Znacznik jedzie do przodu w każdym czystym runie (inaczej okno skanu
  oślepłoby), a zasiew też skanuje.
- **HIGH-1** T2 ożył (`drag` po `step()`); **HIGH-2** rekoncyliacja fail-closed w
  obie strony; **HIGH-3** `VENUE_CREDENTIALS_PATH` + `BINANCE_BASE_URL` z env,
  klucze bez „DEMO"; **MEDIUM-3** `reserved_concurrent_executions=1` + warunkowy
  zapis stanu (`state_version`); **MEDIUM-4** halt zapisywany przed flattenem,
  klucz `halt@<bar>`; **E3** jawny `event_invoke_config` (0 retry).
- **30 nowych testów**, każdy pisany tak, by padać na kodzie sprzed naprawy;
  sprawdzone mutacją **5/5 złapanych**. Suite 444 zielony, złoty wzorzec księgi
  bez zmian.
- Weryfikacja na żywo PRZED deployem (tylko odczyt): `allOrders` w obu trybach,
  `lookup_order` → `None`, `myTrades` = 0,00024844 BNB (co do cyfry jak w logu
  fillów), dry-run `attach_venue` na realnej księdze — obie strony przechodzą.
- `terraform plan`: **2 do dodania, 2 do zmiany, 0 do usunięcia**, wyłącznie
  venue-4h + shadow. `dist/paper_bot_lambda.zip` nietknięty.
- ✅ **DEPLOY WYKONANY 17:00 UTC i zweryfikowany**: sha M5 `r8Luxno…tNq0=` dalej
  nietknięte, retry=0 i współbieżność=1 na obu, wymuszony heartbeat zrobił pełny
  round-trip i wrócił flat, a zlecenia niosą u źródła id `tpsh-ee03d31d29bdef98ecaf`
  / `tpsh-dd06063af2905d43aba9` — **dokładnie** te, które kod wylicza z klucza
  decyzji (determinizm potwierdzony end-to-end). `state_version: 2` w księdze
  heartbeatu = warunkowy zapis działa na prodzie. Kill-switch 4h czysty.
  Kanał 4h dostanie wersję stanu i znacznik zleceń przy runie 20:10 UTC.

**Stan na 2026-09-04 (sesja: PEŁNY AUDYT — dzień 50/56 okna M5).** System
zdrowy w całości: sha M5 `r8Luxno…tNq0=` nietknięte, 9/9 alarmów OK, 0 błędów
przez 14 dni, 84/84 wywołań venue, testy zielone. **Bramka A PASS 6/6** (51 barów),
bramka B `WINDOW_RUNNING` (0 RT, equity +5,32%, maxDD −3,63%), **bramka C 3/20**.
Bot 1d LONG od 22.08; kanał 4h **wciąż LONG od 18.08** (entry 64 643, equity
243,62 = +21,8%, z czego −1,03% zaksięgowane) — pozycja potwierdzona u źródła
(0,05309 BTC, 0 otwartych zleceń). Domena odnowiona automatycznie do
**2027-09-28** (zapis „decyzja ~2026-09-29" niżej jest nieaktualny).

Zrobione 2026-09-04 — **`docs/AUDIT_2026-09-04.md`** (7 agentów + własna
weryfikacja każdego HIGH/CRITICAL w kodzie i na prodzie; NIC nie zmienione poza
docs/plan). Werdykt w skrócie:
- **Strategia: nic do poprawy** — 9/9 odrzuceń = False Strategy Theorem; kanon
  mówi „więcej treningu to zła dźwignia" przy N≈15–20 trejdów.
- **Ścieżka pieniędzy: 2× CRITICAL + 4× HIGH**, wszystko klasa „awaria
  systemowa", nic na Lambdach M5: brak `newClientOrderId` + retry POST po
  timeout (duplikat zlecenia); zlecenie PRZED zapisem `last_bar` + domyślny retry
  Lambdy (re-trade bara); **T2 kill-switcha martwe** (`execution_drag = 0.0` w
  DynamoDB po 3 fillach — potwierdzone); **sizing z konta (sufit 200), nie z
  księgi** → stąd `cash = −1,81` w księdze 4h; wspólny prefix SSM shadow/venue;
  rekoncyliacja tylko loguje.
- **Walidacja: 2× HIGH** — optymalizator walk-forward NIGDY nic nie wybrał
  (`min_trades=10` → fallback do `combos[0]` = 10/50; „adaptive 1,11–1,18" to
  stały backtest 10/50); DSR w złych jednostkach (`0.3` per-bar → zawsze 0,000).
  Sklejanie foldów zawyża OOS Sharpe'a o ~0,05 (ciągły 0,96 vs B&H 0,87).
- 🟢 **Blocker M6 „stały IP" prawie na pewno NIE ISTNIEJE** — reguła Binance
  dotyczy kluczy HMAC; self-generated **Ed25519** mogą handlować bez IP (cytat
  u źródła w audycie §9). NAT GW za $400/rok wypada; koszt = podpis Ed25519
  w executorze. KROK 0 = user testuje klucz jednorazowy.
- ✅ **PR #57 ZMERGOWANY** przez usera w trakcie sesji. Druga część sesji:
  **audyt E2E → `docs/ANALIZA_E2E_2026-09-04.md`** (24 szwy na żywo: feed →
  sygnał → log → księga → giełda → stan → API → strona → alarmy → SNS →
  Terraform). Ścieżka spójna od końca do końca; `terraform plan` bez zmian na
  obu rootach; SNS e-mail CONFIRMED, historia alarmów dowodzi, że rurociąg
  odpalił i wrócił 06–07.08. Luki: **E1** — `gate.py --fidelity` jest 1d-only
  (`WINDOW_START` zaszyte, replay ścieżką modelowaną) → kanał 4h, który pójdzie
  na live, **nie ma sprawdzenia „księga == replay"**; jego FAIL (348 rozjazdów
  po $0,15–0,20) to dokładnie niezaksięgowana prowizja BNB (200,00 vs 199,80).
  **E2** — origin `/api/state` publiczny bez CloudFront (OAC do zrobienia w
  `infra-site/`). **E3** — brak `event_invoke_config` → domyślne 2 retry
  Lambdy aktywne (potwierdza przesłankę CRITICAL-2). Fixy z 21.07 (PR #16)
  wszystkie trzymają.

**Stan na 2026-08-25 (sesja: CHECK-UP + KANDYDAT #9).** System zdrowy w
całości: 9/9 alarmów OK, 0 błędów przez 7 dni, 42/42 wywołań bota 4h,
115/115 barów bez luki, zamrożenie M5 (`CodeSha256`) nietknięte. Pozycja
bota **potwierdzona u źródła** — konto Binance demo trzyma 0,05309 BTC
(= 0,05 bazowe + 0,00309 bota), wszystkie 3 zlecenia zgodne z księgą.

Zrobione 2026-08-25:
- 🔴 **Kandydat #9 (trailing stop) ODRZUCONY** — pierwszy kandydat, którego
  przesłanka PRZESZŁA (zwycięskie 1d szczytują +73,5%, wychodzą +33,5%),
  a mimo to padł: wspólne pasmo na obu horyzontach = 1 wartość (wymagane 3),
  a „poprawa" stoi na 1 transakcji (4h: 111% efektu z jednego zdarzenia).
  Docs: `TRAILING_STOP_DESIGN_2026-08-25.md` + `..._RESULTS_...`. **Bilans 9/9
  odrzuconych.** Nowa lekcja: dobra przesłanka NIE jest obietnicą.
- ✅ **F7 zweryfikowane historycznie** (przy okazji, bo stopy ~10% bywają
  zabójcze): na 1d wyraźnie pomaga, na 4h kosztuje 0,04 Sharpe'a. Bez akcji.
- 🐞 **Naprawione `/api/state` → `paper.equity`** — zwracało `realized`
  (zaksięgowane) zamiast wyceny rynkowej. Niewidoczne, dopóki bot 1d stał
  flat; od 2026-08-22 zaniżało o 2,5%. + 4 testy (`test_site_status.py`).
  ⚠️ **`terraform apply` w `infra-site/` JESZCZE NIE WYKONANY** — plan
  zweryfikowany (1 zmiana, wyłącznie Lambda strony, zero zasobów M5).
- 🔍 **Znaleziona luka wierności kosztów** — patrz „KSIĘGA 4h NIE PŁACI
  PROWIZJI" niżej. Świadomie NIE naprawiona w trakcie zbierania bramki C.

Zrobione 2026-08-08 (PR #54 zmergowany, **PR #55 OTWARTY, CI zielone**):
- **`https://tradepulseai.co.uk` LIVE** (apex + www) — statyczna strona
  portfolio: żywy wykres 4h z Binance, EMA20/100, markery z logu fillów,
  panel realnej pozycji bota giełdowego, sekcja egzekucji, tabela 8
  odrzuconych ulepszeń. Źródło `web/`, deploy `./scripts/deploy_site.sh`
  **z korzenia repo**.
- **Nowa Lambda `tradepulse-site-status`** (read-only, `infra-site/lambda/`)
  serwuje `/api/state` spod tej samej domeny → CSP zostaje `connect-src 'self'`.
  Cache 60 s na brzegu ogranicza origin do ~1/min (rachunek nie może wystrzelić).
- **README przepisany** — stary reklamował 6-warstwowy mózg ML jako serce
  systemu (jest w kwarantannie od 2026-07-17) i powtarzał wycofaną notę
  „edge dies >0.3% fees". Poprawione też Sharpe na OOS 1,00–1,14 vs B&H
  0,81–1,00. Przy okazji naprawiony `backtesting.run --help` (crash na
  niezescape'owanym `%` w argparse).
- Koszt zaktualizowany na uczciwe **$1,35/mies.** ($0,50 strefa + $0,75 domena;
  Lambda/CloudFront/CloudWatch = $0,00 wg realnej faktury).

**Jesteśmy dalej w trybie: czekamy i zbieramy dane.**

#### Gdzie jesteśmy w milestone'ach
M0–M4 ✅ · **M5 BIEGNIE — dzień 40/56**, ocena bramek ≥2026-09-10 · M6 zabramkowane bramką B.
Kanał 4h: long od **2026-08-18 16:00** (entry 64 643,48, qty 0,00309) po
zamknięciu pierwszego round-tripu ze **STRATĄ −1,03%** (06.08 → 12.08);
bramka C zbiera dowody TRWALE (DynamoDB) — `COLLECTING 3/20 filli`;
kill-switch + **F7** (stop 10% od entry, dzienny limit 10%, progi
pre-rejestrowane z pomiaru; ✅ zweryfikowane historycznie 2026-08-25 —
na 1d Sharpe 0,710→0,895 i DD −64,3%→−46,8%, na 4h koszt 0,04 Sharpe'a).
**Kwarantanna enterprise WYKONANA** (5 skazanych klas odmawia startu bez
`ENTERPRISE_ENGINES=on`). Dane pod ML zebrane: funding 2020-01+, snapshot
Coin Metrics 2026-08-07 (też w safety), metrics OI **dociągnięte** (623 170
wierszy, 2166/2166 dni). Alarmy shadow/venue naprawione (PR #43) — patrz niżej.

#### Co CHODZI na produkcji (5 Lambd, wszystkie ENABLED, koszt $1,35/mies. all-in)

| Co | Harmonogram | Rola |
|---|---|---|
| `tradepulse-paper-bot` | `cron(10 0 * * ? *)` | **kanał mierzony M5** — BTC 1d, czysta symulacja. NIE DOTYKAĆ. |
| `tradepulse-paper-bot-status` | (URL) | status/dashboard |
| `tradepulse-shadow-bot` | `cron(25 0 * * ? *)` | heartbeat egzekucji na demo — codzienny round-trip, żeby ścieżka nie zgniła |
| `tradepulse-venue-4h` | `cron(10 0,4,8,12,16,20)` | BTC 4h, księga papierowa z **prawdziwymi fillami** na demo + kill-switch |
| `tradepulse-site-status` | (URL, za CloudFront) | **NIE-M5**, dodana 2026-08-08 — read-only `/api/state` dla strony. Własny root `infra-site/`, IAM = tylko `GetItem`/`Query` na tabeli. Zmiana tutaj NIE dotyka M5. |

#### 🔒 NIENARUSZALNE W OKNIE M5
- Obie Lambdy M5 mają `CodeSha256 = r8LuxnoJgluluwOEuPP6tk5nRDrhpjNq4emap/stNq0=`
  (deploy 2026-07-22). **Zweryfikowane po każdym z 6 `terraform apply` 2026-08-07**
  (ostatni: alarmy, PR #43 — plan dotykał WYŁĄCZNIE `aws_cloudwatch_metric_alarm`).
- Chroni je `lifecycle { ignore_changes = [filename, source_code_hash] }` w
  `main.tf` — dodane, bo repo było JEDNO `apply` od redeployu bota w środku
  pomiaru. 🔴 **Przy M6 ten bezpiecznik trzeba świadomie USUNĄĆ**, inaczej
  deploy po cichu nic nie zrobi.
- Każda nowa Lambda MUSI mieć własny zip (`build_lambda_package.sh --shadow` /
  `--venue-4h`). Współdzielenie `var.lambda_zip_path` = redeploy M5.
- Bramka A: **PASS 6/6** na żywym prodzie, 22 decyzje bez luk.
- 🆕 **DWA ROOTY TERRAFORM (2026-08-08).** `infra-serverless/` = M5, zamrożone.
  `infra-site/` = strona + jej API, własny klucz stanu, **zero zasobów M5** —
  `apply` tam fizycznie nie może zaplanować zmiany na Lambdach bota. To jest
  mocniejsze niż `ignore_changes`. **Nie łączyć rootów.** Efekt uboczny, który
  się opłacił: `infra-site/` mógł przejść na AWS provider 6.x (potrzebny dla
  `invoked_via_function_url`) bez ryzyka dla zamrożonego stacku, zero dryfu.
  Strefa Route53 zostaje własnością `infra-serverless/`, w `infra-site/`
  czytana data source'em.

#### Stan strategii
🆕 **Bot 1d WYSZEDŁ Z FLAT 2026-08-22** — pierwszy sygnał od 2026-05-29,
entry 77 090,34, equity 10 236,53 (+2,37%), 0 zamkniętych transakcji.
Zapis „FLAT przez całe okno" jest **nieaktualny**: okno M5 ma wreszcie
otwartą pozycję w mierzonym kanale. Bramka B dalej ma ~1% mocy w 56 dni
→ spodziewany werdykt `INCONCLUSIVE_EXTEND`, realny horyzont 12–18 mies.
Jedna pozycja tego nie zmienia — zmienia tylko to, że jest co mierzyć.

Kanał 4h (giełdowy) na 2026-08-25: equity 242,07 z 200 = **+21,04%**, ale
uczciwe rozbicie to **−1,03% zaksięgowane** (jedyna zamknięta transakcja,
stratna) i **+22,09% niezrealizowane** w otwartej pozycji. Buy & hold w tym
samym oknie: **+22,47%** — bot jest **1,43 pp ZA rynkiem**. To normalne dla
trend-followingu (wchodzi po potwierdzeniu, zapłacił za jeden fałszywy start),
ale „bije rynek" byłoby nieprawdą.

#### 🔍 KSIĘGA 4h NIE PŁACI PROWIZJI (znalezione 2026-08-25, ŚWIADOMIE NIE NAPRAWIONE)

`_book_actual_fee` w `portfolio.py` księguje prowizję w BNB do `fees_external`
**poza equity** — bo bez kursu BNB nie da się jej przeliczyć. To jest udokumentowana,
uczciwa decyzja („zgadywanie kursu byłoby gorsze niż pokazanie osobno"), ale ma
konsekwencję, której nikt nie policzył: **ścieżka quantity-backed nie obciąża
equity ŻADNĄ prowizją**. Ścieżka modelowana (bot 1d) obciąża normalnie.

Zmierzone po kursach BNB z chwili każdego filla:

| fill | notional | kurs BNB | prowizja | stawka |
|---|---|---|---|---|
| 06.08 21:11 | $199,87 | 771,94 | $0,1955 | 0,0978% |
| 12.08 04:10 | $197,80 | 810,67 | $0,1962 | 0,0992% |
| 18.08 20:10 | $199,75 | 845,60 | $0,2101 | 0,1052% |

- **Razem $0,6018 zapłacone i nigdy niezaksięgowane.** Equity 242,07 → uczciwie
  **241,47**, czyli **+20,73%** zamiast +21,04%. Rośnie z każdym fillem.
- 🔴 **Hipoteza o rabacie BNB OBALONA POMIAREM**: stawka realna to ~0,10%, nie
  0,075%. Model kosztu (`fee_rate=0.001`) jest **trafny co do 0,7%** —
  backtest liczy prowizję dobrze, po prostu żywa księga jej nie stosuje.
- **Dlaczego nie naprawiamy TERAZ:** bramka C jest w trakcie zbierania (3/20),
  a to jest zmiana księgowania w środku pomiaru. Naprawa po zamknięciu bramki C
  albo przy M6, przez dyscyplinę golden master (zamroź PRZED dotknięciem).
- **Co zrobić tanio i od razu:** strona w ogóle nie pokazuje `fees_external`
  (API je zwraca, frontend ignoruje). Wystarczy je wyświetlić, żeby publikowana
  liczba przestała być cicho zawyżona.

#### 🔴 CZTERY RZECZY, KTÓRYCH NIKT NIE SZUKAŁ (z 2026-08-06)
1. **Mina w Terraformie** — `plan` na czystym repo chciał przedeployować obie
   Lambdy M5. Rozbrojone (patrz wyżej).
2. **Model ułamkowy ZANIŻA koszt shorta** — prowizję wyjściową liczy od
   wynikowego kapitału, giełda od notionalu. Dla longa identyczne, dla shorta
   ~$0,07/$10k. Nie dotyczy żywej strategii, ale `engine` ma `allow_short=True`
   domyślnie → dotyczy każdego researchu shortów. Przybite testem, świadomie
   NIE naprawione (to decyzja walidacyjna).
3. **„4h = 7,2× szybszy dowód" było NIEPRAWDĄ** — obalone symulacją. SE
   zannualizowanego Sharpe'a zależy od CZASU KALENDARZOWEGO, nie od
   częstotliwości (`SE = √P·√(1/(P·T)) = √(1/T)`). 4h daje szybciej statystyki
   NA TREJD, nie werdykt o rentowności.
4. **Maker orders nic nie dają** — Binance VIP 0 ma maker = taker = 0,1000%, a
   spread to 0,000016%. Wartość $0,0004/rok wobec $4,88 prowizji. NIE BUDUJEMY.

#### Otwarte, świadomie odłożone
- Prowizja na demo idzie w **BNB** i nie da się tego wyłączyć (brak strony
  preferencji, brak `/sapi/v1/bnbBurn`, brak checkboxa). Na koncie LIVE
  wyłączone 2026-08-06. Księga księguje to w `fees_external` poza equity —
  celowo, bo bez kursu BNB nie da się przeliczyć.
- ~~Kwarantanna enterprise w monolicie~~ — **WYKONANA 2026-08-07**.
- **M3b (odchudzanie monolitu) ZAMKNIĘTE jako nieaktualne** 2026-08-07: produkcja
  to 3 961 linii bez ŻADNEGO powiązania z 39 184 liniami `services/`+`brain/`.
  Kasowanie tych 39 tys. świadomie odrzucone (zabrałoby furtkę `ENTERPRISE_ENGINES=on`).
- 🔴 **BLOCKER M6: klucz Binance z prawem handlu wymaga STAŁEGO IP**, a Lambda
  go nie ma. NAT GW ~$400/rok wobec budżetu $9,60/rok. Pełna analiza wariantów
  w ramce w sekcji M6. PIERWSZY krok = zmierzyć, czy polityka faktycznie gryzie.
- ~~🔑 Klucz LIVE `TradePulseAI` do skasowania~~ — **SKASOWANY 2026-08-08**
  przez usera; konto LIVE bez kluczy, demo (SSM) nietknięte, boty grają.
- ~~Hosting frontendu na tradepulseai.co.uk~~ — **ZROBIONE 2026-08-08**, apex
  + www live (S3 + CloudFront + ACM, root `infra-site/`). Domena auto-renew do
  2026-09-28 ($9/rok — TA POZYCJA JEST W koszcie $1,35/mies., nie zapomnieć).

### 🎯 NASTĘPNA AKCJA (ustalone na koniec sesji 2026-09-05)

> **DECYZJA 2026-09-05:** KROK 1 audytu ZROBIONY. Kolejność dalej wg
> `docs/AUDIT_2026-09-04.md` §10. Do 10.09 nie ruszamy M5 ani `gate.py`.

**0. LISTA AKCJI USERA:**
- [ ] **`terraform -chdir=infra-serverless apply tfplan`** — deploy venue-4h +
      shadow z poprawkami bezpieczeństwa egzekucji (plan zweryfikowany: 2 add,
      2 change, 0 destroy, żadnego zasobu M5). Po apply: sha M5 bez zmian,
      wymuszony heartbeat, `killswitch --timeframe 4h`.
- [ ] **Zmergować PR z branchu `session/exec-safety-20260905`.**
- [ ] **KROK 0 (15 min, zero kodu, wciąż otwarte):** na koncie LIVE założyć
      jednorazowy klucz **Ed25519** (self-generated) z Reading + Spot Trading,
      **BEZ IP**, wypłaty OFF — zapisać, czy Binance go przyjmuje. To rozstrzyga,
      czy M6 kosztuje $0 czy ~$40/rok. Klucza nie używać.
- [ ] Decyzja do pre-rejestracji PRZED kolejną oceną: zaostrzyć bramkę B o
      `psr_vs_zero ≥ 0,95` lub `window_days ≥ 365` (audyt §3 HIGH-2).

**1. OCENA BRAMEK ≥2026-09-10** — kodem JAK JEST (pre-rejestracja), raport do
`docs/`. Spodziewane: A PASS, B `INCONCLUSIVE_EXTEND`, C 3/20.

**2. PO OCENIE (audyt §10 KROK 2):** DSR `0.3/365`; walk-forward
`no_admissible_combo`; ciągły OOS w `calibration_audit.py`; diagnostyki w
raporcie bramki (B&H, CI Lo, N_eff, DD czas trwania); poprawić
`M4_EDGE_VALIDATION.md`/plan („adaptive" = 10/50). Plus **E1**: `gate --fidelity`
per kanał (4h nie ma dziś sprawdzenia „księga == replay").

**3. KSIĘGA v2 (audyt §10 KROK 3, decyzja: zaraz po KROKU 1):** sizing BUY z
`book.cash`, prowizja BNB do equity, resztka qty — pod dyscypliną złotego wzorca.

**4. OPERACJE (dowolna sesja):** healthchecks.io dead-man; `docs/RUNBOOK.md`;
eksport HMRC z fill-logu; `fees_external` na stronie.

---

#### (poprzednia NASTĘPNA AKCJA z 2026-09-04, PR #57 — zachowana dla kontekstu)

> **DECYZJA 2026-09-04: następna sesja = `docs/AUDIT_2026-09-04.md` §10**, po
> kolei. Strategii nie ruszamy (nic do poprawy). Do 10.09 nie ruszamy M5 ani
> `gate.py`; ocenę 10.09 uruchamiamy kodem JAK JEST i zapisujemy do `docs/`.

**0. LISTA AKCJI USERA:**
- [x] ~~Zmergować PR #57~~ — ZMERGOWANY 2026-09-04.
- [ ] **Zmergować PR #58** (audyt E2E; tylko docs + plan).
- [ ] **KROK 0 (15 min, zero kodu):** na koncie LIVE założyć jednorazowy klucz
      **Ed25519** (self-generated) z Reading + Spot Trading, **BEZ IP**, wypłaty
      OFF — i zapisać, czy Binance go przyjmuje / czy znika banner „will be
      deleted". To rozstrzyga, czy M6 kosztuje $0 czy ~$40/rok. Klucza nie używać.
- [ ] Decyzja: księga v2 (sizing z `cash`, prowizja BNB, resztka qty) — razem z
      poprawkami bezpieczeństwa pod golden master, czy dopiero po bramce C?
      Rekomendacja audytu: razem (nie czekać do 2027 ze złą księgą).
- [ ] Decyzja do pre-rejestracji PRZED kolejną oceną co 28 dni: zaostrzyć bramkę B
      o `psr_vs_zero ≥ 0,95` lub `window_days ≥ 365` (audyt §3 HIGH-2).

**1. SESJA KODOWA A (M5-safe, kanał 4h, bezpieczeństwo egzekucji):** audyt §10
KROK 1 — `newClientOrderId` + zero retry POST + rekoncyliacja po
`origClientOrderId`; odczyt filli PRZED decyzją; `drag` po `bot.step()`;
rekoncyliacja fail-closed w obie strony; osobne prefixy SSM; `reserved_concurrent_
executions=1`; testy łapiące każdą awarię; deploy venue+shadow z weryfikacją sha M5.

**2. PO OCENIE 10.09:** DSR `0.3/365`; walk-forward `no_admissible_combo`;
ciągły OOS w `calibration_audit.py`; diagnostyki w raporcie bramki (B&H, CI Lo,
N_eff, DD czas trwania); poprawić `M4_EDGE_VALIDATION.md`/plan („adaptive" = 10/50).

**3. OPERACJE (dowolna sesja):** healthchecks.io dead-man; `docs/RUNBOOK.md`;
eksport HMRC z fill-logu; `fees_external` na stronie.

---
#### (poprzednia NASTĘPNA AKCJA z 2026-08-25 — zachowana dla kontekstu)

> **DECYZJA 2026-08-25: DAJEMY BOTOWI POPRACOWAĆ ~MIESIĄC.** Nie dlatego, że
> nie ma co robić, tylko dlatego, że **jedyne, czego brakuje, to czas
> kalendarzowy**. Kolejka ulepszeń jest zmierzona i pusta (9/9 odrzuconych),
> a w oknie M5 i tak nie wolno ruszać strategii. Każda „poprawka" teraz
> psułaby pomiar, który właśnie zaczął mieć treść.

**0. LISTA AKCJI USERA (krótka, dwie pozycje):**
- [ ] **`terraform apply` w `infra-site/`** — naprawa `/api/state` jest
      zacommitowana, plan zweryfikowany (**1 zmiana, wyłącznie Lambda strony,
      zero zasobów M5**), ale apply zablokował klasyfikator auto-mode.
      Do czasu apply endpoint serwuje starą (zaniżoną) wartość.
- [ ] **Zmergować PR #56** (CI zielone: pytest + gitleaks).

**1. NAJBLIŻSZY KAMIEŃ: ocena bramek ≥2026-09-10** (za ~16 dni od 25.08).
Do tego czasu **nie ruszamy strategii**. Spodziewany werdykt bramki B:
`INCONCLUSIVE_EXTEND` (~1% mocy w 56 dni) — to nie porażka, to arytmetyka.

**2. CO ZROBIĆ PRZY NASTĘPNYM OTWARCIU (kolejność):**
1. Check-up jak 2026-08-25: alarmy, błędy, ciągłość barów, `CodeSha256` M5,
   **i pozycja u ŹRÓDŁA** (saldo konta demo + `allOrders`), nie tylko z księgi.
2. Sprawdzić, **czy kanał 4h zamknął pozycję otwartą 18.08**. To będzie
   pierwsza transakcja z realną treścią (wchodziła przy 64 643, w szczycie
   +22%). Jej wynik to najważniejszy nowy fakt, jaki może się pojawić.
3. Sprawdzić bramkę C (było 3/20) i bota 1d (long od 22.08).
4. Dopiero potem cokolwiek innego.

**3. ODŁOŻONE ŚWIADOMIE (nie zapomnieć, nie robić teraz):**
- **Prowizja poza księgą** — po zamknięciu bramki C, przez dyscyplinę golden
  master. Szczegóły w sekcji „KSIĘGA 4h NIE PŁACI PROWIZJI" wyżej.
- **Pokazać `fees_external` na stronie** — tanie i uczciwe, API już je zwraca,
  frontend ignoruje. Można zrobić w dowolnej sesji, nie dotyka M5.
- **Kandydat #10** — tylko przy ~2× zdarzeń albo cesze z NOWEJ hipotezy.
  Reguła bez zmian po 9 odrzuceniach.

**0-stare. ✅ WSZYSTKO Z 2026-08-07 WDROŻONE I ZWERYFIKOWANE E2E** (deploy F7
zrobiony, dane ML komplet, audyt E2E przeszedł: suite zielony, bramka A PASS,
C COLLECTING 1/20, heartbeat OK, DLQ puste, harmonogramy ENABLED).

**1. ✅ ZROBIONE 2026-08-07** — F7 potwierdzony na żywo (16:10 UTC, bar 12:00:
`held`, zero eventów „position risk", 0 błędów). Alarmy shadow/venue naprawione
i **zaapplikowane** (PR #43): `shadow-bot-errors` zgasł sam **78 s po apply**
zamiast wisieć do jutra — dokładnie to, po co była zmiana. F5 i M3b zamknięte
(patrz niżej). ✅ 2026-08-08: `shadow-bot-no-invocation` dojrzał i przeszedł
w OK (2026-08-07 18:09) — wszystkie 9 alarmów TradePulse w OK, DLQ puste.

✅ **2026-08-08: klucz Binance LIVE `TradePulseAI` SKASOWANY przez usera.**
Konto LIVE ma teraz zero kluczy. Boty grają dalej — używają WYŁĄCZNIE pary
demo z SSM (`/tradepulse/demo/key`+`secret`), zweryfikowane po skasowaniu
(venue-4h `held`, equity 201,51, killswitch czysty). Lista akcji usera PUSTA.
Nowy klucz LIVE dopiero przy M6 (i tam czeka znany blocker stałego IP).

**2. (research, M5-safe)** Backlog wg dowodów — **TANIA CZĘŚĆ WYCZERPANA
2026-08-08**: ~~vol targeting~~ (M4/F2) → ~~ensemble EMA~~ (OOS, doc
ENSEMBLE_OOS) → ~~mean reversion/day trading~~ (4× REJECT, doc
MEAN_REVERSION) → ~~filtry reżimu z idei L1~~ (**3× REJECT 2026-08-08**,
doc REGIME_FILTER: SMA200-y tną Sharpe'a, `calm vol` tnie DD do −43% ale
kosztuje ~0,05 Sharpe'a — zapisany jako przyszła CECHA, nie bramka).
**Poprzeczka dla meta-labelera = czyste EMA20/100.** 🔓 **PRÓG PRÓBY
OSIĄGNIĘTY 2026-08-08**: pooling 8 majorsów (uniwersum wg reguły, bez
cherry-pickingu) = **128 zdarzeń > 100** (doc POOLED_EVENTS_2026-08-08.md;
win rate 36%, mediana hold ~60 d → embargo!). Meta-labeler ODBLOKOWANY.
✅ **Tabela cech GOTOWA 2026-08-08** (`event_feature_table.py` →
`data/ml/events_features.csv`, doc EVENT_FEATURES_2026-08-08.md): 128
zdarzeń × 12 cech (5 per-aktywo + 7 rynkowych z BTC jako proxy cyklu),
dyscyplina point-in-time (shift +1 d dla serii dziennych, kroczące okna,
braki NIE imputowane; komplet 91/128). ✅ **PROJEKT MODELU PRE-REJESTROWANY
2026-08-08** po 3 kwerendach źródłowych → **`docs/METALABELER_DESIGN_
2026-08-08.md` — implementować DOKŁADNIE wg niego, nie renegocjować**:
purged 5-fold w blokach kalendarzowych wspólnych dla 8 rynków, purge po
faktycznych [entry,exit], **embargo 30 d** (h≈1%·T; horyzont etykiety
załatwia purging, NIE embargo — wcześniejszy zapis „≥60 d" był błędny),
logit L2 (XGBoost tylko benchmark), 5 cech wybranych domenowo + wskaźnik
braków, wagi próbek |net_return|, tłumienie 0,5–1,5× zamiast bramki 0/1,
diagnostyka top-5 wygranych, dziennik prób (budżet: dziesiątki na całe
życie projektu). 🔴 **WYKONANE 2026-08-08, próby #1–#2: REJECT W TREŚCI**
(doc METALABELER_RESULTS_2026-08-08.md): mechaniczny PASS 2/2 okazał się
artefaktem jednostajnej dźwigni — rho(p,win)=−0,01, 0/128 zdarzeń realnie
stłumionych, top-5 wygranych 5/5 czerwonych flag, C=0,01 wszędzie. Cechy
nie niosą wykrywalnego sygnału przy N=128 — prognoza literatury
potwierdzona. **Zostajemy przy czystym EMA20/100 (pretendent #8).**
Reguła werdyktu skorygowana osobnym commitem (od próby #3: wymagana
dyskryminacja + realne tłumienie + zero flag). Powrót do tematu tylko
przy ~2× większej próbie (szersze uniwersum/czas) albo cechach z nową
hipotezą (np. funding per-aktywo). SOPR NIEDOSTĘPNY w darmowym Coin
Metrics. **Research: brak tanich otwartych pozycji — pełny tryb
czekania/zbierania do oceny bramek ≥2026-09-10.**

**3. Czekanie na dane:** bramka C zbiera fille sama (~20 filli ≈ 10 mies.);
ocena bramek A/B ≥2026-09-10; re-ocena co 28 dni.

**4. ✅ FRONTEND PORTFOLIO — ZROBIONE 2026-08-08** (PR #54 zmergowany,
**PR #55 czeka na merge usera**, CI zielone). `tradepulseai.co.uk` live.
Otwarte drobiazgi na później, żadne nie pilne:
- 🔴 **Liczby na stronie to publiczne DEKLARACJE, nie ozdoby.** Zdezaktualizują
  się same: poślizg „2,0 → 4,4 bps / 1 of 20 fills" (zmieni się przy każdym
  nowym fillu bramki C), 5 Lambd, 82 zasoby Terraform, 9 alarmów, $1,35/mies.
  **Przy każdej zmianie infry sprawdzić `web/index.html`.**
- Mobile zweryfikowany na 390 px (brak przewijania poziomego; taśma, tabele
  i diagram przewijają się wewnątrz kontenerów — tak ma być).
- Sekcja „three bots" i diagram architektury pokazują 4 Lambdy M5; nowa
  `tradepulse-site-status` jest świadomie pominięta w diagramie jako
  szczegół prezentacji.

⚠️ **NIE ROBIMY:** vol targetingu w wariancie zmierzonym w M4 (odrzucony),
ensemble prędkości EMA (odrzucony OOS 2026-08-08), maker orderów (zmierzone,
bez sensu), shortów na BTC (odrzucone danymi), zmian strategii 1d w oknie,
pozycji ułamkowych w księdze (jedyny powód odpadł z ensemble),
**mean reversion / day tradingu** (zmierzony 2026-08-08: RSI kontra-trend
1d/4h/1h wszystkie REJECT, na 1h Sharpe −1,3…−3,8 i −100% —
docs/MEAN_REVERSION_2026-08-08.md).
### Protokół wznowienia (rób po kolei)
1. **Przeczytaj** `📍 STATUS TERAZ` → `🎯 NASTĘPNA AKCJA` powyżej. Odpowiedź na
   „od czego zacząć" jest tam — nie pytaj o nią usera.
2. **Zacznij z `main`** (`git pull`), zrób nowy feature branch. PR dopiero na
   końcu zadania; **user mergeuje ręcznie**, ja nie mergeuję.
3. **Sprawdź zdrowie** przed zmianami — 4 Lambdy jedną pętlą:
   ```bash
   for f in tradepulse-paper-bot tradepulse-paper-bot-status \
            tradepulse-shadow-bot tradepulse-venue-4h; do
     printf "%-32s " $f
     aws lambda get-function-configuration --function-name $f \
       --region eu-west-2 --query '[State,CodeSha256]' --output text
   done
   ```
   Obie Lambdy M5 MUSZĄ mieć `r8Luxno…tNq0=`. Inna wartość = ktoś przedeployował
   bota w oknie pomiarowym → **zatrzymaj się i powiedz userowi**.
4. **Zweryfikuj cytowane `plik:linia`** grepem, zanim zaczniesz edytować.
5. **Jeśli dotykasz `PaperPortfolio`** → dyscyplina złotego wzorca: zamroź
   PRZED, `==` na floatach, bramka A na prodzie PO.
6. **Testy przed końcem sesji** (cały suite, ~334 przypadki):
   `.venv/bin/pytest app/backend/tests/ -q`
7. **Na końcu:** dopisz do `Log sesji` + zaktualizuj `📍 STATUS TERAZ`
   i `🎯 NASTĘPNA AKCJA`.

### Przydatne
- Pytest: **`.venv/bin/pytest`** (globalny python NIE ma pytest)
- Bramka A na prodzie:
  `.venv/bin/python -m app.backend.paper_trading.gate --source dynamodb --fidelity`
- Stan kill-switcha (⚠️ bez `PAPER_STATE_BACKEND=dynamodb` czyta LOKALNY,
  pusty stan — pułapka znaleziona w audycie E2E 2026-08-07):
  `PAPER_STATE_BACKEND=dynamodb AWS_DEFAULT_REGION=eu-west-2
  .venv/bin/python -m app.backend.paper_trading.run killswitch --timeframe 4h`
- Wymuszony heartbeat: `aws lambda invoke --function-name tradepulse-shadow-bot
  --region eu-west-2 --cli-binary-format raw-in-base64-out
  --payload '{"force":true}' /tmp/o.json`
- Warsztat scenariuszy: `.venv/bin/python scripts/research/scenario_lab.py --list`
- **Terraform:** ja robię `plan -out=tfplan`, **`apply` robi user** (mnie blokuje
  klasyfikator uprawnień). Dawaj mu `terraform apply tfplan` — samo `apply`
  pyta interaktywnie i wisi bez odpowiedzi.
- Klucze demo: SSM `/tradepulse/demo/{key,secret}` (SecureString). Lokalnie
  przez `BINANCE_DEMO_KEY`/`BINANCE_DEMO_SECRET`, **nigdy w repo** (CI: gitleaks).
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
8. **Branch teraz, PR na końcu.** Nowy feature branch z `main` na każde
   zadanie, PR gdy zadanie skończone i CI zielone. **User mergeuje ręcznie.**
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
   zapisane `equity`/`realized` **do 1 grosza** (rekordy są zapisywane już
   zaokrąglone do 2 miejsc — `bot.py`; żądanie 1e-6 od zaokrąglonej liczby
   byłoby niespełnialne z definicji).
6. **Ciągłość infrastruktury:** zero pominiętych dni cronu, zero wiadomości
   w DLQ, alarmy `errors`/`no-invocation` nie odpaliły.
- Wszystkie 6 liczone WYŁĄCZNIE z danych, które już zapisujemy.
  ✅ ZAIMPLEMENTOWANE 2026-07-28: `gate.py --fidelity` (31 testów; każde
  kryterium ma test, że faktycznie ŁAPIE swoją awarię, nie tylko przechodzi).
- **Brakujący dowód ≠ PASS.** Kryterium bez danych = SKIPPED, a werdykt
  całości = **INCOMPLETE**. PASS wymaga wszystkich sześciu.
- ⚠️ **ZNANE OGRANICZENIE, zarejestrowane z góry:** w oknie w całości FLAT
  kryterium 2 (parytet sygnału) traci moc rozróżniającą — każda strategia
  trendowa mówi wtedy „0", więc PASS jest zgodny z hipotezą, że na żywo
  chodzi coś innego. Zweryfikowane empirycznie: weryfikacja logu prod wobec
  EMA10/50 (zamiast 20/100) też przechodzi. Narzędzie **samo to raportuje**
  (`discriminating: false` + CAVEAT przy werdykcie) — nie wolno tego przy
  ocenie przemilczeć ani interpretować jako pełnego dowodu.
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

## ▶ M3b — Odchudzenie / Faza 2 (SESJA D)  ✅ ZAMKNIĘTE 2026-08-07

> **Dlaczego zamknięte bez robienia D1/D2 — pomiar, nie opinia.** Premisa tego
> milestone'u („mamy 3× persistence i 2× emergency, trzeba scalić") padła DWA
> RAZY po tym, jak go zapisano, a plan po prostu za tym nie nadążył:
> **2026-07-17** audyt 6 warstw skazał stos enterprise („unfixable, retrain
> NOTHING"), **2026-08-07** kwarantanna sprawiła, że 5 skazanych klas odmawia
> konstrukcji. Zmierzone 2026-08-07:
>
> | co | linii |
> |---|---|
> | `paper_trading` — PRODUKCJA, 4 Lambdy | **3 961** |
> | `services/` + `brain/` — nigdzie nie wdrożone | **39 184** |
>
> `paper_trading` używa WYŁĄCZNIE importów względnych — zero powiązań z
> `services/`, `brain/`, `emergency`, `persistence`. Konsumenci D1/D2 to
> dokładnie skazany stos: `enhanced_market_persistence` ← `brain_controller`
> (skazany); `emergency_controls` ← `brain_controller` + `intelligent_exit_engine`
> (oba skazane). Czyli D1+D2 = ~2 940 linii refactoru wewnątrz 39 tys. linii
> kodu, którego produkcja nigdy nie wykonuje, częściowo w służbie klas już
> skazanych. Zero wpływu na bota, na bezpieczeństwo i na którąkolwiek bramkę.
>
> **Kwarantanna już osiągnęła cel bezpieczeństwa** (skazany kod nie startuje),
> więc kasowanie tych 39 tys. linii też nie jest pilne — a dodatkowo skasowałoby
> furtkę `ENTERPRISE_ENGINES=on`, którą kwarantanna świadomie zostawiła na
> offline'owy research. Opcja pozostaje otwarta, gdyby repo miało realnie schudnąć.

- ~~**D1. Persistence 3× → jeden**~~ — **OBSOLETE** (patrz ramka wyżej).
- ~~**D2. Emergency 2× → jeden**~~ — **OBSOLETE** (patrz ramka wyżej).
- [x] **D3. Ciche `except Exception`** (L5 `:1509,1514`, L4 `:1429` → 0.3/0.5)
      → loguj/podnoś krytyczne.
- [x] **D4. Legacy testy** `test_fast_diagnostics.py` — **już zielone**:
      zweryfikowane 2026-08-07, `5 passed`, nic nie było do naprawy.
- [x] **D5. Usuń „TEMPORARILY SKIP VALIDATION"** — **już nie istnieje**:
      `lifespan.py` nie ma w repo, stringa nie ma w `app/` (grep 2026-08-07).

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
> ~~Po drodze: ~2026-09-29 wygasa domena~~ — **odnowiona automatycznie do 2027-09-28** (sprawdzone 2026-09-04); nie jest już żadną decyzją w tym oknie.
- [ ] **M5.1** Zbieraj żywe metryki ≥8 tygodni (start 2026-07-16, koniec ≥2026-09-10).
- [ ] **M5.2** BRAMKA B (rentowność) — progi z sekcji 3. Raport.
      ⚠️ Oczekiwany werdykt 2026-09-10: `INCONCLUSIVE_EXTEND` (P(rozstrzygalna
      w 56 dni) = 1%). Re-ocena co 28 dni; realny horyzont 12–18 mies.
- [ ] **M5.3** BRAMKA A (wierność wykonania) — 6 kryteriów z sekcji 3.
      TO jest rozstrzygalne 2026-09-10 i to jest realny dorobek okna.
      Stan 2026-07-28 (dzień 12): **PASS wszystkie 6** na prodzie, z
      zastrzeżeniem o mocy rozróżniającej (okno FLAT). Odhaczyć po 09-10.
- [x] **M5.4** Zaimplementuj `gate.py --fidelity` (Bramka A) — ZROBIONE
      2026-07-28, 31 testów, zweryfikowane na żywym prodzie.

## ▶ M6 — Małe realne kwoty + PR (SESJA F, część 2)
> ### 🔴 BLOCKER M6 ZNALEZIONY 2026-08-07: klucz z prawem handlu wymaga STAŁEGO IP
>
> **Skąd:** własny komunikat Binance na stronie API Management konta LIVE —
> *„if the IP is unrestricted and any permission other than Reading is enabled,
> this API key will be deleted"*. Czyli klucz M6 (Spot Trading = on) **musi**
> mieć whitelistę IP, inaczej Binance sam go skasuje.
>
> **Dlaczego to problem:** Lambda bez VPC wychodzi z puli DYNAMICZNYCH adresów
> AWS — nie ma czego wpisać na whitelistę. Dziś nieszkodliwe (demo), ale przy
> M6 dotyczyłoby kanału z prawdziwą kasą.
>
> **Warianty i koszt** (cennik do potwierdzenia w dniu decyzji — poniżej rząd
> wielkości; budżet bota to dziś **$9,60/rok**):
>
> | wariant | koszt/rok | uwagi |
> |---|---|---|
> | NAT Gateway + EIP | **~$400** | ~$0,045–0,05/h. **40× budżet — odpada** |
> | instancja NAT (`t4g.nano`) + EIP | ~$37 | tanio, ale własny host do utrzymania |
> | mały always-on host robi tylko wywołanie giełdy | ~$42 | zmienia architekturę: to już nie Lambda |
>
> **NAJPIERW ZMIERZYĆ, POTEM BUDOWAĆ** (zasada z 2026-08-06): zanim
> przebudujemy architekturę pod ten komunikat, sprawdzić **czy i kiedy** ta
> polityka faktycznie gryzie — czy Binance kasuje klucz natychmiast, po N dniach,
> czy dopiero przy użyciu. Możliwe, że problem jest mniejszy niż komunikat
> sugeruje. To jest PIERWSZY krok F7, nie ostatni.
>
> **Czego NIE robić teraz:** nie zakładać klucza LIVE „na zapas" — leżałby
> nieużywany 12–18 mies., a Binance i tak może go w tym czasie usunąć.

- [~] **F5. Rotacja sekretów** — zweryfikowane 2026-08-07, szczegóły w `SECURITY.md`:
      **AWS ✅** (zrotowany 2026-07-16, wyciekły `…UDYJX5PC` skasowany 2026-08-07;
      ostatnie użycie 2025-12-27; produkcja i tak nie używa statycznych kluczy —
      4 Lambdy chodzą na rolach IAM). **SECRET_KEY ✅ nie ma czego rotować**
      (monolit nigdzie nie wdrożony, brak lokalnego `.env`, prod odmawia startu
      ze słabym kluczem). 🔴 **ZOSTAJE: klucz Binance LIVE** z `development.env`
      (`ENABLE_LIVE_TRADING=true`) — kopia siedzi w historii gita, tylko user
      może go skasować w API Management. Nic od niego nie zależy: bot czyta
      klucze DEMO z SSM, a `get_parameters` leci przy KAŻDYM wywołaniu bez
      cache'u, więc rotacja propaguje się na następnym przebiegu.
- [ ] **F6. PR** — dopiero gdy M0–M3 stabilne, CI zielone.
- [ ] **F7. Realne $50–100** — Bramka 3 z sekcji 7. Części składowe:
      - 🔴 **maker orders — ODRZUCONE 2026-08-06 na podstawie pomiaru.** Binance
        VIP 0 nalicza maker i taker IDENTYCZNIE (0,1000%/0,1000% — sprawdzone na
        koncie). Cała korzyść to nieprzechodzenie spreadu, a spread BTCUSDT to
        0,01 USDT na 64 468 = 0,000016%. Wartość: **$0,0004/rok** na $200 przy
        4h, przy prowizjach kosztujących $4,88/rok — różnica 12 000×. W zamian
        ryzyko niewypełnienia, psujące `backtest = live`. NIE BUDUJEMY.
      - ✅ **kill-switch ZAIMPLEMENTOWANY 2026-08-06** (`killswitch.py`), wpięty
        w kanał 4h, sprawdzany PRZED reconcile. T1 max-DD >25%, T2 rozjazd
        egzekucji >10%, T3 strata >15% w barze. Fail-closed, idempotentny,
        re-arm wyłącznie ręczny (`run rearm --confirm --note`) z rekordem
        audytowym. 27 testów wg planu z docs/KILL_SWITCH_DESIGN.
      - [ ] stop-loss i dzienny limit straty — do M6
      - [ ] realne pieniądze — dopiero po bramce B
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

# PLAN ROZWOJU — jak zrobić z tego bota, który się utrzymuje (ustalone 2026-08-05)

**Poprzeczka jest śmiesznie nisko i warto to sobie uświadomić.** TradePulse
kosztuje **$0,80/mies. = $9,60/rok** (udział w strefie Route53 $0,50 + zapytania
DNS + storage DynamoDB + 2 nowe alarmy z 2026-08-07 po $0,10; Lambda ~$0; było
$7,20/rok przed PR #43). Na $10k to **0,096%/rok**. **$100 realnego
kapitału przy 10%/rok nadal pokrywa rachunek.** Bot nie musi być lepszy — musi być
URUCHOMIONY na prawdziwych pieniądzach.
*(Konto AWS płaci ~$108/mies., ale ~$88 z tego to `postra-dev` — INNA APLIKACJA,
poza zakresem tego projektu, user wyraźnie: nie dotykamy.)*

**Bot już dowiózł wartość, tylko bramka jej nie widzi.** Od ostatniego SELL
(2026-05-29) BTC zrobił **−12,73%** (dołek −20,2%), bot był FLAT. Na $10k to
$1 273 nieutraconych = 177 lat rachunków AWS. Bramka M5 liczy round-tripy i P&L
**z trejdów** — za „poprawnie przeczekał zjazd" nie daje ani punktu. To zgadza
się z charakterem strategii z audytu kalibracji: redukuje DD, wygrywa
risk-adjusted, nie bije B&H absolutnie.

**Dwie niewiadome, RÓŻNE narzędzia — to jest sedno:**

| | Niewiadoma | Czym się rozwiązuje | Ile trwa |
|---|---|---|---|
| **A** | Czy strategia zarabia? | **Czasem** — nic tego nie przyspieszy poza kanałami | 12–18 mies. |
| **B** | Czy bot umie poprawnie WYKONAĆ trejd? | **Giełdą testową** — dostępne od zaraz | dni |

Cała uwaga szła dotąd w A. **B było nietknięte** (bot NIE MIAŁ kodu składania
zleceń — zero, sprawdzone grepem), blokuje M6 tak samo mocno i da się je zamknąć
od ręki. Dlatego priorytet = testnet, nie strategia.

**Kolejność:**
1. ✅ Szew wykonawczy (PR #24, 2026-08-05)
2. ✅ **`BinanceDemoExecutor`** (2026-08-06) — niewiadoma B ZAMKNIĘTA: bot
   udowodnił, że umie złożyć, wypełnić i rozliczyć zlecenie na prawdziwym
   silniku dopasowań. Szczegóły: docs/EXECUTOR_TESTNET_2026-08-06.md
3. **Księga ilościowa** ← następny krok (qty w BTC zamiast ułamka kapitału,
   + prowizja w BNB vs USDT); `LOT_SIZE`/`MIN_NOTIONAL`/częściowe fille już
   obsłużone po stronie executora
4. **Research 4h/ETH** (równolegle, M5-safe, dane gotowe i zwalidowane)
5. Diagnostyka „flat to też wynik" w raporcie bramki
6. Realne pieniądze — user 2026-08-05: **„nie czas jeszcze"**

**Tempo dowodu — dlaczego 4h w ogóle rozważamy** (szacunek z holdoutu, liczba
round-tripów, NIE walidacja edge'u):

| Instancja | Round-tripy/rok | Przyspieszenie |
|---|---|---|
| BTC 1d *(live)* | 1,69 | — |
| **BTC 4h** | **12,21** | **7,2×** |
| BTC 1h | 54,89 | 32× |
| ETH 1d | 1,80 | +1 równoległy kanał |

⚠️ HACZYK: audyt pokazał, że edge przeżywa 0,5% fee **dlatego, że** to ~20
trejdów przez 6,5 roku — „fee drag jest strukturalnie mały". Przy 7×
częstotliwości drag rośnie 7×. **1h prawie na pewno martwe; 4h to otwarte
pytanie wymagające walk-forward.**

**Protokół researchu 4h/ETH (żeby nie wyklikać sobie wyniku):**
- metoda jak `scripts/research/calibration_audit.py` — walk-forward, 4 layouty,
  holdout <2026-07-16
- siatka: BTC 4h + ETH 1d × fee 0,1 / 0,2 / 0,3 / 0,5% na stronę
- **reguła decyzyjna PRE-REJESTROWANA PRZED uruchomieniem**, propozycja:
  *przyjmujemy kanał tylko jeśli OOS Sharpe ≥0,8 przy 0,2% fee w ≥3 z 4
  layoutów ORAZ bije B&H*
- przyjęcie kanału = **START NOWEGO OKNA papierowego dla tego kanału**, NIGDY
  modyfikacja biegnącego BTC 1d

**Granica, której nie przekraczamy:** do 2026-09-10 można dodawać do raportu
bramki **diagnostyki** (np. wynik vs B&H, time-in-market), ale **NIE WOLNO
ruszać pre-rejestrowanych PROGÓW decyzyjnych** — te są nietykalne.

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
  (`data.py` JEST importowany przy cold starcie przez backtesting/__init__.py,
  ale zmieniona linia siedzi w load_csv(), którego bot nigdy nie woła —
  sprostowanie pierwotnego zapisu „bot nie importuje data.py").
  Zero ML na prodzie potwierdzone. Poprawione
  nieaktualne zapisy planu (fee >0.3%, „3.4 trejdy/rok", PR-y do zmergowania).
  Suite 95 testów zielonych. → PR #20.
- 2026-07-28 (cd.) — BRAMKA A ZAIMPLEMENTOWANA (branch feat/gate-fidelity,
  `gate.py --fidelity`). 6 kryteriów jako czyste funkcje + `evaluate_fidelity`
  (bez I/O, testowalne), loadery DynamoDB/local rozbite na surowe rekordy,
  `load_infra_aws` czyta CloudWatch (Invocations/dzień, DLQ max, historia
  alarmów) — wszystko read-only. 31 testów: KAŻDE kryterium ma parę
  „przechodzi na poprawnym logu" + „łapie swoją konkretną awarię"
  (brakujący bar, duplikat, przekręcony target, inna strategia, zła cena,
  decyzja przed zamknięciem bara, podmieniona equity, zły fee_rate,
  zgubiony trejd, brak inwokacji, DLQ, alarm). Fixture wymusza pełny
  round-trip — pierwsza wersja była FLAT i dwa testy przechodziły z
  niewłaściwego powodu (naprawione). Werdykt: brak dowodu = INCOMPLETE,
  nigdy PASS. **Na żywym prodzie dzień 12: PASS wszystkie 6** (13 rekordów
  07-15→07-27, parytet sygnału na oknie 399 barów, ceny co do grosza, brak
  look-ahead, replay księgowości ±$0.01, 12 dni inwokacji, DLQ pusty).
  ⚠️ ODKRYTE PRZY OKAZJI: w oknie FLAT kryterium 2 nie rozróżnia strategii
  — weryfikacja logu prod wobec EMA10/50 też przechodzi. Narzędzie samo
  raportuje `discriminating: false` + CAVEAT, ograniczenie ZAREJESTROWANE
  w §3 z góry. Suite 126 zielonych. → PR #21.
- 2026-07-28 (cd.2) — TFSTATE→S3 (branch chore/tfstate-s3-backend). Bucket
  `tradepulse-tfstate-590183672693` w eu-west-2: versioning ON (bo zły zapis
  ma być odwracalny), SSE-S3 + bucket key, block-public-access 4/4, policy
  deny na non-TLS. BEZ reguły lifecycle świadomie — stan waży ~60 KB, a
  expiration kasowałaby właśnie te punkty odtworzenia, po które ten bucket
  istnieje. Locking przez S3 conditional writes (`use_lockfile`, TF ≥1.10) —
  zero tabel DynamoDB do utrzymywania i opłacania. Bootstrap poza Terraformem
  (`scripts/bootstrap_tf_backend.sh`, idempotentny) — bucket nie może być
  zarządzany przez stan, który sam przechowuje. PROCEDURA: backup stanu do
  ~/TradePulse_safety + scratchpad → `plan` PRZED (czysty, „No changes") →
  `init -migrate-state` → `plan` PO (czysty) + `state list` 32/32. Uwaga:
  kopia dostała nowy lineage i serial 1 (metadane), treść i komplet zasobów
  bez zmian. Lokalny terraform.tfstate wyzerowany przez TF, .backup (61 KB)
  został jako dodatkowa siatka. `required_version` podbity do >=1.10;
  sprawdzone, że nie psuje CI — infra-deploy.yml celuje w martwy `infra/`,
  nie w `infra-serverless/`, i jest manual-only.
  ODKRYCIE PRZY OKAZJI: pozycja „odnowić domenę przed 09-10" była FAŁSZYWYM
  to-do — `AutoRenew: true` u rejestratora, strefa DNS istnieje (stary zapis
  „skasowana" nieaktualny), bot.tradepulseai.co.uk → 200. Reminder 08-24
  zbędny. NASTĘPNY KROK: tryb czekania do 2026-09-10; jedyny zaległy porządek
  to kwarantanna enterprise (zero pilności, nic tego nie uruchamia).
- 2026-08-05 — **Deep health-check całej apki + otwarcie toru wykonawczego.**
  ZDROWIE (wszystko zielone): obie Lambdy żyją, `CodeSha256 r8Luxno…tNq0=` bez
  dryfu; scheduler ENABLED `cron(10 0 * * ? *)` z DLQ+retry 3×; 3 alarmy OK;
  ZERO błędów w logach za 14 dni (1,6 s, 205/512 MB); 21 decyzji 07-15→08-04
  **bez ani jednej luki**, każda ~00:10:34 UTC; bramka A **PASS na 6/6**;
  bramka okna WINDOW_RUNNING dzień 20/56; holdout nienaruszony (CSV kończą się
  07-15); 3 workflowy deployu poprawnie manual-only; zero sekretów w gicie.
  WERYFIKACJA PROD↔REPO BAJTOWO (ściągnięta paczka Lambdy): 22/25 identycznych,
  3 różnice nieszkodliwe — teza „redeploy zbędny" jest teraz UDOWODNIONA, nie
  zadeklarowana. STRATEGIA: gap EMA −4,70% (od −7,44% na starcie okna, zawęża
  się); **0 sygnałów buy przez całe 20 dni, 0 z 20 dni z gap>0**; ostatni BUY
  2026-05-01, zamknięty 05-29 — 7 tygodni PRZED oknem; do crossa trzeba +4,93%
  na EMA20. To poprawne zachowanie trend-followingu w bessie, nie awaria.
  KOSZTY: TradePulse **$0,60/mies.**; konto płaci $108,76/lip., ale ~$88 to
  `postra-dev` (EC2 t3.medium + RDS + ALB + VPC) — INNA APKA, user: nie dotykamy.
  ZROBIONE: (1) **deletion protection na DynamoDB** (przez TF, plan 0/1/0,
  zweryfikowane; PITR 35 dni < okno 56 dni, a decyzji nie da się odtworzyć);
  (2) **warstwa Executor — PR #24** (`Order→Executor→Fill`, abstrakcja jak u
  giełdy: BUY/SELL). Odkrycie: bot **NIE MIAŁ ŻADNEGO kodu składania zleceń** —
  `PaperPortfolio` to czysta symulacja, więc przy przejściu na realne pieniądze
  byłby to świeży, nigdy nieuruchomiony kod od razu z kasą na nim. Ładne
  uproszczenie: slippage po stronie ZLECENIA zwija wejście i wyjście w jedną
  regułę `fill = ref*(1+order_side*slip)`, tożsamą z `costs.py` we wszystkich
  4 kombinacjach (osobno przetestowane — inaczej live odjechałoby od backtestu).
  DOWÓD, ŻE KSIĘGA NIE DRGNĘŁA: złoty wzorzec złapany PRZED refaktorem (3240
  barów + 1500-krokowa replika syntetyczna, `==` na floatach) + bramka A na
  żywym prodzie. 202 testy zielone (było 126).
  PUŁAPKI ZNALEZIONE: `build_lambda_package.sh` kopiuje TYLKO `paper_trading` +
  `backtesting` → nowy pakiet obok zaimportowałby się lokalnie i wywalił Lambdę
  na `ModuleNotFoundError` (dlatego executor jest w `paper_trading/`; doszedł
  guard + test resolvera, bo guard sam miał błąd i test go złapał). `data/ml/`
  jest CELOWO gitignorowane → złoty wzorzec musiał dostać przypadek syntetyczny
  bez zależności od danych (arytmetyka całkowitoliczbowa, bit-odtwarzalna),
  zweryfikowane uruchomieniem suite'u z ukrytymi danymi: zielone, 3 skipy.
  USTALENIA STRATEGICZNE → patrz sekcja „PLAN ROZWOJU" wyżej (dwie niewiadome
  A/B, tempo dowodu, protokół researchu 4h). Realne pieniądze: **„nie czas
  jeszcze"**. NASTĘPNY KROK: `BinanceTestnetExecutor` (krok 3).
  PR #24 wypchnięty, CI leciało na koniec sesji — **user mergeuje ręcznie**.
- 2026-08-06 — **Krok 3 ZROBIONY: `BinanceDemoExecutor` — niewiadoma B zamknięta.**
  Bot po raz pierwszy w historii projektu ZŁOŻYŁ PRAWDZIWE ZLECENIE i rozliczył
  je z księgą. Round-trip na żywym silniku dopasowań (orderId 54495523957 /
  54495523967): wejście 0.00031 BTC, wyjście, konto wróciło do 0.05000000 BTC
  **co do ostatniej cyfry** — executor sprzedał dokładnie to, co kupił, i nie
  tknął pre-fundowanych coinów. Zwrot −0.1995% = praktycznie sama prowizja
  round-tripu (0.1%×2), czyli księga i venue policzyły to samo.
  KOREKTA PLANU: plan mówił `testnet.binance.vision`, ale nasze klucze są z
  **Binance Demo Trading** — testnet odpowiada na nie `-2015`. Właściwy host:
  **`demo-api.binance.com`** (znaleziony empirycznie: `api.demo.*` nie
  odpowiada, `api-demo.*` daje 404). PUŁAPKA: `demo.binance.com/api/...` robi
  301 na **produkcyjne** `api.binance.com` — naiwne sklejenie base URL z domeny
  UI wysłałoby zlecenia na prawdziwą giełdę. Stała przypięta testem.
  ZMIERZONE, NIE ZAŁOŻONE: (1) prowizja venue 0.1% = dokładnie `fee_rate=0.001`
  bota — model kosztów potwierdzony przez rzeczywistość; (2) poślizg faktyczny
  0.000–0.003% vs zakładane 0.02% → model KONSERWATYWNY, backtest zaniża wynik.
  ⚠️ SPROSTOWANIE (jeszcze tego samego dnia): teza „demo ma własny feed" była
  BŁĘDNA — wzięła się z założenia o poziomie rynku, nie z pomiaru. Sprawdzone:
  ticker demo == ticker prod co do grosza (BTC naprawdę stoi 64,5k), opens świec
  identyczne, closes różnią się o ≤0.01 USDT. Różni się natomiast KSIĘGA ZLECEŃ:
  te same poziomy cenowe, inne wolumeny. Demo = ŻYWE CENY + osobny silnik
  dopasowań z płynnością uczestników demo. Poślizg jest więc lepszą poszlaką,
  niż zapisaliśmy, ale nadal nie pomiarem live (nie zjadamy prawdziwej księgi).
  🔴 ODKRYCIE → wejście do kroku 4: prowizję pobrano w **BNB**, nie w USDT
  (konto trzyma 2 BNB). Księga modeluje fee jako ułamek kapitału w USDT — to
  dwie różne waluty, i nikt tego nie widział, bo nie było kodu składającego
  zlecenia. `fee_asset` już to raportuje; księga ilościowa musi rozstrzygnąć.
  OBSŁUŻONE I PRZYPIĘTE TESTAMI (55, zero sieci): HMAC nad dokładnymi bajtami
  wire, resync przy `-1021` (raz, potem retry), `LOT_SIZE` w `Decimal` z
  zaokrągleniem W DÓŁ, `MIN_NOTIONAL` odrzucany lokalnie (zweryfikowane na
  żywo), VWAP przy fillach po wielu cenach, netowanie prowizji w base asset,
  brak notacji naukowej w `quantity`, 429 z `Retry-After` vs 418 bez retry,
  błędy biznesowe (`-2010`) od razu w górę. Cały suite: 256 zielonych (było 202).
  Higiena: klucze tylko przez env (`from_env`), w repo `.env.example`.
  ⚠️ Klucz LIVE użytkownika był odsłonięty w zrzucie ekranu → do rotacji.
  NASTĘPNY KROK: krok 4 — księga ilościowa (uwaga: dotyka `PaperPortfolio`,
  więc złoty wzorzec zamrozić PRZED refaktorem + bramka A po).
- 2026-08-06 (wieczór) — **Shadow-bot WDROŻONY + rozbrojona mina w Terraformie.**
  PR #26. Codzienny heartbeat na demo (`cron(25 0 * * ? *)`), żeby ścieżka
  wykonawcza nie zgniła między dziś a M6 — strategia robi 1,69 round-tripa/rok,
  więc sama jej nie przećwiczy. Świadomie NIE podąża za sygnałem (stałby flat
  miesiącami); każdy przebieg jest samowystarczalny i kończy flat.
  🔴 NAJWAŻNIEJSZE ZNALEZISKO, niezwiązane z zadaniem: `terraform plan` na
  CZYSTYM repo dawał „0 to add, 2 to change" — obie Lambdy M5 czekały na
  redeploy, bo 2026-08-05 przebudowano zipa przy PR #24. Każdy `apply`
  przedeployowałby bota w środku pomiaru kodem bez weryfikacji deployu.
  Bezpiecznik: `ignore_changes = [filename, source_code_hash]` na obu.
  Po apply POTWIERDZONE: obie nadal `r8Luxno…tNq0=`, LastModified 2026-07-22.
  Shadow ma też własnego zipa (`build_lambda_package.sh --shadow`), bo dzielenie
  `var.lambda_zip_path` znaczyłoby, że sam build zmienia hash Lambdy M5.
  ⚠️ PUŁAPKA: pierwszy deploy padł na `Runtime.ImportModuleError: No module
  named 'pandas'` — dałem 256 MB bez warstwy pandas, bo „heartbeat nie dotyka
  strategii". Błąd w rozumowaniu: import `app.backend.paper_trading.cokolwiek`
  odpala `__init__`, który importuje `bot` → pandas. Decyduje łańcuch importów,
  nie graf wywołań. Komentarz przy Lambdzie `status` mówił to wprost.
  Alarm `shadow-bot-errors` poprawnie wskoczył w ALARM na tym błędzie i sam
  wróci do OK po dobie — czyli monitoring działa (prawdziwy alarm, nie fałszywka).
  SPROSTOWANIE do wcześniejszego wpisu: „demo ma własny feed" było BŁĘDNE —
  ticker demo == prod co do grosza, opens świec identyczne, closes ≤0.01 USDT.
  Różni się KSIĘGA ZLECEŃ (te same ceny, inne wolumeny). Demo = żywe ceny +
  osobny silnik dopasowań.
  KOSZT: $0 dodatkowo (alarmy w darmowym progu 10, Lambda 1×/dzień, SSM
  standard, SQS free tier). Suite 273 zielone.
  NASTĘPNY KROK bez zmian: krok 4 — księga ilościowa.
- 2026-08-06 (późny wieczór) — **Krok 4 ZROBIONY: księga ilościowa.**
  Kluczowa decyzja projektowa: NIE przepisywać księgi, tylko pozwolić FILLOWI
  decydować o ścieżce. Fill bez `qty` (symulacja) → arytmetyka ułamkowa
  nietknięta instrukcja po instrukcji, więc złoty wzorzec przechodzi na `==`.
  Fill z `qty` (prawdziwe venue) → `cash + qty*price` i prowizja faktyczna.
  Reparametryzacja jest ścisła (`qty = side*E/entry`, `cash = E*(1-side)`),
  spięta testem równoważności; zmierzony rozjazd 1,8e-12 = reasocjacja floatów.
  WERYFIKACJA PEŁNA: złoty wzorzec `==` PASS (8 przypadków), **bramka A na
  ŻYWYM PRODZIE PASS 6/6** (22 decyzje → ±$0,01), round-trip przez księgę na
  prawdziwym venue (`quantity_backed: true`, `qty_after: 0.0`). Suite 295
  (było 273). Lambdy M5 bez redeployu, zip M5 hash niezmieniony.
  🔴 ZNALEZISKO: model ułamkowy ZANIŻA koszt shorta — prowizja wyjściowa
  liczona od wynikowego kapitału zamiast od notionalu transakcji. Dla longa
  identyczne (equity wyjściowe = notional), dla shorta ~$0,07/$10k na trejd.
  Nie dotyczy żywej strategii (`allow_short=False`), ale `engine` ma
  `allow_short=True` domyślnie → dotyczy każdego przyszłego researchu shortów.
  Przybite testem, świadomie NIE naprawione (to decyzja walidacyjna, nie bug).
  🔴 REKOMENDACJA M6: wyłączyć prowizję w BNB. Zmierzone na venue: koszt
  wylądował w `fees_external` poza equity, bo bez kursu BNB nie da się go
  przeliczyć, a zgadywanie byłoby gorsze. Dopóki tak jest, koszty w live nie
  odpowiadają backtestowi. Rabat 25% = grosze przy 1,69 round-tripa/rok.
  Shadow-bot od teraz prowadzi heartbeat PRZEZ księgę, więc ścieżka ilościowa
  jest ćwiczona codziennie na prawdziwych fillach, a nie tylko w testach.
  NASTĘPNY KROK: `scenario_lab.py` (warsztat scenariuszy).
- 2026-08-06 (noc) — **Warsztat scenariuszy + wyłączona prowizja w BNB.**
  `scenario_lab.py`: jeden młynek dla każdego kandydata, reguła pre-rejestrowana
  W KODZIE i drukowana PRZED wynikami, holdout egzekwowany w `load()`, kara za
  liczbę prób (Deflated Sharpe). Kontrolka BTC 1d odtwarza audyt kalibracji
  (Sharpe 1,00–1,14) — czyli młynek mierzy to, co powinien.
  WYNIKI: BTC 4h ACCEPT (kruchy — edge ginie między 0,2% a 0,3% prowizji),
  SHORT REJECT (gorszy w każdym layoucie, DD −59…−67%), ETH 1d REJECT (nie bije
  B&H). Szczegóły: docs/SCENARIO_LAB_2026-08-06.md.
  BNB: **wyłączone „Use BNB to pay fees" na koncie LIVE** (było ON, 25% rabatu;
  teraz Off — zweryfikowane w UI). ⚠️ ODKRYCIE: konto DEMO tego nie dziedziczy
  i nie da się tam tego zmienić — brak strony preferencji (404), brak
  `/sapi/v1/bnbBurn` (404), brak checkboxa przy formularzu. Sprawdzone
  empirycznie: heartbeat po zmianie NADAL nalicza w BNB. Skutek: `fees_external`
  będzie się pokazywać w logach shadow-bota i to jest OK — jego zadaniem jest
  dowodzić ścieżki wykonawczej, nie mierzyć kosztów. Przy okazji ścieżka
  `fees_external` jest dzięki temu ćwiczona codziennie na prodzie.
  NASTĘPNY KROK: nowe okno papierowe dla BTC 4h.
- 2026-08-06 (późna noc) — **Kanał BTC 4h na żywym venue + SPROSTOWANIE, które
  zmieniło uzasadnienie.** Przed budową zweryfikowałem tezę „7,2× szybszy dowód"
  symulacją (20 000 historii): **JEST NIEPRAWDZIWA.** SE zannualizowanego
  Sharpe'a przy 4h vs 1d to 1,00–1,02×, nie √6=2,45×. Algebra:
  `SE = √P·√(1/(P·T)) = √(1/T)` — częstotliwość się skraca, zostaje sam czas
  kalendarzowy. Poprawione w docs/SCENARIO_LAB i w tym planie; PR #30 zawierał
  to błędne twierdzenie.
  User poinformowany i wybrał wariant mocniejszy: kanał 4h WPIĘTY W GIEŁDĘ demo,
  czyli księga papierowa z prawdziwymi fillami. Uzasadnienie po korekcie:
  ~12 prawdziwych round-tripów/rok zamiast 1,69, a poślizg/fee drag/zachowanie
  księgi zbiegają się z liczbą trejdów, nie z czasem — i to jest dokładnie to,
  na czym zawiśnie M6, a czego 1d nie da z zasady.
  Zweryfikowane lokalnie na żywym venue: zlecenie 54508851440, 0,0031 BTC,
  poślizg 0,0189% vs 0,0200% zakładane, księga quantity_backed, equity 199,96.
  Restart z dysku odtwarza pozycję executora (0,0031) i nie kupuje ponownie.
  Infrastruktura: osobna Lambda/rola/harmonogram (`cron(10 0,4,8,12,16,20)`)/
  DLQ/alarmy + osobny zip; dzieli tylko tabelę (pk `BTCUSDT_4h`) i SNS.
  Plan: 13 do dodania, 0 zmian — M5 nietknięte, zip M5 hash bez zmian.
  NASTĘPNY KROK: wgrać, zweryfikować pierwszy przebieg, potem maker orders (F7).
- 2026-08-06 (po wdrożeniu 4h) — **Kanał 4h ŻYJE + rozdzielenie dryfu od
  poślizgu.** Wdrożone i zweryfikowane: `tradepulse-venue-4h` Active,
  `cron(10 0,4,8,12,16,20)` ENABLED, pierwszy przebieg z Lambdy złożył prawdziwe
  zlecenie 54510109086 (0,0031 BTC), księga equity 199,91. Lambdy M5 nadal
  `r8Luxno…`. Posprzątane po teście lokalnym: pozycja 0,0031 zamknięta
  (order 54510056311), konto wróciło do 0.05000000 BTC — inaczej saldo byłoby
  trwale przesunięte i psuło rekoncyliację księga↔venue.
  🔴 ODKRYCIE PRZY PIERWSZYCH DWÓCH FILLACH: ta sama cena referencyjna
  (zamknięcie bara 16:00) dała poślizg 0,0189% lokalnie i 0,0437% z Lambdy.
  Powód: referencją jest ZAMKNIĘCIE BARA, a zlecenie leci kilkanaście minut
  później — więc mierzyliśmy ZLEPEK dryfu rynku i prawdziwego poślizgu. Próg
  bramki C (0,02%) był pisany dla tego drugiego, więc na zlepku byłby bez sensu.
  Naprawione: `Reconciliation.drift` i `.execution_slippage` liczone osobno
  (mark price pobierana tuż przed wysłaniem, `measure_drift=True` tylko tam,
  gdzie decyzja i zlecenie są rozdzielone w czasie). Bramka C doprecyzowana:
  C1/C2 dotyczą POŚLIZGU EGZEKUCJI, dodane C6 = mediana dryfu RAPORTOWANA BEZ
  PROGU — bo dryf zależy od opóźnienia harmonogramu, a backtest go w ogóle nie
  modeluje (zakłada fill po cenie bara). Jeśli okaże się systematycznie
  niekorzystny, to osobne odkrycie o wierności backtestu.
  Suite 313 zielonych. NASTĘPNY KROK: wgrać poprawkę (0 add, 2 change), potem F7.
- 2026-08-06 (koniec sesji) — **F7: maker orders ODRZUCONE pomiarem,
  kill-switch ZBUDOWANY.**
  🔴 Zanim cokolwiek zbudowałem, zmierzyłem przesłankę maker orderów — i ona
  nie istnieje. Binance VIP 0: maker 0,1000% = taker 0,1000%, IDENTYCZNIE.
  Jedyna korzyść to nieprzechodzenie spreadu = 0,01 USDT na 64 468 = 0,000016%.
  Rocznie na $200: **$0,0004** przy 4h, wobec $4,88 prowizji — różnica 12 000×.
  A w zamian ryzyko niewypełnienia, psujące gwarancję backtest=live.
  Zaoszczędziliśmy maszynerii stanu (składanie/monitor/timeout/anulowanie/
  przecena/częściowe fille) dla korzyści czwartego miejsca po przecinku.
  ✅ KILL-SWITCH: projekt z 2026-07-25 mówił „implementacja dopiero w M6", ale
  ten sam argument, który napędził całą sesję, dotyczy go tak samo — w M6 byłby
  to świeży, nigdy nieodpalony kod pilnujący prawdziwych pieniędzy, a kanał 4h
  JUŻ składa prawdziwe zlecenia. Zbudowany teraz, na demo, za darmo.
  T1 max-DD >25% od szczytu, T2 rozjazd egzekucji >10% (mierzony z
  `price_error × qty` na fillach — plumbing, NIE strategia), T3 strata >15% w
  jednym barze (detektor awarii). Sprawdzany PRZED reconcile; przy halcie
  spłaszcza pozycję i staje. Fail-closed (wyjątek = HALT), idempotentny,
  szczyt nie pełznie w trakcie haltu, re-arm wyłącznie ręczny z `--confirm`,
  notatką i rekordem audytowym; zero auto-rearm, zero timerów.
  `PaperBot` dostał addytywne pole `extra` na stan kanałowy — 1d go nie zapisuje.
  Testy wg planu z docs/KILL_SWITCH_DESIGN §5: każdy trigger na granicy osobno
  (24,9 vs 25,1 / 9,9 vs 10,1 / 14,9 vs 15,1), halt przeżywa restart, re-arm
  resetuje szczyt, fail-closed na zepsutym stanie. Suite 334 zielonych.
  NASTĘPNY KROK: wgrać (0 add, 1 change), potem stop-loss + dzienny limit.

- **2026-08-07** — 🧾 BRAMKA C MA EWALUATOR (feat/gate-c-evaluator). Odkrycie
  sesji: fille kanału 4h żyły TYLKO w logach CloudWatch z retencją 30 dni,
  a bramka C jest rozstrzygalna po ≥20 fillach ≈ 10 miesięcy — dowody
  wyparowałyby ~9 miesięcy przed oceną. Zbudowane: (1) trwała persystencja
  w DynamoDB (`fill#<bar>#<order_id>` + `reject#<recorded_at>`; zapis w
  `finally`, przeżywa crash Lambdy; odrzucenia rejestrowane w executorze
  tylko dla POST /api/v3/order + `requested_qty` w Reconciliation);
  (2) ewaluator `gate.py --cost-fidelity` — C1–C6 z §2 doc-a bez zmiany
  progów + C0 kompletność fill-logu; <20 filli = COLLECTING (bez PASS/FAIL,
  ale łamane kryteria wymieniane z nazwy), potem FAIL > INCOMPLETE > PASS,
  brakujący dowód = SKIPPED nigdy cichy PASS; (3) backfill pierwszego fillu
  (54510109086) z CloudWatch — pola niemierzone przez stary handler jako
  None (uczciwie nieweryfikowalny dla C1/C2), lokalny test 54508851440
  celowo pominięty (spoza księgi). Werdykt na prodzie: COLLECTING 1/20.
  Deployed venue-4h miał kod sprzed rozdzielenia dryfu → zbudowany nowy zip,
  tfplan = dokładnie 1 zmiana (venue_4h hash), M5 nietknięte. Gate A po
  zmianach CLI: PASS 6/6 (regresja sprawdzona). Testy: +34 nowe, suite zielony.
- **2026-08-07b** — 🔬 RESEARCH ULEPSZEŃ (web/docs/GitHub, 3 równoległe kwerendy)
  → docs/RESEARCH_ULEPSZEN_2026-08-07.md. Ranking wg dowodów: (1) vol targeting
  (Moreira&Muir, Man Group; wersja 1-aktywowa przeżywa koszty, pasmo bez-handlu
  = parametr krytyczny), (2) ensemble prędkości EMA, (3) meta-labeler —
  architektura ✅D11 potwierdzona (stała reguła + inne cechy), ALE próba 15–20
  zdarzeń wymusza pooling BTC+ETH albo najpierw benchmark z filtra zmienności;
  mlfinlab PŁATNY → własne ~200 linii. Cechy: funding (2020-01+), ΔOI
  (2020-09+), MVRV-Z (filtr cyklu), basis z klines. Odrzucone z dowodem:
  exchange flows (rewizje=look-ahead, źródło: sam Glassnode), Fear&Greed
  (nie Granger-przyczynuje zwrotów), long/short ratio. HMM zdegradowany
  (hmmlearn martwy, ≈ próg vol, pułapka smoothed/filtered). Nic nie dotyka M5.
- **2026-08-07c** — 🛑📥🎯 SESJA "kwarantanna → ML-data → F7" (PR #37, #38, #39).
  KWARANTANNA (zaległość z audytu E2E): strażnik w konstruktorach 5 skazanych
  klas (enterprise/entry/exit/learning/brain) — silniki tworzą się nawzajem
  w metodach, więc bramkowany jest jedyny wspólny punkt; router enterprise
  lazy+503, martwa instancja w admin usunięta, fazy bootu 1/3/4-AI/7 pomijane
  (w tym AUTO-START tradingu brainem!); opt-in ENTERPRISE_ENGINES=on tylko do
  researchu; +24 testy. ML-DATA: external_data.py (funding monthly 2020-01+,
  metrics daily 2020-09+ z dedupe realnych dubli, Coin Metrics jako datowany
  IMMUTABLE snapshot + kopia w safety); pobrane: funding 7212 settlementów
  (same 8h, cap ±0,3%), snapshot 2009→2026-05 (MVRV ✅, SOPR BRAK w darmowym,
  lag 2,5 mies.). ODKRYCIE: vol targeting z rankingu researchu był już
  ODRZUCONY w M4/F2 — korekta w doc, ensemble EMA awansuje na #1. F7: pomiar
  przesłanki PRZED progami (f7_premise.py): stop 5% odrzucony, wybrane
  stop 10% close-evaluated (~2 hity/7,5r na 4h) + dzienny limit 10% (~1/rok);
  semantyka = blocked_side silnika; seam target_overlay niewidoczny dla M5;
  rekord decyzji z target + strategy_target (bramka A osądzalna); fail-closed;
  15 testów granicznych. Suite ~430 zielony.
- **2026-08-07d** — 🔬 Research po deployu F7: studium ensemble EMA
  (scripts/research/ema_ensemble_study.py, metodologia = M4/F2): AVERAGE 5
  prędkości bije baseline w OBU epokach (0,93→0,98; 2022+ 0,72→0,79; DD
  −37→−30) i 6/9 lat rok-po-roku — kandydat do harnessu M4, ale wymaga
  ułamkowych pozycji w księdze, więc bez pośpiechu; MAJORITY (0/1, tani
  w adopcji) GORSZY od baseline'u — odrzucony; szybsze membery ignorowane
  (fitting). Licznik ML: pooling BTC+ETH = 31 zdarzeń — potwierdza
  "benchmark-filtr najpierw, meta-labeler gdy urośnie próba". DANE KOMPLET:
  metrics OI dociągnięte (623 170 wierszy 5-min, 2020-09-01→2026-08-06,
  2166/2166 dni, 0 dubli; sum_open_interest 0 NaN — braki tylko w ratio
  long/short, i tak odrzuconych); funding+metrics+snapshot Coin Metrics
  zarchiwizowane w ~/TradePulse_safety/external_data_snapshots/.
- **2026-08-07e** — ✅ AUDYT E2E po sesji: suite zielony; 4 Lambdy Active
  (M5 sha nietknięte); harmonogramy 3/3 ENABLED; DLQ 3/3 puste; 1d bar
  2026-08-06 przetworzony; shadow heartbeat perfekcyjny; 4h long equity
  201,72; bramka A PASS 6/6 na prodzie; C COLLECTING 1/20; kill-switch
  nie-halted (peak 202,33). Znaleziska: (1) alarm shadow-errors = echo
  jednorazowego ImportModuleError z 2026-08-06 13:31 (ręczny invoke w trakcie
  deployu przed dopięciem warstwy pandas) — wyzerowany ręcznie z opisem;
  (2) CLI killswitch bez PAPER_STATE_BACKEND=dynamodb czyta lokalny pusty
  stan — dopisane do „Przydatne". Do potwierdzenia na starcie następnej
  sesji: pierwszy żywy przebieg F7 (16:10 UTC, bar 12:00).
- **2026-08-07f** — ✅ F7 ZWERYFIKOWANY NA ŻYWO + 🔔 naprawa kadencji alarmów.
  Przebieg 16:10 UTC (bar 12:00): `status: held`, ZERO eventów „position risk"
  = poprawne milczenie, equity 201,36 (+0,68%), killswitch czysty, 0 błędów.
  Mail z alarmu `shadow-bot-errors` (13:39 UTC) = ECHO, nie nowa awaria:
  jedyny błąd tej Lambdy to ImportModuleError z **2026-08-06 20:22:33**
  (nie 13:31 — korekta wpisu 2026-08-07e); ręczne zerowanie o 13:37:49 padło
  za wcześnie o ~7h, bo `period=86400` to okno KROCZĄCE — CloudWatch przeliczył
  99 s później, błąd wciąż w oknie, powrót do ALARM. WADA, którą to odsłoniło:
  CloudWatch ewaluuje alarm RAZ NA PERIOD, więc okno = interwał harmonogramu
  znaczy, że przy awarii dzień po dniu alarm już świeci, a stan bez TRANZYCJI
  nie wysyła maila — heartbeat zepsuty tydzień mailuje raz, nieodróżnialnie
  od jednorazówki. Naprawa (`shadow.tf`, `venue_4h.tf`): errors+DLQ 86400/14400
  → **300** (idle bucket bez datapointu + notBreaching = powrót do OK w minuty,
  każda nowa awaria = własna tranzycja = własny mail) + DWA nowe alarmy
  `-no-invocation` wg wzorca z `main.tf` (Errors nie widzi harmonogramu, który
  przestał odpalać: shadow 25×3600 breaching; venue-4h 5×3600 — między barami
  max 3 puste kubełki, więc 5 = realnie zgubiony bar przy OTWARTEJ pozycji).
  Plan: 2 add / 4 change / 0 destroy, **wyłącznie `aws_cloudwatch_metric_alarm`**
  — zero zasobów Lambda, M5 nietknięte (zweryfikowane na JSON planu). Koszt
  +$2,40/rok (2 alarmy × $0,10/mies.), budżet $7,20 → $9,60/rok.
  **Po apply (17:40:41): `shadow-bot-errors` → OK o 17:41:59, czyli 78 s
  później** — stary ALARM zgasł sam zamiast wisieć do jutra, naprawa działa.
  `venue-4h-no-invocation` → OK; `shadow-bot-no-invocation` INSUFFICIENT_DATA
  (potrzebuje 25 h historii, Lambda żyje od 08-06 20:22) — do potwierdzenia.
  sha M5 po apply: `r8Luxno…tNq0=`, LastModified nadal 2026-07-22. ✅
- **2026-08-07g** — 🔐 F5 + 🧹 M3b, oba zamknięte POMIAREM zamiast roboty.
  **F5:** AWS był już zrotowany 2026-07-16 (dzień po Fazie 0) — wyciekły
  `AKIA…UDYJX5PC` (user `Kris`) Inactive, ostatnie użycie 2025-12-27,
  **skasowany dziś**; produkcja i tak nie używa statycznych kluczy (4 Lambdy na
  rolach IAM). SECRET_KEY: **nie ma czego rotować** — monolit nigdzie nie
  wdrożony, brak lokalnego `.env`, prod odmawia startu ze słabym kluczem.
  Zostaje TYLKO klucz Binance LIVE (akcja usera). Gitleaks w CI przechodzi na
  każdym pushu. `SECURITY.md` przepisany na stan zweryfikowany (dokument
  twierdził, że nic nie zrobione). ⚠️ Klasyfikator zablokował odczyt wartości
  sekretów z historii gita — słusznie, nie obchodzono tego; nazwy są w
  SECURITY.md i to wystarczyło.
  **M3b:** premisa obalona pomiarem — `paper_trading` (produkcja) ma **3 961
  linii** i WYŁĄCZNIE importy względne, `services/`+`brain/` **39 184 linie**
  i zero powiązań z produkcją; konsumenci D1/D2 to skazany stos enterprise
  (`brain_controller`, `intelligent_exit_engine`). D1/D2 → OBSOLETE, D4 już
  zielone (`5 passed`), D5 już nie istnieje (`lifespan.py` nie ma w repo).
  Kasowanie 39 tys. linii ODRZUCONE: kwarantanna już osiągnęła cel
  bezpieczeństwa, a kasowanie zabrałoby furtkę `ENTERPRISE_ENGINES=on` na
  offline'owy research. Suite 406 zielony.
- **2026-08-07h** — 🔎 Klucz Binance LIVE obejrzany (screenshoty od usera,
  świadomie BEZ automatyzacji przeglądarki na koncie z prawdziwymi środkami).
  KOREKTA oceny z SECURITY.md: konto LIVE ma jeden klucz `TradePulseAI` i jest
  **read-only** — zaznaczone tylko `Enable Reading`, a Spot/Margin Trading,
  Withdrawals, Universal Transfer, Margin Loan i Prediction Trading są WYŁĄCZONE.
  `ENABLE_LIVE_TRADING=true` z `development.env` było flagą APLIKACJI, nigdy
  uprawnieniem Binance — aplikacja miała ustawione „handluj" kluczem, który nie
  miał do tego prawa. Realny promień rażenia = odczyt sald/pozycji/historii,
  **żadne środki nie mogły się ruszyć**. Wyciek prywatności, nie pieniędzy →
  skasowanie to higiena, nie gaszenie pożaru. Nie dało się potwierdzić, czy to
  TEN wyciekły klucz (klasyfikator blokuje odczyt wartości z historii gita,
  nie obchodzono tego) — przy read-only ta odpowiedź niewiele zmienia.
  🔴 **Przy okazji ZNALEZIONY BLOCKER M6** (patrz ramka w M6): własny komunikat
  Binance mówi, że klucz z jakimkolwiek uprawnieniem poza Reading i bez
  whitelisty IP ZOSTANIE SKASOWANY — a Lambda nie ma stałego IP. NAT Gateway
  ~$400/rok wobec budżetu $9,60/rok. Pierwszy krok: ZMIERZYĆ, czy polityka
  faktycznie gryzie, zanim cokolwiek przebudujemy.
- **2026-08-08** — ✅ Prod zweryfikowany na żywo + 🔬 ensemble EMA ODRZUCONY OOS.
  WERYFIKACJA: 3 boty chodzą (venue-4h co 4h, long 0,0031 BTC, equity 201,51
  +0,75%, killswitch czysty; 1d FLAT poprawnie; shadow round-trip OK, slippage
  ~0); wszystkie 9 alarmów OK — `shadow-bot-no-invocation` dojrzał (OK od
  2026-08-07 18:09); bramka C = 1 rekord FILLED w DynamoDB (COLLECTING 1/20).
  Tryb: czekamy i zbieramy dane. RESEARCH (M5-safe, poziom zwrotów, zero zmian
  w silniku/księdze): `ema_ensemble_oos.py` — skrining GO z 2026-08-07
  przepuszczony przez uczciwy harness (spany OOS 4 layoutów scenario_lab,
  siatka prowizji, reguła pre-rejestrowana 2026-08-08 PRZED liczbami) →
  **REJECT 2/4 checków**: przewaga tylko w layoucie (1000,250) (+0,05), reszta
  ±0,01 szumu; +32% obrotu (4,1 vs 3,1/rok) odwraca znak przy fee 0,2%;
  „DD −37→−30" z pełnej próby = artefakt punktu startu (2 layouty lepiej,
  2 gorzej). Werdykt: `docs/ENSEMBLE_OOS_2026-08-08.md` + korekta w
  RESEARCH_ULEPSZEN. Konsekwencje: pozycji ułamkowych NIE budujemy (jedyny
  powód odpadł); kolejka researchu: #1 benchmark-filtr zmienności przez ten
  sam rygor OOS. EMA20/100 przeżyło piątego pretendenta. DOMKNIĘCIE SESJI:
  PR #46 zmergowany; user SKASOWAŁ klucz LIVE `TradePulseAI` → konto LIVE
  bez kluczy, boty grają dalej na parze demo z SSM (zweryfikowane po
  skasowaniu). Lista akcji usera PUSTA — pełny tryb czekania do ~2026-09-10.
- **2026-08-08b** — 🔬 Przesłanka usera „kupuj jak spada, sprzedawaj jak
  rośnie / agresywniej, jak 6 warstw" ZMIERZONA w scenario_lab (PR #47 był
  już zmergowany): RsiMeanReversion (podręcznikowe parametry, bez strojenia)
  × {1d long, 1d L+S, 4h L+S, 1h L+S} + kontrolka. **Wszystkie 4 REJECT**:
  1d long S=0,29–0,57 (nie bije ani EMA ~1,0 ani B&H), 1d L+S zwrot
  −99…−111%, 4h L+S −99,6%, 1h L+S S=−1,3…−3,8 i −100% wszędzie (1382
  trejdy = ~276% kapitału w prowizjach). Kontrolka: checki 1–3 PASS; jej
  FAIL na DSR = artefakt puli rozdętej wariancją RSI (opisane w doc).
  Przypomnienie z audytu 6 warstw: system „widział kierunek" AUC 0,519 =
  moneta. Werdykt: mean reversion / day trading → NIE ROBIMY.
  Doc: docs/MEAN_REVERSION_2026-08-08.md. EMA20/100: pretendent #6 odparty.
- **2026-08-08c** — 🔬 Decyzja z userem: „zapożyczamy POMYSŁY z 6 warstw,
  nie kod". Przeczytany SAM KOD silników (entry 3551 l., exit 1917 l.,
  trener): 6 warstw = komitet day-tradingowy (L1 reżim, L2 LSTM 1m/5m,
  L3 odwrócenia, L4 struktura ceny, L5 momentum/pewność, L6 timing,
  hold 15 min–4 h); w trenerze widać wprost etykiety = funkcje własnych
  cech (L3: `RSI<30 lub >70`, L4: `BB ekstremum lub vol>0,02`, L5/L6:
  jawne wzory). Pierwszy zapożyczony pomysł (L1 reżim) ZMIERZONY nowym
  kodem `regime_filter_oos.py` (reguła pre-rejestrowana, spany OOS, siatka
  prowizji): **3× REJECT** — `SMA200 rising` 0,75–1,00, `price>SMA200`
  tnie Sharpe'a I pogarsza DD (−59% vs −50%!), `calm vol` (80. percentyl
  kroczący) jedyny tnie DD (−43…−45%) ale kosztuje ~0,05 Sharpe'a wszędzie
  → cecha na przyszłość, nie bramka. **Poprzeczka meta-labelera = czyste
  EMA20/100. Pretendent #7 odparty; tania część kolejki researchu
  WYCZERPANA** — dalej tylko meta-labeler (>100 zdarzeń, dziś 31) albo
  jakościowo nowa hipoteza. Doc: docs/REGIME_FILTER_2026-08-08.md.
- **2026-08-08d** — 🔓 PRÓG PRÓBY META-LABELERA OSIĄGNIĘTY. Pytanie usera
  „czy dane do nauki da się pobrać z historii?" → TAK: pre-rejestrowany
  pooling majorsów wykonany. Uniwersum wg REGUŁY (USDT spot, top-cap, bez
  stabli, ≥5 lat): +BNB/XRP/LTC/ADA/DOGE/SOL, bulk 1d do holdoutu,
  integrity 6/6 clean (pliki gitignorowane, regenerowalne). Spis zdarzeń
  (`pooled_events_census.py`): **128 wejść EMA20/100 z etykietą po
  kosztach** (>100 ✓), win rate 36%, mediana zdarzenia UJEMNA na każdym
  rynku (anatomia trend-followingu: ogon wygranych płaci za resztę) →
  metryką meta-labelera NIE może być accuracy, tylko P&L/Sharpe;
  mediana hold ~60 d → embargo splitu ≥60 d; walidacja grupowana
  (leave-one-asset-out / purged po czasie wspólnym). Doc:
  docs/POOLED_EVENTS_2026-08-08.md. Faza „czekamy na dane do nauki"
  SKRÓCONA z lat do zera — następny krok researchu: tabela cech → model.
- **2026-08-08e** — 📋 TABELA CECH META-LABELERA GOTOWA
  (`event_feature_table.py` → `data/ml/events_features.csv`, gitignored/
  regenerowalny). 128 zdarzeń × 12 cech: per-aktywo vol20/vol_pctl_1y
  (calm-vol z REGIME_FILTER jako cecha!)/trend_gap/ret20/dd_from_1y_high +
  rynkowe z BTC (proxy cyklu): btc_vol20/btc_trend_gap/funding_last/
  funding_cum30/doi7/doi30/mvrv_z (z-score w kroczących 4 latach).
  Point-in-time: cechy ze świecy SYGNAŁOWEJ (nie fillu), funding ≤ czas
  decyzji, serie dzienne shift +1 d, zero imputacji (komplet 91/128),
  inf z zerowej bazy OI → NaN. Projekt cech zadeklarowany w docstringu
  PRZED liczeniem. Doc: docs/EVENT_FEATURES_2026-08-08.md. Krok 2 (model,
  celowo OSOBNA sesja): purged split po wspólnym czasie, embargo ≥60 d,
  leave-one-asset-out, metryka P&L/Sharpe, bar = czyste EMA20/100 na M4.
- **2026-08-08f** — 📐 PROJEKT META-LABELERA PRE-REJESTROWANY po analizie
  kanonu (3 równoległe kwerendy: splity · mały-N klasyfikator · praktyka
  meta-labelingu; źródła pierwotne z URL-ami w doc). Kluczowe ustalenia:
  (1) embargo = 30 d wg h≈1%·T, NIE 60 — horyzont etykiety załatwia
  purging (korekta wcześniejszego zapisu); (2) EPV 46/12=3,8 → logit L2
  z silnym shrinkage, cechy cięte do 5 domenowo PRZED etykietami
  (mvrv_z, funding_cum30, vol_pctl_1y, btc_trend_gap, dd_from_1y_high
  + wskaźnik braków; wykluczone m.in. trend_gap własny — zero information
  advantage); (3) zero korekt balansu klas, zero CalibratedClassifierCV;
  (4) wagi próbek |net_return| + tłumienie 0,5–1,5× zamiast bramki 0/1
  (pułapka ogona trend-followingu); (5) budżet prób z MinBTL = dziesiątki
  na całe życie, dziennik prób w doc; (6) uczciwa prognoza: brak
  opublikowanego pozytywu przy N≈128, dwie pełne ewaluacje po Sharpie
  negatywne → najpewniej „zostajemy przy EMA". Doc:
  docs/METALABELER_DESIGN_2026-08-08.md. Implementacja = następna sesja,
  DOKŁADNIE wg doc.
- **2026-08-08g** — 🔬 META-LABELER WYKONANY (próby #1–#2) → **REJECT
  W TREŚCI**. Implementacja 1:1 wg pre-rejestracji (`metalabeler.py`):
  purged 4-fold (guard z 5 zadziałał: trening<90), embargo 30 d, nested
  C→0,01 we WSZYSTKICH foldach (max shrinkage = dane same mówią „pusto"),
  wagi |ret|, sizing 0,5–1,5×, LOAO, CPCV(6,2), XGB benchmark. Mechaniczna
  reguła przeszła 2/2 (+0,002 Sharpe; CPCV 4/5) — ale diagnostyka obnażyła
  artefakt: WSZYSTKIE p∈[0,60;0,95] → 0/128 stłumionych (pasmo = dźwignia
  1,3×, bo wagi |ret| windują ważony base rate do ~0,85 przy sizingu
  centrowanym na 0,5 — niespójność §2↔§3 projektu), rho(p,net_ret)=0,04
  (p=0,67), rho(p,win)=−0,01 (p=0,90) = ZERO dyskryminacji, top-5
  wygranych 5/5 flag (rangi 0,01–0,14), LOAO 3/8, XGB identycznie.
  Werdykt treściowy: cechy nie niosą sygnału przy N=128; żaden sizing nie
  naprawia zerowej dyskryminacji. Zgodne z prognozą §0 projektu. Reguła
  skorygowana OSOBNYM commitem (od #3: Spearman>0 p<0,10, ≥10% zdarzeń
  <1×, flaga=auto-REJECT). Dziennik prób: 2/kilkadziesiąt zużyte. Docs:
  METALABELER_RESULTS_2026-08-08.md. **EMA20/100 odparło pretendenta #8 —
  wszystkie sensowne ścieżki ulepszeń ZMIERZONE I ZAMKNIĘTE; projekt w
  czystym trybie zbierania danych do ≥2026-09-10.**

- **2026-08-25 — CHECK-UP CAŁEGO SYSTEMU + KANDYDAT #9 (trailing stop).**
  Check-up: 9/9 alarmów OK, 0 błędów/7 dni, 42/42 wywołań 4h, 115/115 barów
  bez luki, `CodeSha256` M5 nietknięty, harmonogramy ENABLED. Pozycja
  zweryfikowana **u źródła, nie w księdze**: konto Binance demo trzyma
  0,05309 BTC (0,05 bazowe + 0,00309 bota), 3/3 zlecenia zgodne co do ceny.
  Ceny bota = realny rynek co do centa (sygnały z `api.binance.com`).
  **Nowe fakty:** bot 1d wyszedł z flat 2026-08-22 (pierwszy sygnał od maja,
  entry 77 090,34, +2,37%) — zapis „FLAT przez całe okno" był nieaktualny;
  kanał 4h +21,04%, ale to −1,03% zaksięgowane + 22,09% niezrealizowane,
  przy buy & hold +22,47% (bot 1,43 pp ZA rynkiem); bramka C 3/20.
  **Kandydat #9 = pierwszy, którego PRZESŁANKA PRZESZŁA** (zwycięskie 1d
  szczytują +73,5%, wychodzą +33,5% → 45 pp oddane; 5/7 szczytuje >2×
  wyjścia) **i który mimo to padł.** Siatka 12 wariantów × 2 horyzonty,
  pętla symulacji zweryfikowana jako lustro silnika (`==` na floatach;
  pierwsze uruchomienie WYKRYŁO rozbieżność 90 vs 91 — brak domknięcia na
  końcu danych). Reguła pre-rejestrowana (bije na OBU horyzontach na ≥3
  sąsiednich wartościach): wspólne pasmo = **1** wartość → REJECT. Treściowo
  też: 4h@20% → 111% efektu z JEDNEJ transakcji, 1d@25% → największy
  pojedynczy efekt (−58,88%) to 1368% sumy = szum, który się skasował.
  Ciasny trailing niszczy strategię (2×ATR: 89/91 stopów, Sharpe −0,78).
  Obalona też własna przesłanka projektowa: stop NIE dokłada round-tripu
  (blokada `blocked_side` zamienia go w inne wyjście z tej samej transakcji).
  Przy okazji **F7 zweryfikowane historycznie**: 1d Sharpe 0,710→0,895 i DD
  −64,3%→−46,8%, 4h koszt 0,04 Sharpe'a — zdrowe, bez akcji.
  **Znaleziona luka wierności:** ścieżka quantity-backed nie obciąża equity
  żadną prowizją (BNB idzie poza księgę) — $0,6018 zapłacone i
  niezaksięgowane, equity 242,07 → uczciwie 241,47. Hipoteza o rabacie BNB
  OBALONA POMIAREM (realna stawka ~0,10%, model trafny co do 0,7%).
  Naprawa świadomie odłożona (bramka C w trakcie zbierania).
  Naprawione: `/api/state` → `paper.equity` liczyło `realized` zamiast
  wyceny rynkowej (zaniżało o 2,5% od 22.08) + 4 testy; suite 410 zielony.
  Docs: TRAILING_STOP_DESIGN/RESULTS_2026-08-25.md. **Bilans 9/9 odrzuconych.**
- 2026-09-04 — PEŁNY AUDYT (branch session/audit-20260904, PR #57): check-up
  100% zdrowy (A PASS 6/6, B WINDOW_RUNNING 0 RT, C 3/20, pozycje u źródła), 7
  agentów (go-live, open source, ML/trening, Binance, statystyka, 2× audyt kodu)
  + własna weryfikacja HIGH/CRITICAL. Wynik `docs/AUDIT_2026-09-04.md`: strategia
  nic do poprawy (False Strategy Theorem); ścieżka pieniędzy 2 CRITICAL + 4 HIGH
  (brak clientOrderId, order-przed-zapisem, martwe T2 — `execution_drag=0.0`
  potwierdzone w DynamoDB, sizing z konta → `cash=−1,81`, wspólny SSM); walidacja
  2 HIGH (walk-forward nigdy nie wybierał → fallback 10/50; DSR w złych
  jednostkach → 0,000). 🟢 Blocker M6 stałego IP dotyczy tylko HMAC — Ed25519
  handluje bez IP (cytat Binance FAQ). Domena odnowiona do 2027-09-28. NIC na M5
  nie ruszone; następna sesja = audyt §10.
- 2026-09-04 (cd.) — AUDYT E2E po merge PR #57 (branch session/e2e-audit-20260904,
  PR #58): 24 szwy zweryfikowane na żywo (`docs/ANALIZA_E2E_2026-09-04.md`) —
  ścieżka spójna od Binance do strony, log decyzji 51/51 + 174/174 bez luk,
  3 fille == 3 zlecenia na venue, pozycja u źródła, `terraform plan` No changes
  na obu rootach, SNS CONFIRMED + historia alarmów. Luki: E1 bramka A 1d-only
  (kanał 4h bez parytetu księgowego; FAIL = niezaksięgowana prowizja 0,1%),
  E2 publiczny origin API, E3 retry async aktywne. Fixy z 21.07 trzymają.
  Pamięć `e2e-audit-verdict` przepisana. Nic na M5 nie ruszone.
- 2026-09-05 — BEZPIECZEŃSTWO EGZEKUCJI, audyt §10 KROK 1 (branch
  session/exec-safety-20260905). Check-up 100% zdrowy przed pracą. Zamknięte:
  CRITICAL-1 (deterministyczny `newClientOrderId` + koniec ślepego retry POST +
  rozstrzyganie przez `origClientOrderId`/`myTrades`), CRITICAL-2 (skan sierot
  przed decyzją, „wytłumaczone" = id ostatniego zapisanego bara, znacznik jedzie
  w każdym czystym runie, zasiew też skanuje), HIGH-1 (T2 liczy drag PO stepie —
  ożył), HIGH-2 (rekoncyliacja fail-closed w obie strony), HIGH-3 (własny prefix
  SSM + `BINANCE_BASE_URL` z env, klucze bez „DEMO"), MEDIUM-3
  (`reserved_concurrent_executions=1` + `state_version` z warunkowym zapisem),
  MEDIUM-4 (halt zapisany przed flattenem, klucz `halt@<bar>`), E3 (jawny
  `event_invoke_config`, 0 retry). 30 nowych testów pisanych pod awarię,
  mutacja 5/5 złapanych, suite 444 zielony, złoty wzorzec księgi bez zmian.
  Weryfikacja na żywo tylko do odczytu (myTrades zwraca prowizję co do cyfry jak
  w logu fillów; dry-run `attach_venue` na realnej księdze przechodzi).
  `terraform plan` 2 add / 2 change / 0 destroy, zero zasobów M5.
  Docs: `EXECUTION_SAFETY_2026-09-05.md`. Księga v2 (HIGH-4) świadomie następna.
