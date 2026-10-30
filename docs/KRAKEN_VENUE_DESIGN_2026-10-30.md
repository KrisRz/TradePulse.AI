# Kraken jako giełda bota — PROJEKT POMIARU PRE-REJESTROWANY (2026-10-30)

> Pisany **przed** pomiarem. Reguła decyzyjna niżej jest wiążąca i nie będzie
> renegocjowana. Żadna liczba ze strategii na danych w GBP ani z Krakena nie była
> liczona przed spisaniem tego dokumentu.

## Po co

Decyzje usera z 2026-10-30:
- pilot na prawdziwych pieniądzach przed bramką B, około £200;
- limit spadku 25% liczony na **całym koncie**, bot handluje częścią `w = 0,5`;
- przejście z Binance na Kraken, ale **dopiero po teście**, bo może Binance jest
  lepszy.

Ten pomiar odpowiada na jedno pytanie: **czy bot 1d ma sens na Krakenie, w funtach,
przy jego opłatach**. Strategia się nie zmienia: `EmaCrossover(20, 100, allow_short=False)`,
stop F7 10%, zero nowych parametrów.

## Co wiemy przed pomiarem (fakty, nie liczby strategii)

- **Binance — dostęp:** konto usera ma kraj zamieszkania Polska, czyli reżim UE.
  Binance nie ma licencji MiCA i od 2026-07-01 blokuje kontom z UE nowe zlecenia
  spot (banner w UI, 2026-09-16). User mieszka w UK, a Binance nie ma zezwolenia FCA.
  2026-10-29 Binance zhakowano (~$6,3 mld), wpłaty i wypłaty wstrzymane.
  Na koncie usera nie ma pieniędzy.
- **Binance — koszty:** 0,10% taker. To jego jedyna przewaga i ten pomiar ją
  wycenia (siatka opłat niżej).
- **Kraken:** licencja MiCA (CBI) i rejestracja FCA (Payward Ltd, FRN 928768).
  Pary XBT/GBP, XBT/USD, XBT/USDC, XBT/EUR są `online` (API `AssetPairs`,
  2026-10-30). XBT/GBP: `ordermin` 0,00006 BTC, `costmin` £0,43. Opłaty na
  najniższym progu: 0,40% maker / 0,80% taker (cennik sprawdzony 2026-09-16).
  Nie ma darmowego sandboxa spot.

## Pomiary

**M1 — strategia na cenie w GBP, długa historia.**
- Dane: `BTCUSDT_1d.csv` (`< 2026-07-16`) podzielone przez kurs GBP/USD z FRED
  `DEXUSUK`. Brakujące dni (weekendy, święta USA) wypełniam ostatnim kursem
  (forward-fill). Zakładam USDT ≈ USD.
- Rzetelność tej syntetycznej ceny sprawdza M3.
- Jedna ciągła symulacja na każdy układ okien `calibration_audit.LAYOUTS`
  (730/180, 500/125, 1000/250, 365/90), bez sklejania foldów.
- Opłaty na stronę: **0,10%** (Binance), **0,40%** (Kraken, maker post-only),
  **0,80%** (Kraken, taker). Slippage 2 bps.
- Odniesienie: B&H BTC w GBP, ta sama opłata.
- Dla porównania to samo w USD.

**M2 — limit spadku na koncie przy `w = 0,5`.**
- Dzienna stopa konta = `0,5 × strategia + 0,5 × gotówka`.
- Gotówka **0%**. Zarobku na gotówce nie zakładam, dopóki nie zobaczę go na koncie.
- Opłata 0,80% (najgorszy przypadek), cena w GBP, od 2018.
- Okna kroczące 365 i 730 dni co 7 dni. Liczę odsetek okien z DD ≤ 25%, medianę
  DD i DD z całej próby.

**M3 — zgodność danych (Kraken vs proxy).**
- Ostatnie 720 dni (więcej API OHLC Krakena nie daje).
- Porównuję Kraken XBT/GBP 1d z syntetyczną BTCUSDT/`DEXUSUK` i Kraken XBT/USD 1d
  z Binance BTCUSDT 1d z `data-api.binance.vision`.
- Miary: korelacja dziennych zwrotów, mediana |różnicy zamknięcia| w bps,
  **zgodność sygnału EMA20/100** (odsetek dni z tym samym stanem long/flat).

**M4 — koszt wejścia na żywo.**
- Książka zleceń XBT/GBP z API `Depth` Krakena, 5 odczytów co minutę.
- Miary: spread w bps oraz poślizg zlecenia rynkowego kupna za £100 i za £1 000
  względem ceny środkowej.

## REGUŁA DECYZYJNA (wiążąca)

Kraken zostaje **giełdą pilota**, jeśli spełnione są wszystkie cztery warunki:

- **R1:** przy 0,80% Sharpe strategii w GBP ≥ Sharpe B&H w GBP w **≥ 3 z 4**
  układów.
- **R2:** przy `w = 0,5`, 0,80% i gotówce 0% DD konta ≤ 25% w **≥ 75%** okien
  730-dniowych **i** w ≥ 90% okien 365-dniowych.
- **R3:** zgodność sygnału EMA20/100 ≥ 95% dni, w obu parach z M3. To dowód, że
  backtest na danych z Binance (lub proxy) opisuje to, co bot zobaczy na Krakenie.
- **R4:** mediana (połowa spreadu + poślizg za £100) ≤ 0,10%.

Gdy coś nie przejdzie:
- **R1 albo R2 nie przechodzi** → bot w tej formie nie ma giełdy. Zostajemy na
  paperze, pilota nie ma. Kandydat #12 musiałby to zmienić.
- **R3 nie przechodzi** → przed pilotem nowy backtest wyłącznie na danych Krakena
  (pobranie paczki OHLCVT).
- **R4 nie przechodzi** → zlecenia post-only (maker) obowiązkowe, a model kosztów
  rośnie o zmierzony poślizg.

**Binance jest „lepszy” tylko wtedy, gdy da się na nim handlować.** Dziś warunek
dostępu nie jest spełniony (konto UE, MiCA, hack). M1 pokaże, ile kosztuje
rezygnacja z jego opłaty 0,10%. Ta liczba nie zmienia decyzji, dopóki dostęp
jest zamknięty.

## Czego ten pomiar nie rozstrzyga

- **Kiedy pilot startuje.** User 2026-10-30: paper ma pokazać zarobek, zanim
  wejdą prawdziwe pieniądze. Warunek wejścia pilota pre-rejestruję osobno,
  w dokumencie pilota, przed startem bota paper na danych Krakena.
- **Executor Krakena** (osobny etap, po decyzji).
