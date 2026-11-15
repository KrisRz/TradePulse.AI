# Kandydat: zlecenia post-only na Krakenie — PROJEKT (2026-11-14)

> Wiążący od commita. Reguła decyzji zapisana **przed** pomiarem na prawdziwych
> zleceniach. Plan 2026-11-14, pozycja 7. Nie zmienia strategii ani P1–P4.

## Po co

Test executora (2026-11-14) pokazał, że na Krakenie kosztem jest opłata: 94,5%
straty testu to taker 0,80%, poślizg niemierzalny. Zlecenie limit z flagą
`post` płaci 0,40%. Ryzyko: nie wykona się, a cena ucieknie.

## Przesłanka (zmierzona przed projektem, publiczna taśma transakcji, bez zleceń)

`scripts/research/postonly_premise.py 45` — 45 dni × 2 strony, zlecenie o 00:10 UTC
jeden krok ceny od pierwszej transakcji, wykonane dopiero gdy późniejsza transakcja
przejdzie **przez** poziom (ostrożnie), po terminie taker po ostatniej cenie:

| Termin | Wykonane jako maker | Średni koszt / stronę | Najgorszy | Zysk wobec 0,80% |
|---|---|---|---|---|
| 5 min | 63,3% | 0,562% | 1,028% | +0,238 pp |
| 15 min | 76,7% | 0,535% | 1,334% | +0,265 pp |
| 60 min | 87,8% | 0,495% | 1,646% | +0,305 pp |
| 240 min | 93,3% | 0,499% | 2,707% | +0,301 pp |

Mediana czasu do wykonania 2,5 min. Taśma jest rzadka (mediana 129 transakcji
w 4 h). Przesłanka przechodzi; to nie obietnica — taśma nie pokazuje kolejki
ani odrzuceń zleceń `post`.

## Reguła, którą mierzymy

- Wejście, korekta i wyjście **na sygnał**: limit `post` na najlepszej cenie po
  naszej stronie (kupno na bid, sprzedaż na ask), termin **15 minut**. Po terminie:
  anuluj → potwierdź → reszta zleceniem market (taker), jeśli ≥ minimum pary.
- Wyjście wymuszone (F7, kill-switch, halt): **zawsze market**. Nie czekamy.
- Przy sprzedaży stop awaryjny jest anulowany na czas oczekiwania (giełda rezerwuje
  monety pod jedno zlecenie). Okno bez stopu ≤ termin. Przyjęte dla sygnału, nie
  dla wyjść wymuszonych.
- 15 min, nie 60: prawie cały zysk (0,265 z 0,305 pp) przy 4× krótszym oknie.

## Pomiar na prawdziwych zleceniach

- **N = 20 zleceń** (10 kupna, 10 sprzedaży), każde ~£3,20, na koncie testowym
  (`XBTGBP_exectest`). Pory dowolne, nie wybierane pod rynek; godzina zapisana.
- Każde: `maker-open` → po 15 min `maker-settle`. Zapis: cena odniesienia (środek
  bid/ask przy złożeniu), wykonanie maker / taker, ceny, opłaty, czasy.
- Koszt strony = opłata / wartość + strona × (cena wykonania / cena odniesienia − 1).
- Budżet straty: £1,50 łącznie. Przekroczenie = stop i raport.

## Reguła decyzji (wiążąca)

**PRZYJĘTY**, gdy na 20 zleceniach jednocześnie:
1. wykonanych jako maker ≥ **60%**;
2. średni koszt strony ≤ **0,65%** (czyli zysk ≥ 0,15 pp wobec taker);
3. zero zleceń zgubionych albo zaksięgowanych podwójnie; księga = saldo po każdym;
4. żadne zlecenie `post` nie wykonało się jako taker (opłata każdego maker-filla = 0,40%).

Inaczej **ODRZUCONY** i zostaje market. Wynik pełny w
`docs/POSTONLY_RESULTS_<data>.md`, także gdy odrzucony.

Po przyjęciu: osobny commit wpina regułę w Lambdę pilota; koszt w backteście
i w papierze zostaje 0,80% (ostrożnie), dopóki bramka C na Krakenie nie zmierzy
kosztu na filach pilota.

## Czego nie mierzymy teraz

Wariantu 4h. Wraca jako osobny kandydat tylko po przyjęciu post-only, z własnym
projektem (przy 0,40% przechodził 3/4 układów „o włos”).
