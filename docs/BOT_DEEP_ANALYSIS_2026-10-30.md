# Głęboka analiza bota — 2026-10-30

> Prośba usera na koniec sesji: jak bot działa, co ma, czego mu brakuje, co mogłoby
> dać mu więcej wiedzy i lepsze decyzje, czy w internecie pojawiło się coś nowego.
> Dokument opisuje i rekomenduje. Niczego nie zmienia w kodzie. Każdy nowy pomysł
> idzie dalej wyłącznie przez pre-rejestrację (projekt w commicie przed liczbami).

## 1. Najkrócej

- **Bot podejmuje dobre decyzje rzadko i z małą przewagą, a jego główną wartością
  jest ograniczanie strat, nie trafianie w rynek.** Uczciwy Sharpe poza próbą 0,96–1,16
  wobec 0,81–1,00 dla trzymania BTC. Na Krakenie przy 0,80%: 0,97–1,13 wobec 0,80–0,98.
- **Największą dźwignią była ekspozycja, nie wiedza.** Połowa konta z korektą przesunęła
  limit 25% z 0–22% okien do 77–93% (zmierzone dziś na prawdziwej księdze). Żadne
  nowe źródło danych nie ma dowodu, że da choćby ułamek tego.
- **Z internetu (2024–2026) jedna rzecz warta taniego testu: implikowana zmienność
  z opcji (Deribit DVOL)** jako wejście do kandydata #12. Reszta to hype albo
  mechanizmy już odrzucone.
- **Najbardziej konkretny zysk operacyjny: zlecenie stop trzymane na Krakenie.**
  Chroni pozycję, nawet gdy nasza Lambda, AWS albo internet padną. Zmienia projekt
  executora.

## 2. Jak bot działa dziś (stan po 2026-10-30)

```
00:10 UTC  EventBridge Scheduler ──async──▶ Lambda tradepulse-paper-kraken
              │                                (ponowienia 2×, nieudane → DLQ → alarm)
              ▼
   feed.fetch_kraken_ohlc(XBTGBP, 1d)  — 399 zamkniętych barów, otwarty odrzucony
              ▼
   strategia: EMA20 > EMA100 → 1, inaczej 0           (jedyny „mózg”)
              ▼
   overlay: kill-switch konta (T1 −25% od szczytu, T3 −15% w barze) → 0 i HALT
            F7: stop 10% od wejścia na zamknięciu, dzienny limit straty 10%
              ▼
   księga PaperPortfolio: 50% konta w BTC, korekta do 50% poza 35–65%,
            opłata 0,80%, poślizg 2 bps, min. korekta £5
              ▼
   DynamoDB: stan + rekord decyzji (bar, cena, target, equity, …)
              ▼
   dead-man ping → healthchecks.io (mail, gdy cisza > ~26 h albo HALT)
```

Ocena: bramki A (zgodność z backtestem co do centa), B (rentowność, B5–B7),
C (koszty, tylko kanał z prawdziwymi fillami). Pilot £200 po P1–P4, najwcześniej
2026-11-27.

## 3. Co bot ma, a czego mu brakuje

| Obszar | Ma | Brakuje | Waga |
|---|---|---|---|
| Sygnał | 1 reguła trendu, sprawdzona na 9 latach i 4 układach okien | wiedzy o *stanie rynku* (zmienność oczekiwana, płynność) — wszystko, co próbowaliśmy, nie przeszło | średnia |
| Ryzyko pozycji | stop 10% i limit dzienny, liczone **raz dziennie** | ochrony **między uruchomieniami** i przy awarii Lambdy/AWS | **wysoka przed pilotem** |
| Ryzyko konta | 50% z pasmem, kill-switch 25% | — (zmierzone dziś: działa) | — |
| Wykonanie | model (paper) | executora Krakena: idempotencja, sprawdzenie zlecenia po timeoucie, status giełdy | **wysoka przed pilotem** |
| Koszty | taker 0,80% | post-only 0,40% przy korektach (nie spieszą się) | niska (grosze przy £200) |
| Gotówka | 0% | odsetek — **Kraken UK ich nie da** (niżej) | niska |
| Dane do oceny | 720 świec Krakena | archiwum barów (bramka A przestanie działać ~315. dnia) | średnia, termin ~2027-09 |
| Obserwowalność | 4 alarmy, dead-man, raporty bramek | — | — |

## 4. Research: nowe źródła wiedzy (2024–2026), ocenione krytycznie

Ograniczenie strukturalne: bot zamyka ~1,7 transakcji rocznie. Seria danych zaczynająca
się w 2021–2024 obejmuje 4–9 sygnałów. **Na poziomie transakcji nic nowego nie da się
zwalidować.** Jedyny uczciwy test to obserwacje dzienne (czy cecha w dniu t przewiduje
zmienność / maksymalny spadek w kolejnych 20–60 dniach), z bootstrapem blokowym
i progiem zapisanym z góry. Moc będzie niska.

