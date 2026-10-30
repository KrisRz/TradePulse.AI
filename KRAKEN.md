# Kraken — mapa i decyzje

> Jedno miejsce na wszystko, co dotyczy Krakena: konta, pieniądze, klucze, co
> z niego korzysta, co postanowiliśmy. Nowa decyzja albo zmiana stanu = nowy wpis
> w „Decyzje” i poprawka mapy w tym samym commicie.
>
> Stan na **2026-10-30**. Para do Krakena: [`BINANCE.md`](BINANCE.md).

## W skrócie

**Kraken to giełda bota, także na prawdziwe pieniądze.** Kolejność:
1. **Paper na cenach Krakena** (XBT/GBP 1d, £200 wirtualne). Zegar rusza w dniu
   deployu.
2. **Pilot** (£200 prawdziwe), gdy paper spełni P1–P4.
3. **Zwiększanie kapitału** wyłącznie po bramce B.

## Konta

| Konto | Stan | Kto | Pieniądze | Klucze API |
|---|---|---|---|---|
| **Kraken live** (kraken.com) | **otwarte i zweryfikowane 2026-10-30**: paszport, rezydencja podatkowa UK z TIN, oświadczenie „not a US person”, profil FCA „Restricted Investor”, test wiedzy o ryzyku 8/8. Panel pokazuje rynek BTC/GBP. Obowiązuje 24 h „cooling off” przed pierwszym zakupem krypto (wymóg UK). | user | **£0 / 0 BTC** (2026-10-30). Pilot: ~£200 przelewem Faster Payments z banku w UK (darmowy, min. £1) | brak. Pilot: **jeden** klucz, saldo + zlecenia, **bez wypłat**, do SSM (ścieżka do ustalenia) |
| Sandbox spot | **nie istnieje** | — | — | — |

Paper **nie potrzebuje konta**: ceny Krakena są publiczne. Konto i klucz są
potrzebne dopiero do pilota (warunek P4).

## Rynek i koszty (sprawdzone 2026-10-30)

- Para: **XBT/GBP** (API: `XXBTZGBP`, `online`). `ordermin` 0,00006 BTC,
  `costmin` £0,43, krok ceny 0,1.
- Opłaty, najniższy próg: **0,40% maker / 0,80% taker**. Pilot liczy 0,80% (zlecenia
  rynkowe).
- Książka XBT/GBP: spread 0,02–0,96 bps, kupno £100 kosztuje 0,002% ponad cenę
  środkową.
- Regulacje: licencja MiCA (Central Bank of Ireland) i rejestracja FCA (Payward Ltd,
  FRN 928768). Legalny dla rezydenta UK.
- Ceny dzienne: publiczne `OHLC` (`interval=1440`), maksymalnie 720 ostatnich barów.
  Ostatni bar jest otwarty, odrzucamy go.

## Jak bot handluje

- Strategia bez zmian: EMA20/100 long-only, stop F7 10%, decyzja raz dziennie po
  zamknięciu baru UTC.
- **Połowa konta (`w = 0,5`) z pasmem 0,15:** przy wejściu inwestuje 50%. Gdy udział
  BTC wyjdzie poza 35–65%, wraca do 50% (~0,6 razy w roku, koszt ~0,07% rocznie).
- **Kill-switch konta:** equity ≤ 75% szczytu → zamknięcie pozycji, stop, alarm,
  ręczne uzbrojenie.
- ⚠️ **Gotówkowa połowa nie jest nietykalna:** po spadku BTC korekta dokupuje
  z gotówki do 50%. W długim spadku zatrzymuje to dopiero kill-switch konta.

## Co w AWS korzysta z Krakena

| Zasób | Stan |
|---|---|
| Lambda paper Kraken (XBT/GBP 1d) | **do zbudowania** |
| Harmonogram, alarmy, dead-man ping | **do zbudowania** |
| DynamoDB `tradepulse_paper_bot`, nowy pk dla Krakena | **do zbudowania** |
| Executor Krakena (zlecenia, pilot) | **do zbudowania**, dopiero przed pilotem |
| SSM: klucz pilota | **brak**, user zakłada przy pilocie |

## Decyzje

| Data | Decyzja | Dlaczego | Dokument |
|---|---|---|---|
| 2026-09-16 | Kraken oceniony jako zapas: tylko 1d (4h nie przeżywa opłat) | Opłaty 0,40/0,80% | pamięć `kraken-venue-assessment` |
| 2026-10-30 | Pilot na prawdziwych pieniądzach **przed** bramką B, ~£200 | User chce zacząć zarabiać, bez ryzykowania tysięcy na niesprawdzonym | `docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md` |
| 2026-10-30 | Limit spadku 25% liczony na **całym koncie**, `w = 0,5` | Limit dotyczy pieniędzy usera, a gotówka obok bota nie spada | jw. |
| 2026-10-30 | **Kraken = giełda bota** | Pomiar pre-rejestrowany: PASS 4/4 (zysk wobec trzymania BTC przy 0,80%, limit konta, zgodność danych 99,6%, koszt kupna) | `docs/KRAKEN_VENUE_RESULTS_2026-10-30.md` |
| 2026-10-30 | Para **XBT/GBP** | Pieniądze usera są w GBP, bez przewalutowania; strategia w GBP przechodzi 4/4 | jw. |
| 2026-10-30 | Najpierw **paper na Krakenie**; pilot dopiero po: P1 ≥ 28 dni bez błędów, P2 bramka A PASS, P3 saldo paper > startowe, P4 konto + wpłata + klucz | Warunek usera: paper ma pokazać zarobek przed prawdziwymi pieniędzmi | `docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md` |
| 2026-10-30 | Trzymanie połowy konta **z korektą (pasmo 0,15)**, nie tylko przy wejściu | Sama połowa przy wejściu: spadek do −40,7%, limit trzyma w 49% okien 2-letnich; z korektą −26,7% i 78% | `docs/KRAKEN_SIZING_RESULTS_2026-10-30.md` |
| 2026-10-30 | Konto Kraken otwarte i zweryfikowane, **bez wpłaty i bez klucza** do czasu P1–P3 | Pieniądze nie leżą na giełdzie, zanim paper pokaże wynik | ten plik |
| 2026-10-30 | Zlecenia rynkowe (taker 0,80%), post-only (0,40%) później | Backtest i projekt liczą 0,80%; post-only dokłada ryzyko braku wykonania | `docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md` |

## Do zrobienia (po kolei)

- [x] Księga z częściową pozycją i korektą 50/50 (2026-10-30): `PaperPortfolio(exposure, rebalance_band, min_rebalance)`, reguła w `backtesting/sizing.py`. Golden master nietknięty, 16 nowych testów, mutacje 8/8, replay prawdziwej księgi: R2 PASS (93% / 77%).
- [ ] Ceny Krakena w bocie (`feed`) i w bramce A.
- [ ] Lambda paper Kraken + harmonogram + alarmy (Terraform z `-target`). **Start zegara.**
- [x] User: konto Kraken + KYC (2026-10-30). Wpłata i klucz dopiero przed pilotem (P4).
- [ ] Executor Krakena (podpis, nonce, sprawdzenie `cl_ord_id` przed wysłaniem, `validate=true`).
- [ ] Ocena P1–P4 po 28 dniach paper → pilot.
