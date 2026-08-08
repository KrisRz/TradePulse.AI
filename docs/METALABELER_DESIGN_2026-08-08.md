# Meta-labeler — projekt PRE-REJESTROWANY na podstawie kanonu (2026-08-08)

> Synteza trzech równoległych kwerend źródłowych (splity walidacyjne ·
> klasyfikator na małej próbie · praktyka meta-labelingu end-to-end),
> wykonanych PRZED napisaniem jakiegokolwiek kodu modelu i przed obejrzeniem
> jakiejkolwiek korelacji cecha↔etykieta. Ten dokument JEST pre-rejestracją:
> implementacja (osobna sesja) ma go wykonać, nie renegocjować. Zmiana =
> osobny commit z uzasadnieniem + wpis w dzienniku prób.

## 0. Uczciwa prognoza, zanim padnie pierwsza liczba

Literatura mówi wprost: **mechanizm pasuje do nas idealnie, baza dowodowa —
nie.** Nasz przypadek (stała reguła nie-ML jako model pierwotny) to
podręcznikowy „white box" de Prado i jedyny wariant, którego nawet krytycy
(QuantConnect) nie skreślają. ALE: każdy opublikowany pozytywny wynik ma
10–100× więcej zdarzeń niż nasze 128, raportuje accuracy/precision zamiast
Sharpe'a, a dwie najpełniejsze ewaluacje PO Sharpie (eksperymenty
Baldisserriego, teza z Lund) wyszły NEGATYWNIE. Do tego trend-following
zarabia ogonem wielkich wygranych (u nas: mediana zdarzenia ujemna,
36% win rate) — a bramka „odfiltruj przegrane" oceniana symetryczną stratą
0/1 racjonalnie zmierza do „pomijaj wszystko" i skasowanie jednego ogona
odwraca znak Sharpe'a. **Najbardziej prawdopodobny wynik eksperymentu:
„zostajemy przy czystym EMA".** To jest OK — wynik negatywny to deliverable.

## 1. Protokół walidacji (kwerenda #1; de Prado AFML r.7, sklearn docs)

- **Purged 5-fold, bloki kalendarzowe WSPÓLNE dla 8 rynków**: zdarzenie
  trafia do folda po dacie wejścia, nigdy po aktywie ani indeksie; bloki
  ciągłe w czasie, ~równe licznością (~25–26 zdarzeń).
- **Purge po FAKTYCZNYCH przedziałach** [entry, exit] każdego zdarzenia
  (3 warunki nakładania z AFML), krzyżowo między aktywami — trening BTC
  nakładający się czasowo na test ETH wylatuje (hossa 2021 = jedno zdarzenie).
- **Embargo 30 dni** po stronie za-testem (reguła h≈1%·T; horyzont etykiety
  załatwia purging, NIE embargo — częsty błąd, nie popełniać).
- Jeśli purge zbije trening folda poniżej ~90 zdarzeń → 4 foldy zamiast 5
  (nigdy nie zmniejszać embarga).
- **Ocena wyłącznie na zbiorczych predykcjach out-of-fold** (wszystkie 128)
  z bootstrapowymi CI (~±8–9 p.p. na wskaźnikach) — pojedynczy fold
  (~26 zdarzeń) nie znaczy nic osobno. Raportować per-fold positive rate
  (widoczność nierównowagi reżimów 2021 vs 2022).
- **Diagnostyki, NIE kryteria selekcji**: leave-one-asset-out (8 foldów;
  test „czy to nie jest potajemnie model BTC") i CPCV(6,2) raz (15 splitów,
  5 ścieżek → rozkład wyniku zamiast jednej liczby).
- **Dziennik prób + budżet**: MinBTL przy ~8 latach skorelowanych danych →
  budżet KILKUDZIESIĘCIU konfiguracji NA CAŁE ŻYCIE projektu. Każda
  ewaluowana konfiguracja = wpis. Ten projekt = próba #1; benchmark XGBoost
  = próba #2. Przy >10 próbach liczyć deflated Sharpe z N prób.

