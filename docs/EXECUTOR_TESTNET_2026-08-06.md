# Warstwa wykonawcza na żywym venue — `BinanceDemoExecutor` (2026-08-06)

> Zamknięcie **niewiadomej B** z planu rozwoju: *czy bot umie poprawnie WYKONAĆ
> trejd?* Niewiadoma A (czy strategia zarabia) dalej biegnie i potrzebuje
> 12–18 miesięcy. B była nietknięta do PR #24 i blokowała M6 tak samo mocno —
> od dziś jest przejechana od końca do końca na prawdziwym silniku dopasowań.
>
> **Nie dotyka okna M5:** żadnej zmiany w Lambdzie, w księdze na DynamoDB ani w
> parametrach strategii. Skrypt buduje portfel w pamięci i handluje kontem demo.

## 1. Korekta planu: to nie jest ten testnet, co myśleliśmy

Plan zakładał `testnet.binance.vision` (klasyczny Spot Testnet, rejestracja
przez GitHuba). Klucze, które mamy, pochodzą z **Binance Demo Trading**
(`demo.binance.com`) — to **osobne środowisko z osobnymi kluczami**.

| Host | Odpowiedź na nasz podpisany `GET /api/v3/account` |
|---|---|
| `testnet.binance.vision` | `-2015 Invalid API-key, IP, or permissions for action` |
| `api.demo.binance.com` | rezolwuje się w DNS, ale nie odpowiada |
| `api-demo.binance.com` | rezolwuje się, zwraca `404` |
| **`demo-api.binance.com`** | **`200 OK`** ← to jest ten |

`demo.binance.com/api/...` przekierowuje 301 na **produkcyjne** `api.binance.com`
— czyli naiwne sklejenie base URL z domeny UI wysłałoby zlecenia na prawdziwą
giełdę. To jest dokładnie ten rodzaj pomyłki, przed którym ma chronić osobny tor.

Stała `DEMO_BASE_URL` jest przypięta testem, żeby nikt jej po cichu nie podmienił.

## 2. Co zmierzyliśmy (a nie założyliśmy)

Konto demo: `canTrade=True`, SPOT, 5000 USDT / 0.05 BTC / 1 ETH / 2 BNB.
Filtry BTCUSDT: `stepSize` 0.00001 BTC, `tickSize` 0.01 USDT, `minNotional` 5 USDT.

### 2.1 Prowizja — zgadza się z modelem
Venue nalicza **0.1% maker/taker**. Bot zakłada `fee_rate = 0.001`
(`paper_trading/bot.py:28`). Trafione co do cyfry — założenie prowizji przestaje
być zgadywanką.

### 2.2 Poślizg — model jest KONSERWATYWNY
Pierwszy realny pomiar liczby, którą bot zakładał od pierwszego dnia:

| Noga | Referencja | Założone | Faktyczne | Poślizg fakt. | Poślizg zał. |
|---|---|---|---|---|---|
| BUY | 64 431.72 | 64 444.61 | 64 431.72 | 0.0000% | 0.0200% |
| SELL | 64 433.92 | 64 421.03 | 64 431.99 | 0.0030% | 0.0200% |

Zakładane 0.02% jest **6–∞× ostrożniejsze** niż zmierzone. Backtest zaniża wynik,
nie zawyża — czyli błąd jest w bezpieczną stronę.

⚠️ **Zastrzeżenie — sprecyzowane po weryfikacji (2026-08-06, korekta):**
pierwotnie zapisaliśmy, że „demo ma własny feed". **To było błędne.** Sprawdzone
porównaniem demo ↔ produkcja:

| Co | Demo vs live |
|---|---|
| Ticker BTCUSDT | **identyczny** co do grosza |
| Świece 1d (open) | **identyczne** |
| Świece 1d (close) | różnica ≤ 0.01 USDT (~0.00002%) |
| Świece 1d (high/low) | różnice do ~13 USDT |
| Księga zleceń — poziomy cen | **te same** |
| Księga zleceń — wolumeny | różne (8.2918 vs 8.2464 BTC na topie) |

Czyli demo to **żywe ceny + osobny silnik dopasowań** z płynnością uczestników
demo. Wniosek: poślizg stamtąd jest **znacznie lepszą poszlaką**, niż sądziliśmy
— odnosi się do prawdziwych poziomów cenowych — ale **nadal nie jest pomiarem
live**, bo nasze zlecenie nie zjada prawdziwej księgi. Prawdziwy poślizg
zmierzymy za realne pieniądze w M6; `Reconciliation` już na to czeka.

Konsekwencja projektowa: shadow-bot może karmić strategię **produkcyjnym** feedem
i wykonywać na demo — sygnał będzie z definicji ten sam co na prodzie, a fill
prawdziwy. Gdyby feedy się rozjeżdżały, taka konstrukcja nie miałaby sensu.

### 2.3 Odkrycie: prowizja poszła w BNB, nie w USDT
Konto trzyma 2 BNB, więc Binance pobrał prowizję **stamtąd** (0.00005075 BNB na
round-trip), a nie z waluty kwotowanej. Księga modeluje prowizję jako ułamek
kapitału w USDT. **To są dwie różne waluty** i nikt tego wcześniej nie zauważył,
bo nie było kodu, który by w ogóle składał zlecenie.

