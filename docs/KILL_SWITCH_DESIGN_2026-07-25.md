# Projekt kill-switcha max-DD pod M6 — 2026-07-25

> Zadanie z planu (M5-safe, pkt 3 listy TERAZ audytu 6 warstw): ZAPROJEKTOWAĆ
> wyłącznik max-DD pod realne pieniądze (M6). **Sam projekt — implementacja
> dopiero przy przejściu do M6.** NIE wdrażać do paper bota w oknie M5:
> wyłącznik zmieniłby mierzone zachowanie (halt ≠ strategia) i unieważnił pomiar.
>
> Kontekst z M4/F2: vol targeting na 1d PSUJE risk-adjusted return w reżimie
> 2022+ — dlatego z całego risk-overlay zostaje na start TYLKO kill-switch;
> reszta (sizing) to opcja do zbadania na harnessie walk-forward po M5.

## 1. Po co jest ten wyłącznik (uczciwie)

Kapitał M6 to $50–100 — strata jest trywialna. Wyłącznik NIE chroni pieniędzy.
**Wyłącznik unieważnia eksperyment, gdy rzeczywistość wychodzi poza kopertę,
która zakwalifikowała strategię:** bramka M5 wymaga paper max DD ≤ 25%; jeśli
live przekracza tę kopertę, przesłanka „live zachowuje się jak paper/backtest"
jest złamana → stop, powrót do paper (Bramka 4 planu §7 działa w obie strony).

## 2. Dowody z danych (silnik repo, dane zwalidowane 2026-07-25)

EMA20/100 long-only, 1d, koszty 0.1%+2bps, 2017-09→2026-07-15 (3240 barów,
final equity 6.94×):

| Metryka | Wartość |
|---|---|
| Max DD (pełny cykl) | **−64.3%** (2018; underwater 1066 dni) |
| 2. najgłębszy epizod | −49.7% (1034 dni) |
| Epizody DD > 25% | 4 w ~9 lat |
| Epizody DD > 30% | 3 w ~9 lat |
| Max DD w pojedynczym roku | −60% (2018) … −10.7% (2026 YTD) |
| Najgorszy 1 dzień | −19.5%; p99 dni stratnych −7.2% |

Wnioski projektowe:
- Kill @ 25% **odpaliłby 4× w 9 lat** — dla wieloletniego bota to „normalna"
  praca strategii, ale dla kilkumiesięcznego etapu M6 = rzadkie zdarzenie,
  którego wystąpienie faktycznie oznacza wyjście poza kopertę bramki.
- Jednodniowy limit straty ~15% to zdarzenie ogonowe (worst 19.5%, p99 7.2%)
  — dobry detektor błędu egzekucji/API, nie normalnej zmienności.
- **Otwarta konsekwencja dla Bramki 4 (skalowanie):** przy horyzoncie lat
  strategia historycznie schodzi dużo głębiej niż 25%. Decyzja o skali musi
  zrewidować próg albo rozmiar ekspozycji (należy do ❓D12) — nie zamiatamy
  tego pod dywan.

## 3. Triggery (trzy, wszystkie pre-definiowane przed startem M6)

| # | Trigger | Próg | Uzasadnienie |
|---|---|---|---|
| T1 | **Max DD od szczytu equity liczonego OD STARTU M6** | **> 25%** | spójny z pre-zarejestrowaną bramką §3; „koperta złamana" |
| T2 | **Rozjazd live vs paper** (ten sam bar, ta sama księgowość) | **> 10%** odchylenia P&L | Bramka 3 planu §7 wymaga tego wprost; mierzy jakość egzekucji/kosztów, nie strategię |
| T3 | **Dzienny limit straty** (close→close equity) | **> 15%** w 1 bar | detektor awarii (błąd API, zły fill, fat-finger) — poza p99 normalnej pracy |

Zadziałanie DOWOLNEGO triggera ⇒ HALT. Progi to stałe w kodzie (jak w
`gate.py`), zmiana progu = commit z uzasadnieniem, nigdy „w locie".

## 4. Mechanika w architekturze Lambda-cron (szkic implementacji)

Rozszerzenie stanu w DynamoDB (item `state`, nowe pola — zero nowych tabel):

