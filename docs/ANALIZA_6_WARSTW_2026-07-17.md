# Głęboka analiza systemu 6 warstw — 2026-07-17

> Audyt 4 równoległych agentów: silnik entry (`intelligent_entry_engine.py`, 3551 linii),
> silnik exit + orchestrator (`intelligent_exit_engine.py` 1917 + `enterprise_trading_engine.py` 2609),
> pipeline ML (trenery, `ml/`, artefakty), oraz research best practices
> (oficjalne docs scikit-learn/TensorFlow/AWS/Google, prace Bailey & López de Prado,
> Harvey et al., Makridakis et al., Hyndman).
>
> Kontekst: żywy bot paper gra **czystą EMA20/100 1d** (decyzja ❓D9) i jest w oknie M5
> (bez zmian strategii do ≥2026-09-10). System 6 warstw jest **uśpiony** — nic poniżej
> nie dotyka żywej strategii.

---

## WERDYKT

System 6 warstw (~10 tys. linii) **nie działa uczciwie end-to-end** i nie nadaje się do
naprawy warstwa-po-warstwie. Audyt potwierdza i wzmacnia decyzję ❓D9: to nie tylko
horizon mismatch — metryki modeli są tautologiczne lub przeciekowe, kluczowe mechanizmy
bezpieczeństwa są martwe przez bugi, a finalna pewność decyzji w ogóle nie pochodzi z warstw.
Rekomendacja strategiczna: **nie naprawiać — zbudować mały, testowalny moduł od nowa**
(meta-labeling nad EMA), a silniki enterprise wygasić/kwarantanna.

---

## 1. Decyzje nie są tym, czym się wydają (aggregacja)

- **Entry: wynik 6 warstw jest ODRZUCANY.** Finalna pewność = pewność sygnału z upstreamu
  (`intelligent_entry_engine.py:2546,2557,2614`). Konsensus liczy widmową 7. „warstwę"
  `microstructure` jako wieczny głos „wait" z pewnością 0 (`:1420, :2234-2249`).
  `consensus_score` = średnia TYLKO głosujących „enter" (selection bias, `:2261-2263`);
  fast-track nie wymaga większości (`:2554`).
- **Exit: trailing stop i progresywne cięcie strat NIGDY nie działają.** Bug kolejności
  merge słownika: `{"should_exit": True, ..., **exit_decision}` — stary `should_exit: False`
  nadpisuje `True` (`intelligent_exit_engine.py:606-612`). Cała nakładka (4 progi strat,
  siatka 6h) jest liczona i wyrzucana.
- **Exit: próg stop-loss ≈ 0** przez podwójne dzielenie ATR (ratio dzielone ponownie przez
  entry_price, `IEE:1394`, `exit_engine_config.py:230`) — L6 głosuje exit 0.98 przy
  każdej mikroskopijnej stracie; progi zysku spadają do 0.02–0.10% (poniżej prowizji).
- **Exit: PnL liczony long-only** (`IEE:1365`) — wygrywający short natychmiast „łapie stop".
- **Bramka 60 s** na początku pozycji blokuje też awaryjny SL (`IEE:480-491`).
- Wagi warstw: dwie sprzeczne tabele ręcznie strojone „na oko", zero kalibracji z danych;
  klucz `layer_4_filters` nie pasuje do `layer_4_technical` (ciche fallbacki).
- Błąd warstwy → cichy neutralny głos (entry: `{"wait", 0.0}`; exit: wykluczenie z głosowania)
  — martwa warstwa jest nieodróżnialna od analizy; brak kworum/health-gate.

## 2. ML, które nie jest ML (pipeline treningu)

- **Etykiety cyrkularne:** w `6layer_enterprise_trainer.py` 5 z 6 warstw ma etykiety będące
  deterministyczną funkcją własnych cech wejściowych (L1 `:216-228`, L3 `:353-366`,
  L4 `:415-427`, L5 `:476-491`, L6 `:541-563`). „Accuracy 0.9999" = odtwarzanie reguł,
  zero informacji o przyszłości.
- **Przeciekowe splity:** retrenery używają `train_test_split(shuffle=True)` na próbkach
  co 15 min z etykietami patrzącymi 1–6 h w przód (`retrain_layer5_enhanced.py:280-282`) i na
  danych z DUPLIKATAMI wierszy per-lookahead (`retrain_exit_layer3_simulated.py:112-115`).
  Deklarowane metryki (L3 AUC 0.80) są zawyżone z konstrukcji. `TimeSeriesSplit`
  zaimportowany, nigdy nie użyty. Brak walk-forward/purging/embargo w całym repo.
