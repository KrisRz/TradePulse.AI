# Kandydat #12 — wielkość pozycji według zmienności, z pasmem — PROJEKT PRE-REJESTROWANY (2026-11-15)

> Zapisany i scommitowany **przed** uruchomieniem jakiegokolwiek wariantu kandydata.
> Reguła decyzji na końcu jest wiążąca. Skrypt drukuje SHA-256 tego pliku.

## Pytanie

Czy konto, które trzyma **mniej BTC przy wysokiej zmienności i więcej przy niskiej**,
ma płytsze spadki niż dzisiejsze stałe `w = 0,5` z pasmem 0,15, i czy ta poprawa
bierze się z wyczucia zmienności, a nie z samego zmniejszenia ekspozycji?

## Co wiemy przed pomiarem

- **Punkt odniesienia** (`docs/KRAKEN_SIZING_RESULTS_2026-10-30.md`, model):
  `w = 0,5`, pasmo 0,15: maxDD −26,7%, CAGR +19,7%, DD ≤ 25% w 94% okien 365 d
  i 78% okien 730 d, 0,6 korekty rocznie, 0,07% kosztu rocznie.
- **Przesłanka** (`scripts/research/premise_recent_window.py`, 2026-11-14):
  zmienność z 20 dni wobec następnych 20: korelacja 0,49. Gdy bot jest LONG przy
  wysokiej zmienności, najgorszy spadek w kolejnych 20 dniach to −39,5% wobec
  −21,4% przy niskiej.
