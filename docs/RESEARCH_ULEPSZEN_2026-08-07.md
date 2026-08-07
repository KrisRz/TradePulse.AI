# Research ulepszeń — 2026-08-07 (web, oficjalne docs, GitHub)

> Pytanie: co jeszcze można zrobić, żeby bot podejmował lepsze decyzje?
> Trzy równoległe kwerendy badawcze (meta-labeling, reżimy/sizing, dane/cechy),
> wyniki zsyntetyzowane wg SIŁY DOWODÓW. Wszystko poniżej podlega dyscyplinie
> projektu: **nic nie dotyka żywej strategii w oknie M5**, a każdy kandydat
> wchodzi wyłącznie przez purged walk-forward i tylko jeśli **bije czystą
> EMA20/100** (✅D9/✅D11). Wynik zerowy = deliverable (zasada „zmierz
> przesłankę" — 2026-08-06 przesłanka padła 4/4 razy).

---

## RANKING KANDYDATÓW (dowody × wysiłek × koszty)

### 1. Volatility targeting — najmocniejsze dowody, próbować pierwsze

- Kanon: Moreira & Muir, *Volatility-Managed Portfolios*
  (https://www.nber.org/system/files/working_papers/w22208/w22208.pdf) —
  skalowanie ekspozycji odwrotnie do świeżej wariancji podnosi Sharpe'a.
- Man Group / Harvey et al., *The Impact of Volatility Targeting*
  (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538): dla aktywów
  risk-on Sharpe rośnie, a **redukcja drawdownu/lewego ogona jest odporna we
  wszystkich klasach aktywów** — krachy przychodzą przy wysokiej zmienności,
  gdy zmniejszona pozycja trzyma mniej.
- Koszty: DeMiguel et al. (JoF 2024,
  https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13395) — wersje
  wieloczynnikowe umierają na obrocie, ale **jedno-aktywowa wersja rynkowa
  przeżywa realistyczne koszty**. Nasz przypadek (jeden asset, long-only) jest
  tym korzystnym.
- Krypto: Concretum używa ~20% ann. target vol jako standard
  (https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/).
- **Parametry startowe do researchu:** EWMA vol 20–30 dni, target 25–35% ann.,
  cap wagi 1,0 (bez lewara — BTC vol 40–80% więc target głównie OBCINA
  ekspozycję), **pasmo bez-handlu 10–20%** (rebalans tylko przy dryfie wagi
  powyżej pasma) — to pasmo decyduje, czy podejście przeżywa 0,1% taker przy
  dziennej częstotliwości.
- Komponuje się z EMA20/100 bez dotykania sygnału (mnoży target position,
  nie zmienia decyzji kierunkowej).

### 2. Ensemble prędkości EMA — tanie, realne dowody

- Uśrednianie sygnału po kilku lookbackach redukuje ryzyko „szczęścia jednego
  parametru"; dowody w ensemble'ach kanałowych Concretum (Sharpe >1.5 na BTC
  i altach, j.w.). Treść blogowa o „MA ribbons" = folklor; zasada uśredniania
  po prędkościach = nie.
- Tanie do przetestowania w `scenario_lab.py` na danych sprzed holdoutu.
- Daily TSMOM na krypto przeżywa koszt 0,1%, umiera >~0,25%
  (https://link.springer.com/chapter/10.1007/978-981-99-6441-3_17) — nasza
  półka kosztowa jest przeżywalna, ale cienka.

### 3. Meta-labeler (pre-rejestrowana ścieżka ✅D11) — architektura OK, próba NIE

- Nasza konstrukcja spełnia oba warunki, przy których meta-labeling działa
  (QuantConnect *Not a Silver Bullet*,
  https://www.quantconnect.com/forum/discussion/14706/why-meta-labeling-is-not-a-silver-bullet/):
  pierwotna reguła jest STAŁA (EMA20/100), a meta-model dostaje INNE cechy
  (reżimowe). Meta-model nad zoptymalizowanym prymarem na tych samych cechach
  nie daje nic.
- Realistyczny uplift jest skromny: H&T na trend-followingu ES: accuracy
  48%→55% (https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy-triple-barrier-method/);
  pooled test na 10 krypto dziennie: +4,5%. Prosty filtr zmienności łapie
  większość korzyści — **to jest benchmark, który ML musi pobić**.
- 🔴 **Zabójcze zastrzeżenie — wielkość próby.** EMA20/100 1d robi 1,69
  round-tripa/rok ≈ 15–20 zdarzeń w CAŁEJ historii. Żadna publikacja nie
  operuje poniżej setek zdarzeń; klasyfikator na <30 próbkach nie istnieje
  uczciwie. Wyjście: **pooling BTC+ETH(+2–3 majorsy) z identyczną regułą**
  (tak zrobiło badanie 10-krypto; akceptowalne metodologicznie, importuje
  cross-asset distribution shift) ALBO najpierw benchmark z filtra
  zmienności i ML tylko, jeśli filtr pokaże sygnał.
- Narzędzia: `mlfinlab` jest PŁATNY (all rights reserved,
  https://github.com/hudson-and-thames/mlfinlab) — nie planować wokół niego.
  Otwarte: `hudson-and-thames/meta-labeling` (kod z papierów JFDS — materiał
  do nauki), `mlfinpy` (MIT, alpha). Dla jednego meta-labelera nad barami
  dziennymi: ~200 linii pandas+sklearn (z własnym purged splitem) > zależność.
- Pułapki z literatury: etykiety fixed-horizon degradują wynik (triple-barrier
  / trend-scanning), przecieki bez purging+embargo (embargo ≥ średni czas
  trzymania pozycji!), przekombinowane modele wtórne (praktycy: mocno
  regularyzowany XGBoost/RF albo regresja logistyczna), kalibracja
  prawdopodobieństw przed progowaniem.

### 4. Nowe dane/cechy (dla meta-labelera) — ranking wg dowody × wiarygodność

| Cecha | Dowody | Darmowe źródło | Historia | Point-in-time |
|---|---|---|---|---|
| **Funding rate** (poziom + skumulowany N-dni) | średnie (Edinburgh *Anatomy of perp returns*; BIS WP 1087 *Crypto carry* — wysoki carry przewiduje kaskady likwidacji) | `GET /fapi/v1/fundingRate` + bulki `data.binance.vision futures/um/monthly/fundingRate/` | bulk od 2020-01, API od 2019-09 | TAK (settled, nierewidowane) |
| **Δ OI × kierunek zwrotu** | średnie | bulki `futures/um/daily/metrics/` (REST trzyma tylko 30 dni!) | od 2020-09 | TAK |
| **MVRV-Z** | recenzowane (Grobys, ScienceDirect 2026 — bije B&H przez 3 cykle), ale to filtr CYKLU (tygodnie–miesiące), nie sygnał dzienny | Coin Metrics community CSV, github.com/coinmetrics/data | od genesis | małe ryzyko rewizji → **snapshotować** |
| **Basis perp–spot** liczony z własnych klines | średnie, mocno skorelowany z fundingiem | własne klines (endpoint `/futures/data/basis` trzyma 30 dni) | od 2019 | TAK (z konstrukcji) |
| SOPR | słabsze, skorelowany z MVRV | Coin Metrics CSV | od genesis | j.w. |

**ODRZUCONE Z DOWODEM (nie relitygować):**
- **Exchange flows/balances** — Glassnode SAM pokazał (2025/26,
  https://research.glassnode.com/why-use-point-in-time-data/), że rewizje
  etykiet podmiotów tworzą look-ahead: identyczna strategia na danych
  point-in-time przegapiła rajdy, które backtest na danych rewidowanych
  „łapał". Darmowa historia point-in-time nie istnieje.
- **Fear & Greed** — badanie 2018–2025 (ScienceDirect 2026): NIE
  Granger-przyczynuje zwrotów, zero zysku OOS; to zwroty przyczynują indeks.
- **Long/short ratio** — brak wiarygodnych dowodów; folklor.

### 5. HMM regime — ZDEGRADOWANY (niżej niż w planie)

- `hmmlearn` efektywnie niemaintainowany (brak release'ów 12+ mies.,
  https://snyk.io/advisor/python/hmmlearn) — jak używać, to z przypiętą wersją.
- 2-stanowy HMM na zmienności ≈ wymyślny próg realized vol — vol targeting
  łapie większość tego sygnału za darmo.
- Klasyczna pułapka smoothed-vs-filtered probabilities: ta sama strategia
  Sharpe 0,78 (uczciwe filtered) vs 1,74 (smoothed = look-ahead)
  (https://github.com/dmitridefreitas-dev/regime-detection). Jeśli kiedyś:
  wyłącznie filtered, refit walk-forward, max 2 stany.

---

## CO WOLNO ROBIĆ TERAZ (M5-safe)

1. **Research w `scenario_lab` na danych < 2026-07-16**: prototyp vol
   targetingu (z pasmem bez-handlu!) i ensemble EMA. Analiza legalna,
   adopcja po M5.
2. **Zbieranie danych od dziś**: bulk funding (2020-01+) i daily metrics
   (2020-09+) z data.binance.vision — niezmienne, regenerowalne;
   **snapshot CSV Coin Metrics TERAZ** (jedyne źródło z ryzykiem rewizji —
   mrożenie kopii dziś eliminuje przyszły look-ahead). Koszt: dysk.
3. **F7 (stop-loss + dzienny limit) i kwarantanna enterprise** — bez zmian,
   właściwa kolejność dla bezpieczeństwa.

## KOLEJNOŚĆ ADOPCJI (post-M5, każda przez harness M4)

vol targeting → ensemble EMA → prosty filtr zmienności jako benchmark →
dopiero potem meta-labeler (pooled BTC+ETH, cechy funding/ΔOI/MVRV-Z/basis,
triple-barrier, purged walk-forward + embargo, XGBoost/logit z silną
regularyzacją, kalibracja przed progiem).

## UCZCIWA PUENTA

Realistyczny sufit: lepszy risk-adjusted zwrot i płytsze obsunięcia — nie
drukarka. Spora szansa, że część kandydatów da wynik zerowy; to też jest
wynik. Oczekiwany uplift meta-labelera: ~10–20% poprawy precyzji/drawdownu
w NAJLEPSZYM razie.
