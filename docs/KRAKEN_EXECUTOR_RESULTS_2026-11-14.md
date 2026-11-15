# Executor Krakena — wynik testu T0–T8 (2026-11-14)

> Zasady: `docs/KRAKEN_EXECUTOR_PREREGISTRATION_2026-11-14.md`. Test na prawdziwym
> koncie Kraken (XBT/GBP), wpłata £10. Zlecenia uruchamiał user komendami
> `scripts/kraken_executor_test.py … --confirm`; odczyty i weryfikacja niezależnie
> przez API. Księga testu: DynamoDB `tradepulse_paper_bot`, pk `XBTGBP_exectest`.

## Werdykt: **PASS 9/9**, strata testu £0,1591 (budżet £3)

| # | Co | Wynik | Dowód |
|---|---|---|---|
| T0 | Bez pieniędzy | **PASS** 11/11, 20:32 UTC | 5 uprawnień, wypłaty i wpłaty `Permission denied`, kupno / sprzedaż / stop w `validate`, zły sekret bez ponowień, zły nonce po 3 próbach |
| T1 | Kupno market | **PASS** | `OXTEEF-HNV7F-HGUHVS`: 0,00012512 BTC, koszt £6,20252, opłata £0,04962 (0,80%); £10 − saldo = £6,2521 |
| T2 | Stop awaryjny | **PASS** | `OAP6ZJ-O4UT7-JTGA2J`: cała ilość, trigger £39 658,0 = 0,80 × wejście |
| T3 | Idempotencja | **PASS** | dwa przebiegi tego samego baru → jedno kupno na giełdzie |
| T4 | Przerwany przebieg | **PASS, na prawdziwej awarii** | pierwszy przebieg stanął po kupnie (błąd niżej); drugi znalazł zlecenie po id klienta, zaksięgował raz, postawił stop |
| T5 | Korekta | **PASS** | stop anulowany (0 wykonania) → 1,4 s → sprzedaż `OOHTT6-KMK5G-GEVDC4` 0,00006 BTC → nowy stop `OUXYGT-DGLEP-AFAKZJ` na 0,00006512, ten sam trigger |
| T7 | Wyjście | **PASS** | `OIWZLI-E3DQQ-YV23NT` 0,00006512 BTC; 0 BTC, 0 otwartych zleceń |
| T6 | Stop, który zadziałał | **PASS** | kupno `OMVUED-JP2CN-5O5J5V` 0,0000645 BTC; stop `OXK75R-P6GRM-CYH6UX` trigger £49 469,8 wykonany 20:51 UTC po £49 466,2 (poślizg 0,007%); `sync` zaksięgował fill z giełdy, księga 0, wejście zablokowane |
| T8 | Eksport HMRC | **PASS** | 5 filli, 3 zbycia, wpływy £9,32, koszt £9,48, strata £0,16; kwoty w GBP |

## Uzgodnienie końcowe (API Krakena vs DynamoDB)

- Kraken: 8 zleceń, 5 wykonanych, 3 stopy anulowane bez wykonania, 0 otwartych.
- Opłaty: Kraken £0,15036 = DynamoDB £0,15036; te same 5 id zleceń po obu stronach.
- Kupna £9,40249, sprzedaże £9,39374, wynik −£0,15911; £10 + wynik = £9,84089,
  saldo `ZGBP 9.8409`, `XXBT 0`.
- Opłata / obrót = 0,79995%. **Strata to w 94,5% opłaty** (£0,150 z £0,159); reszta
  £0,009 to stop z T6 ustawiony celowo 0,3% pod ceną. Poślizg zleceń market na tej
  wielkości jest niemierzalny.

## Błędy znalezione i naprawione w trakcie

1. **Zlecenie niewidoczne tuż po wysłaniu.** `QueryOrders` odpowiedział „unknown” na
   txid zwrócony chwilę wcześniej przez `AddOrder`; executor zatrzymał się z kupionym
   BTC, pustą księgą i bez stopu. Poprawka: czekanie na widoczność, a po wyczerpaniu
   prób `OrderOutcomeUnknown` (następny przebieg kończy sprawę po id klienta). Dwa
   testy regresji; w rundzie T6 kupno przeszło w jednym przebiegu.
2. Pusta pozycja zapisywała się jako `0E-8` — teraz `0`.
3. Eksport HMRC dla pary w GBP ostrzegał „NOT sterling” — poprawione.

## Czego test nie pokrył

- Korekta przez **dokupienie** (T5 był sprzedażą; przy £10 dokupienie łamałoby R7).
  Ścieżka kodu jest ta sama co wejście + stop, pokryta testami na giełdzie w pamięci.
- Częściowe wykonanie zlecenia market (nie wystąpiło).
- `SystemStatus` inny niż `online` i niedostępność API (tylko w testach jednostkowych).
- Publiczna połowa klucza API pojawiła się w sesji (odpowiedź `GetApiKeyInfo`);
  decyzja usera: klucz zostaje. Sekret nie był nigdzie wyświetlony.

## Co dalej

Pozycja 6 planu (review Codexa + PR, gdy user poprosi), potem 7 (post-only) i 8 (#12).
Księga testu zostaje zablokowana po stop-oucie; do pilota powstaje osobny pk.

## Po review kodu (2026-11-15)

Review przed PR-em znalazło 6 błędów w ścieżkach, których test T0–T8 nie dotknął.
Wszystkie odtworzone, naprawione, każdy z testem, który pada na kodzie sprzed poprawki.

| # | Błąd | Poprawka |
|---|---|---|
| 1 | Korekta mogła sprzedać więcej, niż należy do bota, jeśli konto trzyma BTC spoza strategii; R13 odzywało się dopiero po transakcji | wielkość sprzedaży sprawdzana z księgą **przed** anulowaniem stopa i wysłaniem zlecenia (także post-only) |
| 2 | Gdy zapis rekordu transakcji się nie udał po zapisie stanu, rekord znikał z eksportu HMRC na stałe | rekord czeka w zapisanym stanie (`outbox`), w tym samym zapisie co `booked`; następne uruchomienie go dostarcza. Zapis w DynamoDB jest idempotentny po `order_id` |
| 3 | Stop wykonany częściowo i wciąż otwarty był księgowany od razu, a reszta ginęła | `sync` czeka na stan końcowy stopa i nie zmienia stanu wcześniej |
| 4 | Odrzucona korekta albo wyjście (minimum pary, limit ekspozycji, odmowa giełdy) zostawiały pozycję bez stopa | po każdej jednoznacznej odmowie stop wraca |
| 5 | Stop przyjęty przez giełdę tuż przed śmiercią procesu był brany za obce zlecenie | `sync` odnajduje go po identyfikatorze klienta; jeśli zdążył się wykonać, księguje |
| 6 | Wyjście post-only wykonane przed kolejnym uruchomieniem wyglądało jak brak monet (R11) | `sync` uwzględnia to, co oczekujące zlecenie już sprzedało albo kupiło |

Żaden z nich nie wystąpił na prawdziwych zleceniach (rekordy i saldo uzgodnione
co do pensa). Testy executora: 42 → 50. Kod po poprawkach wczytał stan z DynamoDB
i odczytał konto (`status`, tylko odczyt): 0 otwartych zleceń, `outbox` pusty.
Poprawek nie sprawdzałem nowymi prawdziwymi zleceniami.