```json
{
  "halted": false,
  "halt_reason": null,          // "T1_MAX_DD" | "T2_TRACKING" | "T3_DAILY_LOSS"
  "halted_at": null,            // ISO UTC
  "m6_peak_equity": 10000.0,    // szczyt od startu M6 (dla T1)
  "m6_start_equity": 10000.0,
  "prev_bar_equity": 10000.0    // dla T3
}
```

Przepływ w `step()` (kolejność jest częścią projektu):

```
1. jeśli halted → NIE handluj; zwróć {"status": "HALTED", reason, ...}
   (idempotentnie, każdy kolejny cron też) + przypomnienie SNS raz dziennie
2. pobierz bar, policz equity MTM (istniejąca księgowość PaperPortfolio)
3. sprawdź T1/T2/T3 NA STARYM stanie (przed reconcile!)
4. trigger? → (a) flatten pozycji po bieżącym close (ta sama ścieżka
   reconcile(0)), (b) zapisz halted=true + reason + decyzję do logu
   (load-bearing, jak dziś), (c) ALARM SNS (nowy komunikat, istniejący topic),
   (d) koniec — bez nowego wejścia
5. brak triggera? → normalny reconcile; zaktualizuj m6_peak_equity,
   prev_bar_equity
```

**Re-arm wyłącznie manualny:** `python -m app.backend.paper_trading.run rearm
--confirm` — kasuje `halted`, resetuje `m6_peak_equity` do bieżącego equity,
dopisuje rekord audytowy `rearm#<ts>` (kto/kiedy/dlaczego w polu note).
Żadnego auto-rearm, żadnego timera.

Własności wymagane:
- **Fail-closed:** wyjątek w ewaluacji triggerów = traktuj jak trigger
  (HALT + alarm), nigdy „nie umiem policzyć → handluję dalej".
- **Idempotencja:** wielokrotny cron po halcie nie zmienia stanu (poza
  heartbeatem statusu) — dokładnie jak dzisiejszy `skipped`-path.
- Zero nowych zależności, zero nowych zasobów AWS (stan w istniejącej tabeli,
  alarm na istniejącym SNS). Dashboard statusu pokazuje HALTED na czerwono.

## 5. Plan testów (przed wdrożeniem w M6)

1. Unit: każdy trigger osobno (syntetyczne equity: DD 24.9% vs 25.1%; rozjazd
   9.9% vs 10.1%; dzień −14.9% vs −15.1%) + kolejność „check przed reconcile".
2. Unit: halt jest trwały (restart z DynamoDB → dalej HALTED), re-arm resetuje
   peak, rekord audytowy powstaje.
3. Unit: fail-closed (wstrzyknięty wyjątek w ewaluacji → HALT, nie trade).
4. E2E paper: wymuszony trigger na koncie paper (osobny pk, np.
   `BTCUSDT_1d_killtest`) → flatten + alarm SNS dochodzi mailem.
5. Equivalence: z wyłączonym (nie-strzelającym) kill-switchem wynik identyczny
   z dzisiejszym botem co do 1e-6 (istniejący test parytetu rozszerzony).

## 6. Czego świadomie NIE robimy

- **Vol targeting / dynamiczny sizing** — F2 (M4_EDGE_VALIDATION): psuje 1d
  w reżimie 2022+. Wraca najwyżej jako eksperyment na harnessie po M5.
- **Trailing tighten / stopnie DD** — audyt 6 warstw pokazał, dokąd prowadzi
  ręcznie strojona drabinka progów. Jeden próg, jedna semantyka.
- **Auto-rearm / cooldown** — powrót do gry po halcie to decyzja człowieka
  przy danych (dlatego rearm ma `--confirm` i rekord audytowy).
- **Wdrożenie w oknie M5** — patrz nagłówek.

## 7. Otwarte punkty (do rozstrzygnięcia PRZY implementacji M6, nie teraz)

- ❓ T2 wymaga równoległego paper-tracka w M6 (ten sam sygnał, wirtualne
  konto) — de facto już istnieje: paper bot po prostu dalej działa obok
  realnego; trzeba tylko porównywać te same bary.
- ❓ Czy T1 liczyć od startu M6 (projekt powyżej), czy all-time — od startu
  jest spójne z „kopertą bramki", all-time surowsze; decyzja przy D12.
- ❓ Realny broker-side stop (OCO na Binance) jako obrona, gdy Lambda nie
  wstanie — osobny mechanizm, rozważyć w F7 razem z maker orders.
