# Binance — mapa i decyzje

> Jedno miejsce na wszystko, co dotyczy Binance: co jest na kontach, co z niego
> korzysta, co postanowiliśmy. Nowa decyzja albo zmiana stanu = nowy wpis w
> „Decyzje” i poprawka mapy w tym samym commicie.
>
> Stan na **2026-10-30**. Para do Binance: [`KRAKEN.md`](KRAKEN.md).

## W skrócie

**Binance odchodzi.** Prawdziwe pieniądze idą na Kraken. Na Binance zostaje tylko
**demo** (fałszywe pieniądze) do czasu, aż paper na Krakenie ruszy. Potem wygaszamy
kanały demo według listy na dole.

## Konta

| Konto | Co to jest | Pieniądze | Klucze API | Stan |
|---|---|---|---|---|
| **Binance live** (binance.com) | Prawdziwe konto usera, kraj zamieszkania **Polska** (reżim UE) | **brak** | **żadnych**, nigdy nie zakładaliśmy | Od 2026-07-01 nowe zlecenia spot zablokowane (MiCA). 2026-10-29 hack, wypłaty wstrzymane. Logowanie działa z telefonu, przez web nie (2026-10-30). |
| **Binance Demo Trading** (demo-api.binance.com) | Osobne środowisko z wirtualnymi pieniędzmi | wirtualne | `/tradepulse/demo/key` + `secret` w SSM (2026-08-06) | Działa, z tego handluje kanał 4h i shadow |

## Co w AWS korzysta z Binance (region eu-west-2)

| Zasób | Co robi | Źródło Binance | Harmonogram (UTC) |
|---|---|---|---|
| Lambda `tradepulse-paper-bot` | Bot 1d (M5), czysta symulacja, $10k wirtualne | **publiczne ceny** `api.binance.com` (BTCUSDT 1d), bez klucza | `cron(10 0 * * ? *)`: 00:10 UTC (01:10 BST) |
| Lambda `tradepulse-venue-4h` | Kanał 4h, prawdziwe zlecenia na demo, księga $200 | demo API + klucze `/tradepulse/demo`, prefiks zleceń `tpv4h-` | co 4 h o :10 |
| Lambda `tradepulse-shadow-bot` | Heartbeat: codzienne mini zlecenie $10 na demo | demo API + klucze `/tradepulse/demo`, prefiks `tpsh-` | 00:25 UTC |
| Lambda `tradepulse-paper-bot-status`, `tradepulse-site-status` | Status dla strony | DynamoDB, nie Binance | na żądanie |
| DynamoDB `tradepulse_paper_bot` | Stan i dziennik decyzji | pk `BTCUSDT_1d`, `BTCUSDT_4h` (+ shadow) | — |
| SSM `/tradepulse/healthcheck/{venue-4h,shadow}` | Dead-man ping (healthchecks.io) | — | — |
| 10 alarmów `tradepulse-*` | Błędy, brak wywołań, DLQ, kill-switch 4h | — | 2026-10-30: wszystkie OK |
| Strona tradepulseai.co.uk | Pokazuje kanały demo Binance | — | do poprawy przy wygaszaniu |

⚠️ **Bot 1d zależy od publicznego API Binance.** Jeśli po hacku Binance wyłączy
publiczne ceny, bot 1d przestanie działać i alarm `no-invocation`/`errors` to pokaże.
2026-10-30 dane przyszły normalnie (ocena bramek z dnia 106).

## Wyniki demo (ocena bramek 2026-10-30, tylko odczyt)

- **Bot 1d:** +1,07% wobec samego trzymania BTC +20,15%, maxDD −9,96%. 0 zamkniętych
  transakcji, LONG od 2026-08-22. Werdykt `INCONCLUSIVE_EXTEND`.
- **Kanał 4h:** $225,48 (+12,74%) wobec samego trzymania BTC +19,78%, 5 zamkniętych
  transakcji, PF 3,04, maxDD −10,10%. Werdykt `FAIL` tylko na `fee_drag`
  (znany, nieinterpretowalny odczyt przez stare prowizje BNB poza equity).

## Decyzje

| Data | Decyzja | Dlaczego | Dokument |
|---|---|---|---|
| 2026-08-06 | Kanał 4h i shadow na Binance Demo | Prawdziwe zlecenia bez prawdziwych pieniędzy | `docs/` M5/E-track |
| 2026-09-16 | Zostajemy na demo, M6 i giełda odłożone | Konto live: brak rynków USDT, banner MiCA | `plan.md` |
| 2026-10-30 | Konto live z krajem Polska **nie nadaje się** do bota | MiCA: konta UE bez nowych zleceń spot od 2026-07-01; Binance bez licencji MiCA i bez zezwolenia FCA | — |
| 2026-10-30 | **Odchodzimy z Binance, prawdziwe pieniądze na Kraken** | Brak dostępu + hack 2026-10-29. Pomiar: Binance tańszy tylko o ~0,05 Sharpe'a | `docs/KRAKEN_VENUE_RESULTS_2026-10-30.md` |
| 2026-10-30 | Demo działa dalej do startu paper Kraken | Nie zostawiamy bota bez działającego kanału | ten plik |

## Wygaszanie (do zrobienia, w tej kolejności, dopiero gdy paper Kraken działa)

- [ ] Wyłączyć harmonogramy `tradepulse-venue-4h-schedule` i `tradepulse-shadow-bot-daily`.
      Kanał 4h najpierw zamknąć do FLAT, żeby demo nie zostało z pozycją.
- [ ] Bot 1d `tradepulse-paper-bot`: zastąpiony przez paper Kraken (nowy zegar).
      Wyłączyć po starcie Krakena.
- [ ] Usunąć zasoby przez Terraform z `-target` (Lambdy, harmonogramy, alarmy, DLQ),
      sprawdzić poza Terraformem (`aws lambda list-functions`, `aws scheduler list-schedules`).
- [ ] Usunąć z SSM `/tradepulse/demo/*` i `/tradepulse/healthcheck/{venue-4h,shadow}`.
      Skasować checki w healthchecks.io (user).
- [ ] Dane w DynamoDB (`BTCUSDT_1d`, `BTCUSDT_4h`) **zostają** jako historia (koszt ~0).
- [ ] Strona: przestać mówić o kanałach Binance.
- [ ] Konto live (user, poza botem): gdy Binance wznowi wypłaty, zostawić puste.
      Kraj zamieszkania na koncie powinien zgadzać się z rzeczywistym (UK). To sprawa
      regulaminu, niezależna od bota.

## Bezpieczeństwo po hacku 2026-10-29

- Nie klikać linków w mailach i SMS-ach „od Binance”. Ostrzeżenia czytać tylko
  w aplikacji.
- Na koncie live nie ma kluczy API. Jeśli kiedyś się pojawią, to nie nasze, usunąć.
