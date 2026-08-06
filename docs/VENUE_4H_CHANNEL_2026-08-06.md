# Kanał BTC 4h na żywym venue — pre-rejestracja i projekt (2026-08-06)

> Księga papierowa, ale **fille pochodzą z prawdziwego silnika dopasowań**.
> Ta sama zwalidowana strategia (EMA20/100 long-only), co na 1d — inny interwał
> i inne źródło fillu.
>
> ⚠️ Ten dokument powstał **PRZED uruchomieniem okna**. Progi poniżej są
> pre-rejestrowane. Edytowanie ich po zobaczeniu wyników jest tą samą awarią,
> przed którą chroni pre-rejestracja w `scenario_lab.py`.

## 1. Uczciwe uzasadnienie (po sprostowaniu)

Pierwotnie kanał 4h uzasadnialiśmy tym, że da **7,2× szybszy dowód**. **To było
błędne** i zostało obalone symulacją (20 000 historii, prawdziwy Sharpe 1,0):

| okno | SE(1d) | SE(4h) | stosunek |
|---|---|---|---|
| 1,8 mies. | 2,610 | 2,551 | **1,02×** |
| 12 mies. | 0,999 | 1,002 | 1,00× |
| 8 lat | 0,354 | 0,353 | 1,01× |

Precyzja **zannualizowanego** Sharpe'a zależy od czasu kalendarzowego, nie od
gęstości próbkowania: `SE = √P · √(1/(P·T)) = √(1/T)`. Częstotliwość skraca się
w ułamku. Gdyby było inaczej, stosunek rósłby do √6 = 2,45×.

**Czego więc ten kanał NIE robi:** nie skraca drogi do werdyktu o rentowności.
Bramka B dla 4h ma ten sam horyzont co dla 1d.

**Co robi, a czego 1d nie potrafi z zasady:** produkuje **~12 prawdziwych
round-tripów rocznie zamiast 1,69**. Poślizg, fee drag, częściowe fille,
zaokrąglenia do `LOT_SIZE` i zachowanie księgi na prawdziwym fillu zbiegają się
z **liczbą trejdów**, nie z czasem — i to są dokładnie wielkości, na których
zawiśnie M6. Shadow-bot dowodzi, że ścieżka *działa*; ten kanał mierzy, **ile
kosztuje**, gdy prowadzi ją strategia, a nie heartbeat.

## 2. Pre-rejestrowane progi (spisane przed startem)

### Bramka A — wierność wykonania
Bez zmian: te same 6 kryteriów co dla 1d (kompletność logu, parytet sygnału,
parytet ceny, brak lookahead, parytet księgowy, infrastruktura).

### Bramka B — rentowność
**Te same progi i ten sam horyzont co 1d.** Żadnego przyspieszenia — patrz §1.
Nie wolno tego kanału traktować jako szybszej drogi do M6.

### 🆕 Bramka C — wierność kosztowa *(specyficzna dla tego kanału)*
To jest to, po co kanał istnieje. Rozstrzygalna po **≥20 prawdziwych fillach**
(przy ~12 round-tripach/rok ≈ 10 miesięcy):

⚠️ **Doprecyzowane po pierwszych dwóch fillach (2026-08-06, przed startem
harmonogramu).** Pierwotny zapis mierzył „poślizg" jako `fill / cena_referencyjna`.
To **zlepek dwóch różnych kosztów** i próg 0,02% dla niego nie ma sensu:

| | referencja | fill | „poślizg" |
|---|---|---|---|
| zlecenie `54508851440` | 64 446,00 | 64 458,18 | 0,0189% |
| zlecenie `54510109086` | 64 446,00 | 64 474,17 | **0,0437%** |

Ta sama referencja, dwa razy inny wynik — bo referencją jest **zamknięcie bara**,
a zlecenie leci kilkanaście minut później. Rozkład jest teraz mierzony osobno
(`Reconciliation.drift` i `.execution_slippage`, mark price pobierana tuż przed
wysłaniem):

```
dryf        = mark_przy_zleceniu / zamknięcie_bara − 1    ← ruch rynku, NIE modelowany
egzekucja   = fill / mark_przy_zleceniu − 1               ← TO modeluje `slippage`
```