- **Jedyna uczciwa liczba jest miażdżąca:** LSTM 1m/5m mają **AUC ≈ 0.519** (rzut monetą)
  wg własnych metadanych — i są wdrożone.
- **LSTM w runtime dostaje 200× powieloną bieżącą świecę** zamiast sekwencji
  (`enterprise_trading_engine.py:891-895`; w exit dodatkowo z szumem `np.random` →
  niedeterminizm), z cechami o złych semantykach, bez scalera.
- **Bug jednostek L5 żyje dalej w L1/L3/L4/L6:** runtime `_get_market_features`
  (`ETE:579-633`) podaje close jako ratio (trening: USD), MACD histogram (trening: linia w USD),
  inne formuły volatility/trend_strength. Scalery poza L5 w praktyce nigdy nieaplikowane
  (klucze `regime_classifier`/`technical_filters` vs `layer_4`/`layer_5`).
- **Dekodowanie klas L1 przestawione** (`ETE:707`) — bear raportowany jako bull
  (kolejność alfabetyczna XGB vs ręczna lista).
- **Exit L3: wynik modelu ML jest liczony i WYRZUCANY** — rekomendację buduje licznik reguł
  (`IEE:1149-1254`). Z 6 „modeli AI" w exit realnie odpalany jest 1, a jego output ignorowany.
- Brak bramki promocji modeli (retrain → nadpisz plik → restart), brak oceny PnL/Sharpe
  po kosztach, artefakty mutowalne bez wersjonowania (3 sprzeczne metadane L5),
  `scaler_persistence.py` = ręcznie wymyślone parametry udające treningowe.

## 3. Martwe mechanizmy bezpieczeństwa i inne twarde bugi (entry)

- Cooldown re-entry martwy: nieistniejący `EntryReason.WAIT_FOR_CONFIRMATION` + złe kwargs,
  wyjątek połknięty na debug (`:788-799`).
- Downtrend protection „działa" przez crash (TypeError), nie by design (`:997-1011`).
- Ścieżka „wait_for_better_price" crashuje (nieprawidłowa wartość enuma, `:2535`).
- Adaptacja progów permanentnie zepsuta (`self._default_thresholds` niezdefiniowane, `:528-542`).
- L4 nie zna kierunku sygnału — głosuje „enter" na setupie niedźwiedzim przy BUY (`:1909-1951`).
- L6 stosuje godziny 9–16 czasu lokalnego serwera do BTC 24/7 (`:2129-2130`).
- L1: percentyle ATR w skali dziennej vs dane 1m → reżim prawie zawsze RANGING_LOW_VOL;
  cała „adaptacyjna" konfiguracja zdegenerowana do stałych (`:1446`, config `:84-89`).
- Kelly: podłoga 2% pozycji nawet przy zerowym/ujemnym edge (config `:395`), optymistyczne
  priory (55%/2.5%/1.5%) bez historii; Sharpe √252 na trejdach intraday.
