# Filtry reżimu nad EMA20/100 (idea warstwy L1) — werdykt OOS: 3× REJECT (2026-08-08)

> Zapożyczamy POMYSŁY z 6 warstw, nie kod — to był pierwszy: warstwa L1 miała
> rozpoznawać reżim rynku i bramkować wejścia. Nowy kod
> (`scripts/research/regime_filter_oos.py`), ten sam rygor co przy ensemble:
> filtry pre-specyfikowane bez strojenia, wyłącznie spany OOS 4 layoutów
> scenario_lab, siatka prowizji, holdout <2026-07-16, reguła zarejestrowana
> PRZED pierwszą liczbą. To był też punkt #1 kolejki researchu: prosty filtr
> reżimu/zmienności = poprzeczka, którą przyszły meta-labeler musi pobić.

## Filtry (podręcznikowe, spisane przed uruchomieniem)

Każdy bramkuje TYLKO stronę long (w = sygnał_EMA × filtr) — może bota
wyciągnąć z rynku, nigdy wprowadzić w nowy typ pozycji:

1. `price>SMA200` — trzymaj longi EMA tylko powyżej średniej 200d
2. `SMA200 rising` — tylko gdy średnia 200d rośnie (diff 20d)
3. `calm vol` — tylko gdy zrealizowana zmienność 20d jest poniżej własnego
   kroczącego 80. percentyla z roku (stan „volatile" z L1, bez look-ahead)

## Werdykt: wszystkie trzy REJECT — czyste EMA20/100 znów wygrywa

Sharpe @ prowizja 0,1% (OOS):

| layout | **czyste EMA** | price>SMA200 | SMA200 rising | calm vol |
|---|---|---|---|---|
| (730, 180) | **0,96** | 0,89 | 0,83 | 0,90 |
| (500, 125) | **1,07** | 1,02 | 0,81 | 1,03 |
| (1000, 250) | **1,16** | 1,11 | 1,00 | 1,11 |
| (365, 90) | **1,04** | 0,99 | 0,78 | 1,00 |

- `SMA200 rising` — najgorszy (Sharpe 0,75–1,00), odpada bez dyskusji.
- `price>SMA200` — nie dość, że tnie Sharpe'a, to **POGARSZA drawdown**
  (−59% wobec −50% baseline'u w każdym layoucie): filtr rozjeżdża się w
  fazie z EMA i wymusza bycie poza rynkiem/w rynku w złych momentach.
- `calm vol` — jedyny z sensowną historią: **DD spada do −43…−45%**
  (z −50%) i to on przechodzi check DD. Ale kosztuje ~0,05 Sharpe'a w
  KAŻDYM layoucie (2 z 3 checków FAIL). Płacisz zwrotem za spokój — to
  ta sama waluta, w której vol targeting oblał M4/F2. Spójny wynik.

## Co z tego wynika

1. **Poprzeczka dla meta-labelera = czyste EMA20/100.** Żaden prosty filtr
   jej nie podniósł. To upraszcza przyszłą decyzję: model ML musi pobić
   goły sygnał, bez gwiazdek.
2. **Idea L1 w wersji prostej (progi na trendzie/zmienności) nie dodaje
   wartości na 1d.** Jeśli reżim ma pomóc, to jako CECHA w uczonym modelu
   (funding, ΔOI, MVRV-Z, zmienność razem), nie jako ręczna bramka 0/1.
   Dokładnie to przewiduje ścieżka ✅D11.
3. **Tania część kolejki researchu jest WYCZERPANA.** Vol targeting (M4/F2),
   ensemble (OOS), mean reversion (4×), filtry reżimu (3×) — wszystko
   zmierzone i odrzucone. Zostaje meta-labeler, a ten czeka na próbę
   >100 zdarzeń (pooling BTC+ETH daje dziś 31). Od teraz research znaczy:
   czekać, aż dane urosną — albo nowa hipoteza jakościowo inna od
   zmierzonych.
4. Siódmy pretendent odparty. `calm vol` zapisujemy jako kandydata na
   cechę (nie bramkę) meta-labelera — jedyne, co realnie kupował, to
   płytszy DD.

## Jak powtórzyć

```bash
PYTHONPATH=. python scripts/research/regime_filter_oos.py
```

Wynik maszynowy: `docs/regime_filter_oos_result.json`. Reguły nie wolno
edytować po zobaczeniu wyników.