## 2. Model (kwerenda #2; Peduzzi/van Smeden/Riley, sklearn, van der Ploeg)

- **Regresja logistyczna L2, NIE XGBoost.** EPV = 46 pozytywnych / cechy;
  literatura: modele elastyczne potrzebują ~10× więcej danych na stabilność
  (van der Ploeg 2014). XGBoost tylko jako pre-rejestrowany benchmark
  (max_depth 2, min_child_weight ≥5, eta ≤0,1, reg_lambda ≥5, natywne NaN;
  oczekiwanie: przegra).
- **Cechy: 5 + 1 wskaźnik braków, wybrane TERAZ, domenowo** (bez podglądania
  etykiet; zasada information advantage — model wtórny ma widzieć to, czego
  reguła EMA NIE widzi; teza z Lund: meta widzące głównie output prymarnego
  jest gorsze niż nic):
  1. `mvrv_z` — pozycja w cyklu on-chain (pokrycie 100%),
  2. `funding_cum30` — nagromadzony lewar/chciwość (86%),
  3. `vol_pctl_1y` — spokój zmienności; JEDYNA cecha, która w
     REGIME_FILTER kupowała płytszy DD (87%),
  4. `btc_trend_gap` — kontekst trendu całego rynku (100%),
  5. `dd_from_1y_high` — pozycja aktywa w jego cyklu (88%),
  6. `missing_era` — JEDEN wspólny wskaźnik „serie jeszcze nie istniały".
  WYKLUCZONE świadomie: `trend_gap` własny (to jest sygnał prymarny —
  zero information advantage), `ret20` (koreluje z trend_gap), surowy
  `vol20` (duplikat percentyla), `doi7/doi30` (pokrycie 73% — za dziurawe
  na 128 próbek), `funding_last` (szum 8h vs suma 30 d), `btc_vol20`
  (duplikat vol_pctl po stronie rynku).
- **Pipeline obowiązkowy** (oficjalna zasada anty-przeciekowa sklearn):
  SimpleImputer(median) → StandardScaler → LogisticRegression(L2) — całość
  wewnątrz CV; imputer/scaler NIGDY nie widzą foldu testowego.
- **C przez nested inner purged 3-fold na log-loss**, siatka {0,01, 0,03,
  0,1, 0,3} (nested tuning = 1 próba, nie 4 — Vabalas). Oczekiwać C ≪ 1.
- **Zero korekt balansu klas** (36% to łagodna nierównowaga; SMOTE/wagi
  psują kalibrację — van den Goorbergh 2022). Asymetria kosztów → próg.
- **Bez CalibratedClassifierCV** (logit skalibrowany z konstrukcji;
  isotonic wprost przeciwwskazany <1000 próbek). Krzywą kalibracji OOF
  tylko OBEJRZEĆ i zaraportować.

## 3. Cel treningu i użycie wyniku (kwerenda #3; de Prado r.3/r.10, H&T)

- **Wagi próbek = |net_return|** — inaczej model optymalizuje pomijanie
  tanich strat i drogich wygranych jednakowo; to główna pułapka profilu
  ogonowego.
- **Tłumienie zamiast wykluczania**: rozmiar pozycji w paśmie
  **0,5×–1,5×** przez sigmoid de Prado (r.10) ściśnięty do pasma; NIE
  twarda bramka 0/1. Błędna ocena wielkiej wygranej ma ją stłumić,
  nie skasować.
- **Diagnostyka ogona (pre-rejestrowana)**: raportować rangi P(win) dla
  top-5 wygranych zdarzeń w OOF. Model plasujący którąkolwiek z top-5
  poniżej mediany = czerwona flaga niezależnie od zbiorczego wyniku.