| Źródło | Co mówi dowód | Werdykt |
|---|---|---|
| **Deribit DVOL** (30-dniowa implikowana zmienność BTC) | Darmowe, bez kluczy, bez rewizji; **sprawdzone: historia od 2021-03-24**. Prace (Almeida i in. 2024; Alexander & Imeraj) opisują premię za ryzyko zmienności, ale **nikt nie pokazał przewidywania spadków poza próbą**. Od 2023 DVOL rośnie *razem* z ceną, więc reguła „wysoka zmienność = wyjdź” może ciąć najlepsze odcinki. | **Test #1:** jako *oczekiwana* zmienność w kandydacie #12 (odrzucony #1 używał zmienności zrealizowanej — to inny mechanizm). Osobno: premia VRP / odwrócona struktura terminowa jako flaga ryzyka. |
| Realne stopy (FRED DFII10), szeroki dolar (DTWEXBGS) | darmowe, bez rewizji; korelacje niestabilne między epokami (Molnar 2026) | Tani test falsyfikacyjny, niski prior |
| Podaż stablecoinów (DefiLlama) | jedyna recenzowana praca (Wei 2018) — brak przewidywania; reszta to marketing vendorów; endogeniczna wobec ceny | Niski prior; zrobić snapshot danych, zanim się im zaufa |
| **Przepływy ETF BTC** | DWF Labs 2026 (694 dni): korelacja z *poprzednimi* 5 dniami 0,54, z *następnymi* 0,03 — przepływy idą za ceną. Regresje „R² 95%” to klasyczna regresja pozorna na poziomach. | **Hype.** Bot trendowy już ma tę informację. |
| Globalne M2 „wyprzedza BTC” | zerwało się w 2025 (M2 +12% r/r, BTC −12%) | **Hype** |
| On-chain point-in-time (Glassnode) | potwierdza nasz stary wniosek o look-ahead; dane PiT dopiero od 07.2025 i płatne | Do backtestu bezużyteczne |
| Wczesne ostrzeganie przed krachem (LPPLS, „critical slowing down”) | na danych dziennych nie działa wg własnych autorów; działa tylko na minutach/perpach i odwraca się na holdoucie | **Odpada** |
| Nowe prace o DD w trendzie krypto (Zarattini 2025, AdaptiveTrend 2026, Talyxion) | dźwignia, short, rotacja 20 coinów, strojenie Optuną — wszystko odrzucone albo zabronione dla nas | Nic do przeniesienia |
| LLM jako trader | Alpha Arena: większość modeli straciła; Look-Ahead-Bench: przewaga znika poza danymi treningowymi | **Odpada** (sprawdzone wcześniej tego dnia) |

Ciekawostka bez wartości handlowej: praca Molnara (2026) zapisuje z góry „dno 2026
między 5.10 a 16.11”. To darmowy test poza próbą cudzej hipotezy — obserwować, nie
handlować.

## 5. Research: Kraken od strony operacyjnej (z dokumentacji Krakena)

Źródło: raport researchu z oficjalnej dokumentacji. Strony API Krakena renderują się
w JS i nie dało się ich przeszukać curlem, więc **pola zleceń potwierdzimy przy budowie
executora przez `validate=true`**.

- **Stop po stronie giełdy.** `AddOrder` przyjmuje `stop-loss`, `stop-loss-limit`,
  `trailing-stop`. Zlecenie stop **blokuje BTC** (hold), więc korekta i wyjście muszą
  najpierw je anulować. Wyzwolony stop to zlecenie rynkowe z opłatą taker.
- **Nie używać `CancelAllOrdersAfter`** jako dead-mana: anulowałby też ochronny stop,
  a Lambda raz dziennie nie utrzyma go przy życiu.
- **Idempotencja:** `cl_ord_id` (UUID albo do 18 znaków ASCII, unikalny tylko wśród
  *otwartych* zleceń) + `deadline` (giełda odrzuca żądanie po czasie). Po timeoucie
  szukać po `cl_ord_id` w `OpenOrders` **i** `ClosedOrders`. To ta sama pułapka co na
  Binance: unikalność nie chroni przed duplikatem po wypełnieniu.
- **Opłaty:** `AssetPairs` przestał zwracać opłaty (8.09.2026) — prawdziwą stawkę
  czytać z `TradeVolume`. Post-only (`oflags=post`) oszczędza 0,40% na stronie.
- **Gotówka:** wg strony regulacyjnej Krakena klienci z UK **nie mogą używać Opt-in
  Rewards**. Gotówkowa połowa na Krakenie zarabia 0%.
- **Przed handlem:** `SystemStatus` ma od 1.09.2026 pola o planowanej przerwie
  i awarii — sprawdzać przed wysłaniem zlecenia.
- **Klucz:** uprawnienia bez wypłat, IP whitelist opcjonalny (Lambda bez stałego IP
  działa), `GetApiKeyInfo` pozwala botowi sprawdzić na starcie, że klucz **nie ma**
  prawa wypłat.

## 6. Rekomendacje, w kolejności

### Przed pilotem (wymagane, w trakcie 28 dni papieru)

