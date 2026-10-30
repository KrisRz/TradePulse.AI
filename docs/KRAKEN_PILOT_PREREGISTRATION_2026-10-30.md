# Pilot na prawdziwych pieniądzach na Krakenie — PRE-REJESTRACJA (2026-10-30)

> Wiążące od commita tego dokumentu. Progi można zaostrzyć przed danymi, **nigdy
> poluzować**. Każda zmiana to nowy dokument, decyzja usera.

## Decyzje usera (2026-10-30)

1. Giełda: **Kraken**, para **XBT/GBP**. Podstawa: `docs/KRAKEN_VENUE_RESULTS_2026-10-30.md`,
   werdykt PASS 4/4. Binance tylko do czasu wygaszenia kanałów demo.
2. Pilot **przed bramką B**, kapitał około **£200**.
3. Limit spadku **25% liczony na całym koncie**. Bot handluje częścią **`w = 0,5`**.
4. **Paper na Krakenie ma pokazać zarobek, zanim wejdą prawdziwe pieniądze.**
   Warunek niżej, potwierdzony przez usera.

## Strategia (bez zmian)

`EmaCrossover(20, 100, allow_short=False)`, stop F7 10%, jedna decyzja na dzień po
zamknięciu baru 1d (UTC).

## Etap 1 — paper na Krakenie (nowy zegar)

- Ceny: publiczne OHLC Krakena **XBT/GBP 1d**.
- Konto wirtualne **£200**. Bot dostaje `w × equity` konta, reszta to gotówka (0%).
- Koszt: **0,80% taker na stronę** plus zmierzony poślizg. Projekt venue liczył
  0,80%, więc pilot handluje zleceniami rynkowymi (taker). Post-only (0,40%) to
  osobne usprawnienie po pilocie, z własnym dowodem, bo dokłada ryzyko braku
  wykonania.
- Start z bieżącym stanem sygnału. 2026-10-30 sygnał to LONG (od 2026-08-22),
  więc paper wchodzi w pozycję na pierwszym barze po starcie. Tak samo wszedłby
  pilot.
- Zegar startuje od pierwszej decyzji zapisanej w DynamoDB.

## WARUNEK STARTU PILOTA (wiążący, potwierdzony przez usera 2026-10-30)

Pilot startuje w pierwszym dniu oceny, w którym spełnione są **jednocześnie**:

- **P1:** paper Kraken działa **≥ 28 dni** i ma **0 błędów funkcji**, sprawdzone
  w metrykach;
- **P2:** bramka A (zgodność wykonania) liczona na kanale Kraken paper = **PASS**;
- **P3:** **equity paper po opłatach > equity startowe**, z otwartą pozycją
  wycenioną po bieżącej cenie;
- **P4:** user ma zweryfikowane konto Kraken z wpłaconym kapitałem i kluczem API
  bez prawa do wypłat.

Jeśli P3 nie jest spełnione, ocena wraca co 28 dni. ⚠️ Zapisane przed danymi:
28 dni nie dowodzi zyskowności (bot wygrywa 36% transakcji, zamyka ~1,7 transakcji
rocznie). P3 to warunek komfortu i ochrona przed startem w złym momencie, nie
dowód przewagi. Dowodem przewagi pozostaje bramka B.

## Etap 2 — pilot (prawdziwe pieniądze)

- Kapitał: wpłata usera, około £200. Bot dostaje `w = 0,5` equity konta w chwili
  wejścia, nigdy więcej (twardy budżet w executorze).
- **Kill-switch konta:** equity konta ≤ 75% swojego szczytu → zamknięcie pozycji,
  stop bota, alarm. Ponowne uzbrojenie wyłącznie świadome, zgodnie z
  `docs/RUNBOOK.md`.
  - Pomiar M2: najgorszy historyczny spadek konta przy `w = 0,5` to −26,7%, więc
    kill-switch **może zadziałać przy normalnym spadku**. To jego zadanie.
  - Budżet straty pilota: ~£50.
- Klucz API: zapytania o saldo i zlecenia, **bez wypłat**.
- Idempotencja po naszej stronie: przed każdym zleceniem sprawdzenie, czy zlecenie
  z tym samym id klienta już istnieje (ta sama pułapka co na Binance).
- Podatki: każdy fill trafia do eksportu HMRC (`scripts/hmrc_export.py`), kwoty
  w GBP.

## Ocena i zwiększanie kapitału

- Bramki A, B i C liczone co 28 dni na kanałach Kraken (paper i pilot).
- **Kapitał rośnie wyłącznie po bramce B PASS** (z B5, B6, B7) na kanale Kraken.
  Do tego czasu kapitał pilota się nie zmienia.
- B7 wymaga 365 dni, więc najwcześniejsze zwiększenie kapitału to rok od startu
  zegara paper Kraken.