- **Historia:** #1 (cel zmienności bez pasma, M4/F2) odrzucony, bo zjadły go obroty.
  Przesłanka, która przeszła, nie jest obietnicą (#9, #10).
- Żadna liczba kandydata #12 nie jest znana w chwili commitu tego dokumentu.

## Model (taki sam jak punktu odniesienia)

`scripts/research/kraken_sizing_study.py` bez zmian w rachunku:
- strategia EMA20/100 + stop F7 10%, `run_backtest`, opłata **0,80%**, slippage
  2 bps, cena w GBP, dane `< 2026-07-16`, od 2018-01-01;
- konto £200, gotówka 0%, minimalna transakcja £5;
- dzienna stopa części zainwestowanej = dzienna stopa krzywej strategii;
- post-only (0,40%) **nie** jest zaliczane: koszt liczony ostrożnie, po 0,80%.

## Kandydat

Docelowy udział BTC na dzień `t+1`, znany po zamknięciu dnia `t`:

```
w_t = clip( 0,5 × M_t / σ_t ,  0,25 ,  0,65 )
```

- `σ_t` — estymator zmienności z danych do zamknięcia dnia `t` włącznie;
- `M_t` — mediana wszystkich wartości `σ` do dnia `t` włącznie (rosnące okno, co
  najmniej 60 wartości). Bez patrzenia w przyszłość: przy typowej dla dotychczasowej
  historii zmienności konto trzyma 0,5;
- sufit **0,65** = górna krawędź dzisiejszego pasma i limit `MAX_EXPOSURE`
  executora; kandydat nigdy nie celuje wyżej, niż punkt odniesienia może zadryfować;
- podłoga **0,25**.

Estymatory:
- **RV20, RV60** — odchylenie standardowe dziennych logarytmicznych stóp zwrotu
  ceny zamknięcia w GBP z 20 / 60 dni, × √365;
- **DVOL** — dzienne zamknięcie indeksu Deribit DVOL (BTC), publiczne API, od
  2021-03-24.

Handel:
- wejście w pozycję: w grę idzie `w × konto`, gdzie `w` to wartość z zamknięcia
  dnia poprzedzającego wejście;
- po zamknięciu każdego dnia w pozycji: jeśli |udział BTC − `w_t`| > `b`, transakcja
  przywraca `w_t`; opłata 0,80% od kwoty, poniżej £5 pomijamy;
- **jedno pasmo** obsługuje i dryf ceny, i zmianę zmienności: korekta następuje
  dopiero, gdy rozjazd z celem przekroczy `b`. To jest „próg na korektach ze
  zmienności” — małe ruchy `σ` nie powodują transakcji.

Siatka: estymator ∈ {RV20, RV60, DVOL} × `b` ∈ {0,10; 0,15} = **6 wariantów**.
Niczego poza tą siatką nie uruchamiam.

Sprawdzenie harnessu przed liczbami kandydata: przy `σ_t = M_t` (stały cel 0,5)
i `b = 0,15` skrypt musi odtworzyć punkt odniesienia **co do bitu** (`==` na
krzywej konta).

## Kontrola „sama ekspozycja”

Dla każdego wariantu liczę **kontrolę**: stałe `w` równe średniemu `w_t` kandydata
z dni w pozycji, to samo pasmo `b`. Kontrola ma tę samą średnią ekspozycję, ale nie
zna zmienności. Bez niej każdy wariant, który po prostu trzyma mniej BTC, wyglądałby
jak ulepszenie.

## Raport dla każdego wariantu, kontroli i punktu odniesienia

- maxDD z całej próby, CAGR, Sharpe (dzienne stopy konta, × √365);
- odsetek okien 365 i 730 dni (start co 7 dni) z DD ≤ 25% i mediana DD;
- liczba korekt na rok i ich koszt w % rocznie; średni, minimalny i maksymalny `w_t`
  w pozycji;
- maxDD osobno w połowach 2018–2021 i 2022–2026.

Warianty DVOL liczone na okresie, w którym DVOL istnieje (start po zebraniu 60
wartości); punkt odniesienia i warianty RV przeliczam na **tym samym** okresie do
porównania.

## REGUŁA DECYZJI (wiążąca)

Wariant RV **przechodzi**, gdy spełnia wszystkie warunki na całej próbie:

1. **Spadki względem punktu odniesienia:** maxDD płytszy o co najmniej **2,0 pp**
   oraz odsetek okien z DD ≤ 25% nie niższy ani dla 365, ani dla 730 dni.
2. **Sharpe ≥ Sharpe punktu odniesienia − 0,10.**
3. **Lepszy niż sama ekspozycja:** maxDD płytszy od kontroli o co najmniej
   **1,0 pp** oraz CAGR nie niższy od kontroli o więcej niż **0,5 pp**.
4. **Stabilność:** maxDD nie głębszy niż punktu odniesienia w **żadnej** z połów
   2018–2021 i 2022–2026.

**#12 PRZYJĘTY**, gdy przechodzą co najmniej **2 z 4** wariantów RV (sąsiedzi
potwierdzają, że to nie jeden szczęśliwy punkt siatki). Wybieram wtedy szersze
pasmo, a przy remisie dłuższe okno (mniej transakcji).

**#12 ODRZUCONY** w każdym innym przypadku. Zostaje `w = 0,5` z pasmem 0,15.

**DVOL** nie może zostać przyjęty z tego pomiaru: próba jest za krótka (od 2021).
Jeśli na wspólnym okresie wariant DVOL spełnia warunki 1–3 i ma maxDD płytszy od
najlepszego wariantu RV o co najmniej 1,0 pp, wynik brzmi „obiecujący” i jedynym
następstwem jest osobny projekt pomiaru równoległego na papierze. W przeciwnym
razie DVOL jest odrzucony jako wejście.

Progów nie luzuję po zobaczeniu liczb. Wszystko, czego projekt nie przewidział,
zapisuję w wynikach bez renegocjacji reguły.

## Co przyjęcie znaczy, a czego nie

- Przyjęcie to wynik **modelu**. Przed jakimkolwiek użyciem: zmienny cel w księdze
  (`PaperPortfolio`), odtworzenie wyniku na implementacji bar po barze (jak
  `kraken_book_replay.py`), test równoważności, mutacje.
- Kanał paper Kraken i pilot mają zapisane `w = 0,5` z pasmem 0,15
  (`docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md`). Zmiana sposobu trzymania
  pozycji na tych kanałach to **decyzja usera i nowy dokument**, nie skutek tego
  pomiaru.
- To 12. kandydat w rejestrze (11 zmierzonych, 11 odrzuconych), 6 wariantów.
