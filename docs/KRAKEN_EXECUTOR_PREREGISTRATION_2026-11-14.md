# Executor Krakena i test minimalnymi zleceniami — PRE-REJESTRACJA (2026-11-14)

> Wiążące od commita tego dokumentu. Zasady można zaostrzyć przed danymi, **nigdy
> poluzować**. Każda zmiana to nowy dokument i decyzja usera.
> Uzupełnia `docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md`; **P1–P4 pilota bez zmian**.
> Podstawa: `docs/BOT_DEEP_ANALYSIS_2026-10-30.md` §5–6, decyzje usera 2026-11-14.

## Po co

Kraken nie ma sandboxa spot. Kod składający zlecenia nie może pierwszy raz zadziałać
na £200 pilota. Dlatego executor sprawdzamy na prawdziwej giełdzie **najmniejszymi
możliwymi zleceniami**, niezależnie od P3 (P3 zależy od rynku, nie od jakości kodu).
Ten test nie mówi nic o rentowności i nie jest startem pilota.

## Pieniądze i klucz (decyzje usera — do potwierdzenia kwoty)

- Wpłata testowa: **£10** (decyzja usera 2026-11-14, wpłacone tego dnia; pierwotnie
  proponowane £20). Budżet straty testu: **£3**. Przekroczenie = stop i raport.
- Jeden klucz API: saldo, zlecenia otwarte i zamknięte, składanie i anulowanie
  zleceń. **Bez wypłat, bez wpłat, bez eksportu.** W SSM jako SecureString:
  `/tradepulse/kraken/key`, `/tradepulse/kraken/secret`. Klucz nigdy w czacie,
  w repo ani w logach.
- ~~Wpłata dopiero po T0~~ User wpłacił przed T0 (2026-11-14). Zasada, która z tego
  zostaje: **żadne prawdziwe zlecenie nie wychodzi przed PASS na T0.**

## Zasady executora (R)

| # | Zasada |
|---|---|
| R1 | Start każdego przebiegu: klucz **nie ma prawa wypłat** (sprawdzone w API) — inaczej stop bez zlecenia. |
| R2 | Przed handlem `SystemStatus == online`; inny stan = brak zlecenia, ponowienie w następnym przebiegu, zapis `reject`. |
| R3 | Limity pary (`ordermin`, `costmin`, krok ceny i ilości) czytane z `AssetPairs` przy każdym przebiegu; opłata z `TradeVolume`. Zlecenie poniżej minimum nie wychodzi. |
| R4 | **Idempotencja po naszej stronie.** Id klienta wyprowadzone z (kanał, bar, cel), ≤ 18 znaków, prefiks `tpk`. Przed wysłaniem: szukanie tego id w `OpenOrders` **i** `ClosedOrders`. Znalezione = księgujemy istniejące, nie wysyłamy drugiego. |
| R5 | Każde zlecenie ma `deadline` (≤ 60 s). Timeout albo błąd sieci = stan nieznany → wyszukanie jak w R4, nigdy ślepe ponowienie. |
| R6 | Zlecenia handlowe: **market** (taker 0,80%), kupno w kwocie GBP z gotówki księgi, sprzedaż w ilości BTC z księgi. Post-only to osobny kandydat. |
| R7 | Twardy budżet: po zleceniu udział BTC w equity konta ≤ **0,65**; pojedyncze zlecenie ≤ `VENUE_MAX_NOTIONAL`. Przekroczenie = zlecenie nie wychodzi. |
| R8 | **Awaryjny stop na giełdzie:** po każdym wejściu i każdej korekcie zlecenie `stop-loss` (market, trigger `last`) na całą ilość BTC bota, **20% poniżej ceny wejścia**. F7 (10% na zamknięciu dnia) dalej decyduje jak w backteście. |
| R9 | Kolejność przy korekcie i wyjściu: **anuluj stop → potwierdź anulowanie → handel → nowy stop** (przy wyjściu bez nowego). Pozycja bez stopu dłużej niż jeden przebieg = alarm. |
| R10 | `CancelAllOrdersAfter` **nie jest używane** (skasowałoby stop). |
| R11 | **Uzgodnienie na starcie przebiegu:** saldo BTC i GBP na giełdzie vs księga (±1 krok ilości), otwarte zlecenia vs oczekiwany stop. Stop wykonany między przebiegami = księgujemy fill z `ClosedOrders`, stan FLAT, wejście zablokowane do powrotu sygnału do 0 (reguła F7). Rozjazd niewyjaśniony = halt i alarm. |
| R12 | Każdy fill: cena, ilość, opłata i waluta opłaty z giełdy, zapis `fill#` w DynamoDB, wiersz w eksporcie HMRC (GBP). |
| R13 | Bot rusza tylko swoją ilość z księgi. Nigdy nie sprzedaje „całego salda”. |

