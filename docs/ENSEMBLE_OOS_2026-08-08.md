# Ensemble prędkości EMA — werdykt OOS: REJECT (2026-08-08)

> Kontynuacja studium z 2026-08-07 (`ema_ensemble_study.py`), które na pełnej
> próbie dało kandydata GO (Sharpe 0,93→0,98, DD −37→−30, 6/9 lat). To był
> skrining, nie werdykt. Dziś ten sam ensemble przeszedł przez uczciwy harness:
> **wyłącznie spany OOS, 4 layouty scenario_lab, siatka prowizji, B&H obok,
> reguła decyzyjna zarejestrowana PRZED pierwszą liczbą.**
>
> Narzędzie: `scripts/research/ema_ensemble_oos.py` (wynik maszynowy:
> `docs/ema_ensemble_oos_result.json`). Holdout <2026-07-16 wyegzekwowany
> w kodzie. Zero fittingu: rodzina 5 memberów (10/50, 15/75, 20/100, 30/150,
> 40/200) była pre-specyfikowana 2026-08-07, przed jakimkolwiek wynikiem.
> Poziom zwrotów, konwencja M4/F2 (decyzja close(t), zwrot o(t+1)→o(t+2),
> koszt = (fee+slip)·|Δw|) — celowo BEZ silnika, bo silnik zaokrągla pozycje
> do ±1/0, a wsparcie ułamkowe to dokładnie koszt adopcji, o którym to studium
> rozstrzyga.

## Reguła (spisana 2026-08-08, przed uruchomieniem)

Wszystkie cztery muszą przejść; trzy z czterech to odrzucenie:

1. ens Sharpe ≥ baseline w ≥3/4 layoutów @ fee 0,1% → **PASS** (3/4)
2. ens Sharpe ≥ baseline w ≥3/4 layoutów @ fee 0,2% → **FAIL** (2/4)
3. ens Sharpe > B&H w ≥3/4 layoutów @ fee 0,2% → **PASS** (4/4)
4. ens maxDD nie gorszy od baseline w ≥3/4 layoutów @ fee 0,1% → **FAIL** (2/4)

**→ REJECT. Ensemble spada z kolejki adopcji.**

## Liczby (Sharpe @0,1% / @0,2%, OOS)

| layout | baseline | ensemble | Δ @0,1% | Δ @0,2% | DD base | DD ens |
|---|---|---|---|---|---|---|
| (730, 180) | 0,96 / 0,96 | 0,95 / 0,94 | −0,012 | −0,015 | −49,7% | −45,4% |
| (500, 125) | 1,07 / 1,07 | 1,08 / 1,07 | +0,004 | +0,001 | −49,7% | −53,8% |
| (1000, 250) | 1,16 / 1,15 | 1,21 / 1,20 | **+0,049** | +0,046 | −49,7% | −45,4% |
| (365, 90) | 1,04 / 1,04 | 1,04 / 1,03 | +0,002 | −0,001 | −49,7% | −53,8% |

Obrót: baseline 2,9–3,3 jedn./rok, ensemble 4,0–4,3 (+~32%).

## Dlaczego pełna próba kłamała (uczciwa diagnoza)

1. **Cała przewaga siedzi w jednym layoucie.** (1000, 250) daje +0,05 Sharpe'a;
   pozostałe trzy to ±0,01 — szum. Pełnopróbkowe „0,93→0,98" było uśrednieniem
   tego jednego zwycięstwa z trzema remisami, plus wkład wczesnych lat
   (2017–2019), które w spanach OOS z długim burn-inem w ogóle nie występują.
2. **Wyższy obrót zjada mikro-przewagę dokładnie na progu stresu.** +32%
   obrotu × 0,2% = różnica, która wystarcza, żeby (365, 90) przeszedł z +0,002
   na −0,001. Przewaga, którą zabija jeden krok prowizji, nie jest przewagą.
3. **Poprawa drawdownu była artefaktem punktu startu.** −37→−30 z pełnej próby
   rozpada się per-layout na 2× lepiej (−45,4%) i 2× gorzej (−53,8%) —
   zależnie od tego, gdzie zaczyna się span OOS względem cyklu 2021–22.
   Frakcyjne wagi wchodzą w krach z ekspozycją ~0,6 zamiast 0/1 — czasem to
   amortyzuje, czasem dokłada.

## Co z tego wynika

- **Nie budujemy pozycji ułamkowych w księdze/silniku** — jedyny powód
  inżynieryjny właśnie odpadł. To oszczędza realny post-M5 wysiłek.
- **EMA20/100 pozostaje niezdetronizowane** — po vol targetingu (M4/F2),
  nodze short, kanale ETH i 4h-jako-skrócie to piąty kandydat, który poległ
  na uczciwym pomiarze. Wniosek z audytu kalibracji („nigdy nie wybrany
  walk-forwardem, ale trzyma się") dalej stoi.
- **Kolejka adopcji po korekcie:** benchmark-filtr zmienności (istnieje w
  `vol_targeting_study.py::regime_filter_study`, do przepuszczenia przez ten
  sam rygor OOS) → meta-labeler dopiero, gdy pooling da >100 zdarzeń
  (dziś BTC+ETH = 31 — za mało).
- Wzorzec potwierdzony piąty raz: **skrining pełnopróbkowy ≠ werdykt;
  wynik negatywny to deliverable** (zasada „zmierz przesłankę").

## Jak powtórzyć

```bash
PYTHONPATH=. python scripts/research/ema_ensemble_oos.py
```

Reguły nie wolno edytować po zobaczeniu wyników — zmiana reguły = osobny
commit z uzasadnieniem + przeliczenie od zera.