- Etykiety zostają nasze (realne round-tripy netto po kosztach) — to JEST
  kanoniczna meta-etykieta („outcome of the bet"); triple-barrier byłby
  potrzebny, gdybyśmy handlowali barierami PT/SL, a nie handlujemy
  (F7 stop 10% to close-eval na 4h; dla zdarzeń 1d bez zmiany).

## 4. Kryterium akceptacji (bez zmian od 2026-08-08, mechaniczne)

> 🔴 **KOREKTA REGUŁY po próbach #1–#2 (2026-08-08, osobny commit,
> uzasadnienie w METALABELER_RESULTS_2026-08-08.md §Korekta):** reguła
> poniżej okazała się podatna na artefakt jednostajnej dźwigni — model o
> ZEROWEJ dyskryminacji (rho(p,win)=−0,01) przeszedł ją 2/2, bo wagi
> |net_return| windują ważony base rate do ~0,85, sizing centrowany na 0,5
> nigdy nie schodzi poniżej 1× i „pobicie EMA" robi lewar, nie osąd.
> Od próby #3 werdykt wymaga DODATKOWO: (a) Spearman(p, win) > 0 przy
> p<0,10 na OOF; (b) ≥10% zdarzeń zsizowanych <1,0×; (c) 0 czerwonych
> flag w top-5 wygranych (flaga = automatyczny REJECT, koniec ze statusem
> „diagnostyka"). Próby #1–#2 ocenione TREŚCIOWO jako REJECT.

Strategia TŁUMIONA modelem (pasmo 0,5–1,5×, te same zdarzenia OOF) musi
pobić **czyste EMA20/100** na Sharpie po kosztach na zbiorczych ścieżkach
OOF, ORAZ nie przegrywać na większości z 5 ścieżek CPCV. Uplift w
accuracy/precision NIE jest dowodem niczego (pułapka metryki symetrycznej).
Przegrana → zostajemy przy czystym EMA, model do archiwum, wynik do docs.
Wygrana → pełny harness M4 → własne okno paper PO M5. Model po selekcji
ZAMROŻONY; monitoring realized-vs-predicted precision (refit przy ~16
zdarzeniach/rok to kosmetyka — nie udawać, że nie jest).

## 5. Źródła (zweryfikowane bezpośrednio w kwerendach)

de Prado, whitepaper GARP (AFML r.3/7/10 — purge/embargo/meta/sizing):
garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf · sklearn: common_pitfalls
(przecieki), modules/cross_validation (non-iid), modules/calibration,
modules/classification_threshold, TunedThresholdClassifierCV · Peduzzi 1996
+ van Smeden 2016/2019 + Riley 2019/2020 (EPV/shrinkage) · van der Ploeg 2014
(data hunger) · van den Goorbergh 2022 (szkodliwość korekt balansu) ·
Vabalas 2019 (CV na małych próbach) · Bailey & López de Prado (DSR, PBO,
MinBTL) · Hudson & Thames: toy example, Does Meta-Labeling Add to Signal
Efficacy (PDF), github.com/hudson-and-thames/meta-labeling (4 papery JFDS) ·
QuantConnect 14706 (krytyka) · teza Lund 9120301 (negatywny wynik OOS) ·
CFM (ogon trend-followingu) · studium 10-krypto (dev.to/nydartrading).
⚠️ mlfinlab.com = przejęta domena (hazard) — nie używać; fork: mlfinpy.

## 6. Dziennik prób (prowadzić od pierwszego uruchomienia)

| # | data | konfiguracja | wynik | wniosek |
|---|---|---|---|---|
| 1 | 2026-08-08 | logit L2, purged 4-fold (guard z 5), embargo 30 d, C nested→0,01×4, wagi \|ret\|, sizing 0,5–1,5× | mech. PASS 2/2 = artefakt dźwigni; rho(p,win)=−0,01; 0/128 stłumionych; 5/5 flag top-5 | **REJECT w treści** |
| 2 | 2026-08-08 | XGBoost benchmark (depth 2, mcw 5, eta 0,1, λ 5, natywne NaN) | identyczna degeneracja (+0,002) | REJECT; benchmark zgodny |