Dziś to nieszkodliwe (księga zostaje ułamkowa, wariant (a)), ale **krok 4 —
księga ilościowa — musi to rozstrzygnąć**: albo wyłączamy płacenie prowizji w
BNB, albo księgujemy ją po kursie BNB. Pole `fee_asset` jest w `Fill` i w
`Reconciliation` po to, żeby to było widoczne, a nie zgubione.

## 3. Dowód, że ścieżka działa

Round-trip `--force-signal` na żywym venue (`orderId` 54495523957 / 54495523967):

```
→ ENTRY  planned 0.00031 BTC (~19.97 USDT)   book entry_fill 64,431.72
→ EXIT                                        net return -0.1995%
   executor holds 0 BTC (expect 0)
```

Zwrot **−0.1995%** to praktycznie sama prowizja round-tripu (0.1% × 2 = 0.2%) —
czyli księga i venue policzyły to samo.

**Stan konta po teście — najmocniejszy dowód:**
```
przed:  2.00000000 BNB | 0.05000000 BTC | 5000.00000000 USDT
po:     1.99994925 BNB | 0.05000000 BTC | 5000.00008370 USDT
```
BTC wróciło **co do ostatniej cyfry** do 0.05 — executor sprzedał dokładnie to,
co kupił, i **nie tknął pre-fundowanych coinów konta**. Zero dustu.

## 4. Co ten kod obsługuje (i dlaczego to nie jest paranoja)

| Rzecz | Dlaczego | Gdzie przypięte |
|---|---|---|
| Podpis HMAC-SHA256 | Podpis musi pokrywać **te bajty**, które lecą na wire | `test_signature_covers_the_exact_query_that_is_sent` |
| Clock skew `-1021` | Laptop dryfuje, kontener się usypia; wygląda jak błąd kluczy | resync **raz**, potem retry |
| `LOT_SIZE` w `Decimal` | `0.1+0.2` nie jest poprawną ilością BTC → `-1013` | `test_flooring_is_exact_where_binary_floats_are_not` |
| Zaokrąglanie **w dół** | W górę potrafi przekroczyć saldo, które finansuje zlecenie | `test_quantity_is_floored_to_the_lot_step` |
| `MIN_NOTIONAL` | Odmowa **lokalnie** — venue i tak odrzuci, a zżera limit zapytań | zweryfikowane na żywo (3 USDT < 5) |
| Częściowe fille | Zlecenie MARKET chodzi po księdze; cena = VWAP | `test_market_order_walking_the_book_averages_by_quantity` |
| Prowizja w base asset | Kupujesz 0.05 BTC, płacisz 0.1% w BTC → masz 0.04995 | `test_commission_in_the_base_asset_reduces_what_we_can_sell` |
| Notacja naukowa | `Decimal` renderuje `5E-5`; venue to odrzuca | `test_quantity_is_sent_without_scientific_notation` |
| Rate limit 429 / ban 418 | 429 → `Retry-After`; 418 = już ban, **nie ponawiać** | osobne testy |
| Błędy biznesowe | `-2010` nie naprawi się od ponowienia → od razu w górę | `test_business_errors_are_raised_immediately` |

**55 testów, zero sieci** — CI jest deterministyczny, a suite nie wymaga kluczy.

## 5. Czego to świadomie NIE rozwiązuje

`PaperPortfolio` liczy pozycje jako **ułamek kapitału** i nie zna ilości; giełda
zna wyłącznie ilości. Wariant (a) tłumaczy jedno na drugie **na granicy**: BUY
wydaje ustaloną część salda kwotowanego, SELL zwraca dokładnie to, co kupiły
nasze własne zlecenia (stąd `position_qty` — dlatego pre-fundowane 0.05 BTC jest
bezpieczne).

Konsekwencja jest uczciwa: **księga zostaje ułamkowa, venue ilościowe, a ta klasa
tłumaczy między nimi.** Zrobienie księgi ilościowej to krok 4 i to jest to, czego
naprawdę potrzebuje M6 — razem z rozstrzygnięciem sprawy prowizji w BNB (§2.3).

## 6. Higiena kluczy

- Klucze **tylko** przez `BINANCE_DEMO_KEY` / `BINANCE_DEMO_SECRET`
  (`BinanceDemoExecutor.from_env`). W repo ląduje wyłącznie `.env.example`.
- W CI stoi gitleaks; klucz raz zacommitowany to klucz do rotacji.
- ⚠️ Klucz **live** (`binance.com`, tylko `Enable Reading`) był w tej sesji
  odsłonięty w zrzucie ekranu → **do skasowania/rotacji**. Do tego toru nie jest
  potrzebny i nigdzie w kodzie nie występuje.

## 7. Jak to uruchomić

```bash
export BINANCE_DEMO_KEY=... BINANCE_DEMO_SECRET=...

python scripts/demo_roundtrip.py --check                    # łączność, filtry, salda
python scripts/demo_roundtrip.py --dry-run --notional 20    # sizing, nic nie wysyła
python scripts/demo_roundtrip.py --force-signal --notional 20 --hold 5
python scripts/demo_roundtrip.py --force-signal --json      # rekoncyliacja jako JSON
```

`--force-signal` istnieje, bo strategia robi **1.69 round-tripa na rok** —
czekanie na prawdziwy cross EMA oznaczałoby miesiące niepewności, czy kod
podpisujący w ogóle działa. Tu cała ścieżka przechodzi w minutę.