1. **Executor Krakena z ochroną po stronie giełdy.** Po każdym wejściu: zlecenie
   `stop-loss` na 10% poniżej wejścia, trzymane na giełdzie. Korekta i wyjście:
   anuluj stop → handel → nowy stop. Idempotencja przez `cl_ord_id` + `deadline` +
   wyszukanie w otwartych i zamkniętych. `SystemStatus` przed handlem.
   `GetApiKeyInfo` na starcie: brak prawa wypłat albo stop.
   ⚠️ Stop na giełdzie działa na cenie bieżącej, a nasz F7 na zamknięciu dnia —
   to **inna reguła niż w backteście**. Rozwiązanie do pre-rejestracji: stop
   giełdowy jako *awaryjny* (np. 15–20%, szerzej niż F7), F7 dalej decyduje na
   zamknięciu. Wtedy backtest = bot w normalnych dniach, a giełda chroni tylko
   przy katastrofie.
2. **Pre-rejestracja zasad executora** (ten punkt i kolejność anuluj → handel → stop),
   testy, próby na `validate=true`.

### Badania (każde: projekt w commicie przed liczbami)

3. **Kandydat #12 w dwóch wariantach:** wielkość pozycji wg zmienności zrealizowanej
   i wg **DVOL**, oba z pasmem bez handlu, od 2021-03-24. Punkt odniesienia:
   **dzisiejsze `w = 0,5` z pasmem 0,15**, nie sama strategia. Przyjmujemy tylko,
   jeśli pobije je na DD przy nie gorszym Sharpe.
4. **Test dzienny DVOL/VRP/struktura terminowa → maksymalny spadek w 30 dni**
   wobec bootstrapu blokowego. Jeśli nie przejdzie zera — koniec tematu.
5. **Jeden przebieg falsyfikacyjny** realne stopy + dolar + stablecoiny. Niski prior.

### Porządki

6. **Archiwum barów Krakena** (codzienny zapis zamkniętego baru do DynamoDB/S3)
   przed ~2027-09, inaczej bramka A przestanie działać.
7. **Provider AWS 6.x → runtime python3.14** (plan, pozycja 9; kod gotowy — 480/480
   testów na pandas 3.0.2).

### Czego nie robić

Przepływy ETF, M2, sentyment i Fear & Greed, on-chain bez PiT, LLM jako decydent,
dźwignia, short, perpy, dokładanie monet, ML na 128 zdarzeniach, „wczesne
ostrzeganie” na danych dziennych.

## 7. Decyzje dla usera

- **Gotówkowa połowa poza Krakenem?** Na Krakenie UK zarabia 0%. Konto
  oszczędnościowe w banku daje ~4% na ~£100, czyli ~£4 rocznie, ale przy każdym wejściu
  trzeba by przelać pieniądze ręcznie (Faster Payments, zwykle minuty). Przy £200
  rekomendacja: **zostawić na Krakenie**. Wrócić do tematu przy większym kapitale.
- **Szerokość awaryjnego stopu na giełdzie** (pkt 1): rekomendacja 20% od wejścia —
  rzadko się uruchomi w normalny dzień, a chroni przed nocnym krachem przy awarii.
  Do potwierdzenia w pre-rejestracji executora.

## Źródła

- Deribit DVOL API (historia od 2021-03-24 sprawdzona wywołaniem): https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data.md
- Almeida i in., „Risk Premia in the Bitcoin Market” (2024): https://econpapers.repec.org/paper/arxpapers/2410.15195.htm
- Alexander & Imeraj, „The Bitcoin VIX and its Variance Risk Premium”: https://sro.sussex.ac.uk/id/eprint/91094/
- DWF Labs o przepływach ETF (2026): https://cointelegraph.com/news/bitcoin-etf-flows-follow-price-trends-dwf-labs
- BIT, M2 decoupling (2026): https://www.bit.com/knowledge-hub/global-m2-decoupling
- Wei (2018), emisja Tethera: https://ideas.repec.org/a/eee/ecolet/v171y2018icp19-22.html
- Glassnode, dane point-in-time: https://docs.glassnode.com/data/point-in-time-metrics
- Shu & Zhu, LPPLS (Physica A 2020): https://arxiv.org/pdf/1905.09647v2.pdf
- Garcia Seuma, liquidation cascades (2026): https://arxiv.org/abs/2607.27070
- Molnar, „Bitcoin Runs on a Clock” (2026): https://arxiv.org/abs/2607.26188
- Zarattini, Pagani, Barbon (2025): https://ideas.repec.org/p/chf/rpseri/rp2580.html
- AdaptiveTrend (2026): https://arxiv.org/html/2602.11708v1
- Kraken AddOrder: https://docs.kraken.com/api/docs/rest-api/add-order
- Kraken CancelAllOrdersAfter: https://docs.kraken.com/api/docs/rest-api/cancel-all-orders-after
- Kraken changelog: https://docs.kraken.com/api/docs/change-log
- Kraken stop-loss: https://support.kraken.com/articles/7699391647892-stop-loss-orders
- Kraken, regulacje i Opt-in Rewards w UK: https://support.kraken.com/se/articles/where-is-kraken-licensed-or-regulated
- Kraken fee schedule: https://www.kraken.com/features/fee-schedule