| Kryterium | Próg |
|---|---|
| C1. Mediana **poślizgu egzekucji** | ≤ 0,02% (założenie modelu) |
| C2. p90 **poślizgu egzekucji** | ≤ 0,05% |
| C3. Zlecenia odrzucone przez venue | ≤ 2% wszystkich prób |
| C4. Fille częściowe pozostawiające niedomkniętą pozycję | 0 |
| C5. Rozjazd księga↔venue na ilości | 0 przypadków > 1 `stepSize` |
| **C6. Mediana dryfu decyzja→zlecenie** | **raportowana, BEZ progu** |

C6 nie ma progu celowo: dryf zależy od opóźnienia harmonogramu, nie od jakości
egzekucji, a **backtest go w ogóle nie modeluje** (zakłada fill po cenie bara).
Jeśli okaże się systematycznie niekorzystny, to osobne odkrycie o wierności
backtestu i osobna decyzja — być może skrócenie opóźnienia z 10 minut.

**Skutek FAIL na C1/C2:** model kosztów zaniża rzeczywistość → backtest zbyt
optymistyczny → progi bramki B trzeba przeliczyć przy wyższej prowizji **przed**
dopuszczeniem realnych pieniędzy.

## 3. Projekt

```
co 4h (cron 10 0,4,8,12,16,20 UTC)
  feed → EMA20/100 → sygnał
     ↓ (tylko przy zmianie pozycji)
  PaperPortfolio  ←── BinanceDemoExecutor
     ↓                    ↓
  księga ilościowa    PRAWDZIWE zlecenie MARKET
  (pk BTCUSDT_4h)     na demo-api.binance.com
```

Kapitał księgi = pułap zlecenia = **200 USDT**. Trzymane równo celowo: księga
liczy pozycje jako ułamek kapitału, więc „pełna pozycja" musi odwzorować się na
zlecenie mniej więcej tej wielkości. Rozjechanie ich sprawiłoby, że księga
raportowałaby strategię siedzącą w 99% w gotówce. 200 USDT odpowiada temu, co M6
naprawdę planuje ($50–100), zostawia miejsce shadow-botowi i trzyma każde
zlecenie daleko od progu `MIN_NOTIONAL` = 5 USDT.

## 4. 🔴 Pułapka, dla której powstał osobny handler

`BinanceDemoExecutor` śledzi pozycję **w pamięci**. Lambda żyje sekundy, a ten
bot może trzymać longa tygodniami. Odtworzony bot próbowałby sprzedać pozycję,
o której nie wie, że ma — `nothing to sell` — i **prawdziwe coiny zostałyby na
giełdzie bez kodu zdolnego je zamknąć**. Co gorsza, wyszłoby to dopiero przy
pierwszym wyjściu, potencjalnie miesiące później.

Lekarstwem jest księga ilościowa z kroku 4: `PaperPortfolio.qty` jest
persystowane, więc `attach_venue()` odtwarza pozycję executora **z księgi**, a nie
z salda konta — saldo nie odróżnia naszej pozycji od 0,05 BTC, którymi konto było
zasilone.

Zweryfikowane lokalnie: stan zapisany z `qty: 0.0031` → świeży proces →
`executor trzyma: 0.0031`, drugie uruchomienie na tym samym barze nie kupiło
ponownie.

Handler raportuje przy każdym przebiegu `book_qty` obok `venue_free_base`. Nie
muszą być równe (konto ma pre-fundowane coiny), ale muszą poruszać się razem.
Jedyny niemożliwy stan — księga trzyma więcej, niż konto w ogóle ma — jest
zgłaszany głośno, bo wtedy noga wyjścia nie mogłaby się wypełnić.

## 5. Izolacja od M5

Osobna Lambda, rola, harmonogram, DLQ i alarmy. Osobny zip (dzielenie
`var.lambda_zip_path` przedeployowałoby bota M5 w środku okna). Dzieli tylko
tabelę DynamoDB — pod kluczem `BTCUSDT_4h`, więc mierzona księga 1d jest
nietykalna — oraz temat SNS.

Koszt: **$0** (Lambda 6×/dzień i alarmy mieszczą się w darmowych progach).
