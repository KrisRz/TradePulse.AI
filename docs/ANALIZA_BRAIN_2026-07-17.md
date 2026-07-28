# Analiza modułu brain — 2026-07-17

> Audyt `app/backend/brain/` (brain_controller.py 1312, brain_events.py 382,
> brain_state.py 293, io/market_data.py 539, io/audit_logger.py 536) + wpięcie
> (core/container.py, core/application.py, core/brain_state_store.py, api routes).
> Kontekst: żywy bot paper (Lambda) NIE importuje brain; silniki enterprise, które
> brain „orkiestruje", są przeznaczone do wygaszenia (docs/ANALIZA_6_WARSTW_2026-07-17.md).

## WERDYKT

**Brain to fasada.** Reklamowany 7-krokowy pipeline (`brain_controller.py:9`) jest w całości
martwym kodem. Realny cykl (`_execute_trading_cycle`, `:495-549`) robi 3 rzeczy: sprawdza
`day_trading_engine.is_running`, liczy aktywne pozycje, inkrementuje licznik. ~50 linii
logowania statusu owinięte w 1300 linii ceremonii. Decyzja D2 (brain=monitor, engine=egzekucja)
została ZADEKLAROWANA, ale nie wykonana — kontroler nadal nosi cały martwy stack egzekucji
(`:663-910`), własną instancję IntelligentExitEngine (`:192`) i duck-typing w internals silników.

## Kluczowe defekty

**Krytyczne (gdyby brain był nośny):**
- **C1 Zombie RUNNING:** po >10 błędach pętla robi `break` BEZ zmiany stanu (`:478-482`) —
  API raportuje żywy brain z martwą pętlą. `_handle_emergency` odpala transition przez
  `create_task` z synchronicznego callbacku (`:335-338`) — może nigdy nie wykonać.
- **C2 Stany terminalne bez wyjścia:** HALT/ERROR → nic; `start_trading` wymaga WARMUP,
  `initialize` wymaga INIT — po stopie/błędzie brainu nie da się zrestartować.
- **C3 Wyścig singletona + trwała degradacja:** `get_brain_controller` bez locka (`:1274-1307`),
  nieudany init cachuje NIEZAINICJALIZOWANY obiekt (nigdy nie retry); application.py:319-348
  tworzy DRUGĄ instancję obok singletona (w procesie mogą żyć 2-3 brainy).
- **C4/C5:** niezainicjalizowany brain → AttributeError w `get_status()`; `self.entry_engine`
  nigdzie nie przypisany, a używany (`:679,:691`) — dowód, że pipeline entry nigdy nie działał.
- **Audyt cyklu = NameError:** `_audit_cycle` woła `write_decisions` bez importu (`:926`),
  wyjątek połykany (`:933`).

**Persystencja:**
- **P1 (WARTE NAPRAWY NIEZALEŻNIE):** `brain_state_store.py:150` hardcoduje
  `DynamoDBClient(local_development=True)` w ścieżce zapisu — na AWS zapis idzie do lokalnego
  endpointu, odczyt do właściwego. Store jest w `core/` i jest UŻYWANY dziś (application.py,
  routes/trading.py).
- P2: cache mutowany przed zapisem DB — po nieudanym zapisie serwowany stan-widmo.
- P3: naiwne `utcnow()` w store vs tz-aware w brain. Bogaty stan FSM brainu NIE jest
  persystowany nigdzie (restart = amnezja); DynamoDB trzyma tylko flagę {enabled, start_time}.

**io/ (0 importerów — osierocone):**
- market_data.py: init ZAWSZE crashuje na connectivity-test (KeyError — test przed
  wypełnieniem `source_stats`, `:121-138`), circuit breaker jednokierunkowy (nigdy nie
  odzyskuje źródła, `recovery_timeout` zadeklarowany i nieużywany), RateLimiter bez locka.
- audit_logger.py: bufor rośnie bez limitu przy awarii DB, synchroniczne boto3 w async,
  task flush bez referencji i bez cancel.

**System eventów = ceremonia:** 3 subskrypcje (2 to log-stuby), publisherzy odpalają
z martwych ścieżek, historia w pamięci bez konsumenta, `list.pop(0)` O(n). Typowane modele
eventów ładne — dla zerowej publiczności.

**Testowalność:** zero — singletony wołane wewnątrz metod, realne timery (3 min warmup),
brak wstrzykiwanego zegara/danych, żaden test nie dotyka brainu. FSM bez tabeli przejść.

## Rekomendacje

**(a) Naprawiać tylko jeśli brain przeżyje** (nie wydawać wysiłku inaczej): tabela przejść FSM
+ krawędzie recovery, jedna ścieżka tworzenia z lockiem, nie cachować nieudanych initów,
głośne błędy zamiast blanket except.

**(b) ZACHOWAĆ / przenieść do przyszłej architektury meta-labeling:**
- `BrainStateStore` (z fixami P1–P3) — wzorzec „flaga enabled + bariera startowa" jest
  idealny dla bota Lambda-cron. **P1 naprawić od razu, bo działa dziś.**
- Koncept FSM (INIT/WARMUP/RUNNING/HALT) — przepisać jako ~100-liniowy table-driven.
- Modele Pydantic decyzji (`TradingSignal`, `RiskContext`, `EntryAnalysis`, `ExitAnalysis`,
  brain_state.py:111-153) — gotowe kontrakty dla „sygnał EMA → filtr ML → wynik → audyt".
- Schemat rekordu audytowego (audit_logger.py:96-149) — jako szablon; implementację
  napisać cienką od nowa.
- Kształt `get_status()` jako szablon endpointu statusu.

**(c) SKASOWAĆ:** cały martwy pipeline w kontrolerze (~600 linii `:551-934`, `:988-1174`),
`brain/io/` w całości (0 importerów, zepsute), `brain_events.py` (383 linie dla 3 log-stubów),
ściany printów i choreografię sleep(1/2/3) w application.py.

**Konkluzja:** gdy silniki enterprise odchodzą, jedyna żywa funkcja brainu — logowanie
„engine is running" co 15 s — odchodzi z nimi. Racjonalny ruch: (c)+(b) — skasować moduł,
zostawić BrainStateStore (fix P1 teraz), a ideę FSM + modele decyzji + schemat audytu
przenieść do małego, celowego orchestratora bota meta-labeling po M5.
