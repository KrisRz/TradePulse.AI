# Jak bot trzyma `w` konta — PROJEKT POMIARU PRE-REJESTROWANY (2026-10-30)

> Dopisany **przed** pomiarem rodzin A i B niżej. Reguła wyboru jest wiążąca.

## Skąd ten dokument

R2 w `docs/KRAKEN_VENUE_RESULTS_2026-10-30.md` przeszedł na modelu, w którym konto
**codziennie wraca do 50/50**, a samo wyrównywanie **nic nie kosztuje**. Przy pisaniu
kodu wyszło, że bot w obecnej formie robi coś innego: przy wejściu inwestuje
`w × konto` i potem tego nie rusza. Po długim rajdzie udział BTC rośnie wtedy do
~0,9 i krach w tej samej pozycji uderza w prawie całe konto.

Zmierzone przed tym dokumentem (skrypt z brudnopisu, GBP, opłata 0,80%, od 2018),
jedyna liczba znana przed projektem:
- **wejście `w = 0,5` bez wyrównywania:** maxDD −40,7%, CAGR +20,0%;
- DD ≤ 25% w **75%** okien 365-dniowych i **49%** okien 730-dniowych.

**R2 nie przechodzi.** Werdykt R2 z wyników venue dotyczy więc tylko implementacji,
która wyrównuje proporcję. Koszty tego wyrównywania nie były w nim policzone.

## Rodziny do zmierzenia

Wszystkie warianty liczone tak samo:
- strategia: EMA20/100 + F7, `run_backtest` przy 0,80%, slippage 2 bps, cena GBP
  (jak w M1);
- konto startuje od **£200**, gotówka daje 0%;
- dzienna stopa części zainwestowanej = dzienna stopa krzywej strategii (opłaty
  wejścia i wyjścia proporcjonalne, w niej zawarte);
- pozycja otwarta = dni między `entry_time` a `exit_time` transakcji z silnika.

**Rodzina A — wejście bez wyrównywania, `w` ∈ {0,5; 0,4; 0,3}.** Przy wejściu
w pozycję w grę idzie `w × konto`. Najprostsza implementacja: księga dostaje
budżet, nic więcej się nie zmienia.

**Rodzina B — `w = 0,5` z pasmem wyrównywania, `b` ∈ {0,05; 0,10; 0,15}.**
- Po zamknięciu każdego dnia w pozycji: jeśli |udział BTC − 0,5| > `b`, transakcja
  przywraca 0,5.
- Opłata 0,80% od kwoty transakcji.
- Transakcję mniejszą niż **£5** pomijamy. To minimum Krakena 0,00006 BTC
  (~£3,5) z zapasem.

Raport dla każdego wariantu:
- maxDD z całej próby, CAGR;
- odsetek okien 365 i 730 dni (start co 7 dni) z DD ≤ 25% i medianę DD;
- liczbę transakcji wyrównujących na rok i ich koszt w % rocznie.

## REGUŁA WYBORU (wiążąca)

Warunki R2 bez zmian: **≥ 75% okien 730-dniowych i ≥ 90% okien 365-dniowych
z DD ≤ 25%**.

1. Jeśli przechodzi jakikolwiek wariant rodziny A, wybieram **największe `w`**,
   które przechodzi. Prostszy kod wygrywa.
2. Jeśli żaden wariant A nie przechodzi, wybieram **najszersze pasmo `b`** rodziny B,
   które przechodzi. Najmniej transakcji.
3. Jeśli nie przechodzi nic, pilot nie startuje w tej formie. Wracam do usera
   z liczbami.

Wybrany wariant zastępuje „`w = 0,5` przy wejściu” w
`docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md`. To doprecyzowanie, jak spełnić
limit, który user zatwierdził. Sam limit (25% konta) się nie zmienia.
