# Meta-labeler — wynik prób #1–#2: REJECT w treści (2026-08-08)

> Implementacja DOKŁADNIE wg pre-rejestracji (METALABELER_DESIGN_2026-08-08):
> `scripts/research/metalabeler.py`, wynik maszynowy
> `docs/metalabeler_result.json`. Fold guard zadziałał zgodnie z projektem
> (trening <90 po purge → 4 foldy po 32 zdarzenia; purge 7–20 zdarzeń/fold;
> nested C wybrał 0,01 — maksymalny shrinkage z siatki — we WSZYSTKICH
> foldach, czyli dane same mówią „prawie nic we mnie nie ma").

## Co wyszło mechanicznie — i dlaczego to artefakt

Reguła werdyktu spisana w projekcie przeszła 2/2:
Sharpe per-event tłumiony vs czysty +0,002 [CI 95%: −0,000…+0,011],
CPCV 4/5 ścieżek. **ALE pre-rejestrowana diagnostyka obnażyła, skąd to się
wzięło:**

1. **Zero dyskryminacji.** Spearman(p, net_return) = **0,04** (p=0,67);
   Spearman(p, win) = **−0,01** (p=0,90). Predykcje modelu są statystycznie
   NIEZWIĄZANE z wynikami zdarzeń.
2. **Rozkład prawdopodobieństw zdegenerowany**: wszystkie p ∈ [0,60; 0,95],
   nigdy <0,5 → wszystkie rozmiary ∈ [1,08; 1,48], **0/128 zdarzeń realnie
   stłumionych**. Pasmo „tłumienia" stało się jednostajną dźwignią ~1,3×.
   Mechanizm: wagi treningowe |net_return| (celowe, §3 projektu) windują
   WAŻONY base rate z 36% do ~0,85 — a formuła sizingu de Prado zakłada
   środek w 0,5. Niespójność §2↔§3 projektu, ujawniona dopiero pomiarem.
3. **Top-5 wygranych: 5/5 CZERWONYCH FLAG** (rangi 0,01–0,14) — największe
   wygrane lądują na DNIE rozkładu predykcji. Dokładnie pułapka ogona,
   przed którą ostrzegała literatura.
4. LOAO: lepiej w 3/8 aktywów (szum). XGBoost benchmark: identyczna
   degeneracja (+0,002).

Dźwignia 1,3× na dodatnio-sumującej serii podbija sumę zwrotów mechanicznie
(+148→+175) — to nie jest osąd modelu, tylko lewar. Reguła werdyktu w
projekcie nie przewidziała tego trybu porażki.

## Werdykt w treści: REJECT — zostajemy przy czystym EMA20/100

Rozstrzyga punkt 1: żadna formuła sizingu nie naprawi modelu o zerowej
dyskryminacji — poprawianie §3 (np. centrowanie sizingu na ważonym base
rate) tylko sprowadziłoby wynik do gated≈plain. **Cechy (mvrv_z,
funding_cum30, vol_pctl_1y, btc_trend_gap, dd_from_1y_high) nie niosą
wykrywalnego sygnału o wyniku wejść EMA przy N=128** — dokładnie to
przewidywała uczciwa prognoza z §0 projektu (brak opublikowanego pozytywu
przy tej wielkości próby; obie pełne ewaluacje po Sharpie w literaturze
negatywne). Ósmy pretendent odparty; prognoza literatury potwierdzona
pomiarem.

## Korekta reguły werdyktu (osobny commit, zgodnie z dyscypliną)

Reguła „pobij Sharpe'a + wygraj ≥3/5 CPCV" jest podatna na artefakt
jednostajnej dźwigni. Przy KAŻDYM przyszłym powrocie do meta-labelera
werdykt wymaga DODATKOWO (pre-rejestrowane od teraz):
- Spearman(p, win) > 0 z p<0,10 na OOF, ORAZ
- ≥10% zdarzeń zsizowanych PONIŻEJ 1,0× (model musi faktycznie tłumić),
- 0 czerwonych flag w top-5 wygranych (flaga → automatyczny REJECT,
  nie „diagnostyka").

## Dziennik prób (stan po tej sesji)

| # | data | konfiguracja | wynik | wniosek |
|---|---|---|---|---|
| 1 | 2026-08-08 | logit L2, purged 4-fold, embargo 30d, C nested→0,01, wagi \|ret\|, sizing 0,5–1,5× | mech. PASS 2/2, ale rho(p,win)=−0,01, 0/128 stłumionych, 5/5 flag | REJECT w treści — zero dyskryminacji |
| 2 | 2026-08-08 | XGBoost benchmark (fixed: depth 2, mcw 5, eta 0,1, λ 5) | identyczna degeneracja (+0,002) | REJECT; benchmark potwierdza |

Budżet prób: wykorzystano 2 z ~kilkudziesięciu na życie projektu.

## Warunki uczciwego powrotu do tematu (nie „a może jednak")

1. **Więcej zdarzeń**: ~2× przyrost = poszerzenie uniwersum poolingu
   (kolejne majorsy z ≥5-letnią historią, wg tej samej reguły) albo czas.
2. **Nowe cechy o realnej hipotezie** (nie kolejne przekształcenia tych
   samych pięciu) — np. funding per-aktywo (dziś tylko BTC).
3. Skorygowana reguła werdyktu (wyżej) obowiązuje od próby #3.

## Jak powtórzyć

```bash
PYTHONPATH=. .venv/bin/python scripts/research/metalabeler.py
```