- Walidatory historyczne: indeksy przesunięte o ~14/~19 barów (wyniki mierzone na złych
  świecach), świeczki „walidowane" hardcoded tabelą; fabrykowane metryki
  (`average_confidence: 0.75`, uptime „100%").
- Wyścigi: współdzielony stan `self._last_filter_passed` / `current_dynamic_thresholds`
  między współbieżnymi wywołaniami; `initialize()` bez locka; nieograniczony wzrost
  `_rev_hits`; modele LSTM ładowane z dysku przy KAŻDEJ analizie.

## 4. Benchmark vs kanon (best practices, źródła oficjalne)

**Architektura odwraca kanoniczne priorytety:** ciężka w warstwy predykcyjne (gdzie wg
literatury edge najmniejszy, ryzyko overfittingu największe), lekka w walidację i kontrolę
ryzyka (gdzie największy zwrot z wysiłku).

| # | Praktyka | Werdykt | Wysiłek |
|---|---|---|---|
| 1 | Risk overlay: vol targeting + ułamkowy Kelly cap + wyłącznik max-DD (Harvey et al. SSRN 3175538) | ADOPTUJ | niski (~50 linii, zero ML) |
| 2 | Dane treningowe 3 mies. → 3–5+ lat (Binance darmowe; MinBTL: krótkie okno + wiele prób ⇒ fałszywe edge, AMS 2014) | ADOPTUJ | niski |
| 3 | Walk-forward `TimeSeriesSplit(gap≥horyzont)` — embargo nienegocjowalne (sklearn docs; de Prado ch.7) | ADOPTUJ | niski |
| 4 | Audyty LSTM: target = log-returns nie ceny; scaler fit tylko na train; baseline persystencji (TF tutorial; Makridakis PLOS ONE) | ADOPTUJ | niski |
| 5 | Lekki MLOps: wspólny moduł cech train+serve (wzór `ml/l5_features.py`), artefakty wersjonowane hash+git SHA, okno paper jako shadow test | ADAPTUJ | średni |
| 6 | Deflated Sharpe / MinTRL jako bramka po oknie M5 (Bailey & de Prado, SSRN 2460551) | ADAPTUJ | niski |
| 7 | Meta-labeling: EMA jako model pierwotny (strona), JEDEN meta-model uczony „czy sygnał EMA zarobi" → gate/size; reszta warstw = cechy, nie głosy | PO M5 | wysoki |
| 8 | Reżim: HMM 2–3 stany na returns+volatility (`hmmlearn`, ~20 linii) zamiast ręcznego klasyfikatora bez obiektywnych etykiet | PO M5 | średni |
| 9 | Pełny purged K-fold/CSCV/PBO, feature story, SageMaker/Vertex | POMIŃ | przerost dla 1-os. bota |

Kluczowa obserwacja architektoniczna: ważona średnia 6 heterogenicznych score'ów
**miesza** błędy zamiast je **bramkować**; wagi między warstwami to wolne parametry
zawyżające licznik prób (problem overfittingu backtestu). Kanon (de Prado, meta-labeling):
sygnał pierwotny → jeden dobrze postawiony klasyfikator binarny → prawdopodobieństwo
steruje rozmiarem. To zbiega 6 strojonych wag do jednego uczciwego modelu.

## 5. Plan działania (zgodny z oknem M5)

### TERAZ (nie dotyka żywej strategii — dozwolone w M5)
1. **Decyzja porządkowa:** silniki enterprise oznaczyć jako kwarantanna/legacy
   (nie ładować w żadnej żywej ścieżce; upewnić się, że Lambda ich nie importuje — dziś nie importuje).
2. **Przygotować bramkę oceny okna M5:** skrypt DSR/MinTRL (1 strona numpy) do oceny
   wyników paper po 2026-09-10, z pre-rejestrowanymi progami (już w plan.md: maxDD ≤25%,
   PF ≥1.3, net P&L >0, tracking error <10%).
3. **Rozszerzyć dane historyczne** do pełnej historii Binance (1d + 1h) — za darmo,
   fundament pod przyszłe M4/F4.
4. **Zaprojektować risk overlay pod M6** (vol targeting + cap + kill switch) — uwaga:
   F2 w M4_EDGE_VALIDATION pokazał, że vol targeting na 1d PSUJE risk-adjusted return
   w reżimie 2022+ — więc z overlay zostawić na start tylko **wyłącznik max-DD** (kill switch),
   resztę traktować jako opcję do zbadania na tym samym harnessie walk-forward.

### PO M5 (M4/F4, gated na dowodach)
5. **Nie naprawiać 10 tys. linii.** Jeden eksperyment: meta-labeler nad EMA
   (cechy 1d, target 1d „czy sygnał EMA zarobi po kosztach"), purged walk-forward z embargo,
   promocja tylko jeśli bije czystą EMA na harnessie z M4. Reżim jako cecha z HMM.
6. Jeśli eksperyment wygra → przenieść do produkcji wzorcem `ml/l5_features.py`
   (wspólny moduł cech + test kontraktu) i przepuścić przez własne okno paper (shadow).
7. Jeśli przegra → skasować silniki enterprise na dobre; czysta EMA + risk kill switch.

---

*Raporty źródłowe agentów (pełne, z cytowaniami plik:linia i URL): sesja Claude 2026-07-17.
Wszystkie twierdzenia o kodzie mają cytowania plik:linia zweryfikowane na main @ 9068232.*