### Stop awaryjny — co zmierzone przed zapisem (dane < 2026-07-16, BTC 1d)

W 15 transakcjach 2017–2026 stop giełdowy zadziałałby przed F7 albo sygnałem:
przy 12% — 4 razy, przy 15% — 2 razy, przy **20% — 1 raz** (2018-01-16: dołek dnia
−27%, zamknięcie −12,4%). 20% znaczy więc: w zwykłych dniach bot = backtest, giełda
chroni tylko przy załamaniu albo awarii bota. Koszt tej polisy w jedynym
historycznym przypadku: wyjście po −20% zamiast −12,4% na pozycji (3,8 pkt proc.
konta przy `w = 0,5`). Przyjęte świadomie.

## Test — kryteria (wszystkie muszą być PASS)

| # | Co | PASS gdy |
|---|---|---|
| **T0** | Bez pieniędzy: klucz, podpis, `validate=true` | brak prawa wypłat potwierdzony; saldo czytane; kupno, sprzedaż i stop-loss przyjęte w trybie `validate`; zły podpis i zły nonce dają czytelny błąd, bez ponowień w pętli |
| **T1** | Kupno market ~£5 | fill zapisany; opłata w księdze = opłata w historii Krakena (±£0,01); BTC w księdze = saldo (±1 krok) |
| **T2** | Stop awaryjny po kupnie | widoczny w `OpenOrders` z naszym id, na całą ilość, trigger −20% |
| **T3** | Idempotencja | powtórzony przebieg tego samego baru nie tworzy drugiego zlecenia (liczba zleceń na giełdzie bez zmian) |
| **T4** | Przerwany przebieg | zlecenie wysłane, zapis lokalny celowo pominięty → następny przebieg znajduje je po id i księguje **raz** |
| **T5** | Korekta | anuluj stop → zlecenie ≥ £5 → nowy stop na nową ilość; ani chwili z dwoma stopami |
| **T6** | Stop, który zadziałał | stop ustawiony 0,3% pod ceną; po wykonaniu następny przebieg księguje fill z giełdy, stan FLAT, wejście zablokowane. Brak wykonania w 72 h = powtórka, nie PASS |
| **T7** | Wyjście | anuluj stop → sprzedaż całej ilości bota → 0 otwartych zleceń, BTC bota = 0 (pył < `ordermin` dozwolony i zapisany) |
| **T8** | Eksport HMRC | każdy fill z T1–T7 w eksporcie, kwoty w GBP, suma opłat = historia Krakena |

- Dowolny FAIL = stop, naprawa z testem, **powtórka od T1**.
- Łączna strata > £3 = stop i raport.
- Po PASS: raport `docs/KRAKEN_EXECUTOR_RESULTS_<data>.md` z id zleceń i zrzutem
  salda. Reszta wpłaty zostaje na koncie do pilota albo wraca do banku (decyzja usera).

## Czego ten dokument nie zmienia

- Pilot (£200, `w = 0,5`, pasmo 0,15, kill-switch 25%) startuje wyłącznie po P1–P4.
- Kapitał rośnie wyłącznie po bramce B na kanale Kraken.
- Strategia: `EmaCrossover(20, 100)` long-only, F7 10%.

## Sprawdzone na żywym API 2026-11-14 (tryb `validate=true`, żadne zlecenie nie trafiło na giełdę)

- Klucz `tradepulse-bot`: uprawnienia z `GetApiKeyInfo` to `query-funds`,
  `query-open-trades`, `query-closed-trades`, `modify-trades`, `close-trades`.
  `WithdrawMethods` i `DepositMethods` → `EGeneral:Permission denied`. R1 = lista
  uprawnień musi być podzbiorem tych pięciu.
- Saldo: `ZGBP 10.0000`. Opłata z `TradeVolume`: 0,80% (następny próg 0,60% od $2 500).
- `cl_ord_id`: przyjmuje tekst do 18 znaków albo UUID; 24 znaki → `Invalid arguments:cl_ord_id`.
- `validate=true` **nie sprawdza salda** (sprzedaż bez BTC przechodzi) — brak środków
  wyjdzie dopiero na prawdziwym zleceniu; executor sprawdza saldo sam (R11).
- Poniżej `ordermin` → `Invalid arguments:volume minimum not met`; `deadline`
  w przeszłości → `Invalid arguments:deadline`.
- `stop-loss` sprzedaży z `trigger=last` i limit `oflags=post` przyjęte.
- `OpenOrders` i `ClosedOrders` filtrują po `cl_ord_id`.
- £5 po bieżącej cenie = 0,00010065 BTC (minimum 0,00006).
