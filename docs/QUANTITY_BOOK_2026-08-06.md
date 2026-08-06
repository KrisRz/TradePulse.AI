# Księga ilościowa — krok 4 (2026-08-06)

> Domknięcie luki, którą PR #24 nazwał wprost: symulacja liczy pozycje jako
> **ułamek kapitału** i nie zna pojęcia ilości; giełda operuje **wyłącznie na
> ilościach**. Do M6 to nie miało znaczenia, bo nic tu nie rozmawiało z giełdą.
>
> **Okno M5 nietknięte:** złoty wzorzec przechodzi bit-w-bit, bramka A na żywym
> prodzie PASS 6/6, Lambdy M5 bez redeployu.

## 1. Dlaczego nie „przepisaliśmy księgi na ilości"

Naiwny refaktor — `cash` + `qty` zamiast ułamka — jest algebraicznie równoważny,
ale **przestawia kolejność operacji zmiennoprzecinkowych**:

```
ułamkowo:   E * (1 + side*(p/entry - 1))
ilościowo:  cash + qty*p
```

To te same liczby w matematyce, różne w `float`. Złoty wzorzec porównuje przez
`==` (celowo — patrz dyscyplina), więc taki refaktor **wymusiłby jego
przebłogosławienie**, czyli dokładnie tę awarię, przed którą wzorzec chroni.

Zamiast tego: **o ścieżce decyduje fill.**

| Fill | Ścieżka | Arytmetyka |
|---|---|---|
| bez `qty` (`SimulatedExecutor`) | modelowana | **nietknięta, instrukcja po instrukcji** |
| z `qty` (prawdziwe venue) | ilościowa | `cash + qty*price`, prowizja faktyczna |

Reparametryzacja jest ścisła, także dla shortów. Przy wejściu z kapitałem `E`:

```
qty  = side * E / entry_fill
cash = E * (1 - side)          # 0 dla longa, 2E dla shorta
```

skąd `cash + qty*p == E * (1 + side*(p/entry_fill - 1))` — czyli wzór ułamkowy.
Dlatego jedno może zastąpić drugie.

**Spinacz przed rozjazdem:** `test_the_two_paths_agree_when_fed_the_same_trade`
podaje ścieżce ilościowej fill niosący dokładnie to, co wyprodukowałby model, i
sprawdza, że księgi się schodzą. Zmierzony rozjazd: **1,8·10⁻¹²** względnie —
czysta reasocjacja floatów, o 10 rzędów wielkości poniżej centa, który toleruje
bramka A. Ten sam rodzaj strażnika co `slipped_price` vs `costs.py` w PR #24.

## 2. 🔴 Odkrycie: model ułamkowy źle liczy prowizję shorta

Testy równoważności wywaliły się na shortach — i słusznie, bo to **prawdziwa
różnica modelowa, nie zaokrąglenie**.

Przy zamykaniu pozycji model ułamkowy nalicza prowizję od **wynikowego
kapitału** (`apply_fee(entry_equity * (1 + gross))`), a giełda od **notionalu
transakcji**. Dla longa to ta sama liczba — equity wyjściowe *jest* notionalem.
Dla shorta nie:

```
short, E=10k, entry=28 000, exit=27 900:
  equity wyjściowe = 10 025,68        notional transakcji = 9 954,32
  model ułamkowy   = 10 015,652893
  ścieżka ilościowa= 10 015,724250    różnica: +0,071357
```

Czyli **model ułamkowy zaniża koszt shortowania** o ~$0,07 na $10k na trejd.

**Dziś nie boli:** żywa strategia to `allow_short=False`, a spot nie umie
shortować. **Ale `backtesting.engine` ma `allow_short=True` domyślnie**, więc
każdy przyszły research shortów niesie to przybliżenie. Kto będzie walidował
strategię short, musi zdecydować, któremu modelowi ufa — ścieżka ilościowa jest
tą, którą naprawdę zastosuje giełda.

Przybite testem `test_on_a_short_the_two_paths_deliberately_disagree`, żeby to
nigdy nie było niespodzianką.

## 3. Prowizje, których model nie umie wyrazić

Giełda może pobrać prowizję w trzech różnych miejscach i księga rozróżnia je
po `Fill.base_asset` (dodane w tym kroku, ustawiane przez executor):

| Naliczona w | Co robi księga |
|---|---|
| aktywie właśnie kupionym (BTC) | schodzi z **pozycji** (`qty`) |
| walucie kwotowanej (USDT) | schodzi z **gotówki** (`cash`), sumuje w `fees_quote` |
| czymkolwiek innym (**BNB**) | trafia do `fees_external`, **NIE do equity** |

Trzeci przypadek jest świadomy: bez kursu BNB nie da się tego przeliczyć.
Zgadywanie kursu byłoby gorsze niż pokazanie osobno, a ciche pominięcie
zawyżałoby każdy wynik.

### 🔴 Rekomendacja do M6: wyłączyć płacenie prowizji w BNB

Zmierzone na żywym venue (round-trip $20, 2026-08-06):

```json
{ "realized": 9999.9999985,
  "fees_quote": 0.0,
  "fees_external": { "BNB": 2.452e-05 } }
```

Equity wygląda na prawie nietknięte, bo **prawdziwy koszt poszedł w BNB i księga
go nie widzi**. Dopóki tak jest, `backtest = live` nie domyka się po stronie
kosztów.

Dwie drogi:

- **(a) Wyłączyć „pay fees with BNB"** na koncie → prowizja zawsze w base albo
  quote, księgowana ściśle, model się domyka. Kosztuje utratę 25% rabatu.
- (b) Zostawić rabat i przeliczać BNB→USDT w chwili fillu → więcej ruchomych
  części i własny błąd kursu.

**Rekomendacja: (a).** Rabat to ~0,025% na stronę; przy 1,69 round-tripa rocznie
mówimy o groszach rocznie. Wierność modelu kosztów jest warta więcej niż to.

## 4. Dowód, że działa

- **Złoty wzorzec:** przechodzi na `==`, 8 przypadków, ścieżka modelowana
  nietknięta.
- **Bramka A na żywym prodzie:** PASS 6/6, 22 zapisane decyzje odtwarzają się do
  zapisanej księgi (±$0,01).
- **Żywe venue:** shadow-bot prowadzi round-trip przez `PaperPortfolio` z
  prawdziwym executorem — `quantity_backed: true`, `qty_after: 0.0`, prowizja
  BNB poprawnie w `fees_external`.
- **Suite:** 295 zielonych (było 273), z czego 21 nowych na samą księgę
  ilościową.

Od teraz shadow-bot ćwiczy **ścieżkę ilościową codziennie na prawdziwych
fillach**, a nie tylko w testach — czyli tę samą, na której w M6 zawiśnie kasa.

## 5. Zgodność wstecz

Każdy stan zapisany przez Lambdę M5 nie ma pól `qty`/`cash`. `from_dict`
odbudowuje je z `side`/`entry_fill`/`entry_equity`, więc wczytanie starej księgi
nie zostawia pozycji wyglądającej na płaską. Przybite testem
`test_a_book_written_before_these_fields_existed_still_loads`.
