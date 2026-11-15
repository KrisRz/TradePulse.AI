# Kandydat post-only — WYNIK (2026-11-15)

> Projekt i reguła decyzji: `docs/POSTONLY_DESIGN_2026-11-14.md`
> (SHA-256 `d885b3e8480d0837e6707afd725b2a6ccf7d56386a0a3c8b635f6e307aff934c`,
> commit `efa31a9`, przed pierwszym zleceniem). Prawdziwe zlecenia na koncie
> testowym Kraken XBT/GBP, pk `XBTGBP_exectest`. M01 uruchomione ręcznie przez usera,
> M01x–M10x przez `maker-cycles` uruchomione przez usera 2026-11-14 ~21:10 UTC,
> koniec 2026-11-15 01:15:49 UTC.

## Werdykt: **PRZYJĘTY** (4/4 kryteria)

| # | Kryterium | Próg | Wynik | |
|---|---|---|---|---|
| 1 | Wykonane jako maker | ≥ 60% | **17/20 = 85,0%** | PASS |
| 2 | Średni koszt strony | ≤ 0,65% | **0,536%** | PASS |
| 3 | Zero zgubionych / podwójnych, księga = saldo | 0 | Kraken 25 wykonanych = 25 filli w DynamoDB (te same id); 0 otwartych; saldo £9,5132 = £10 + sprzedaże − kupna − opłaty (£9,51322); księga 0 BTC | PASS |
| 4 | Żaden `post` jako taker | 0 | 17/17 wykonanych `post` z opłatą 0,40% | PASS |

Budżet straty £1,50: zużyte **£0,33** (strata konta £0,4868 − £0,1591 z testu executora).

## Liczby

| | Wynik |
|---|---|
| Koszt strony, maker (17) | 0,365–0,404% (opłata 0,40% ± pozycja wobec środka arkusza) |
| Koszt strony, po terminie → taker (3) | 1,131%, 1,160%, **1,901%** |
| Średnia: kupna / sprzedaże | 0,533% / 0,539% |
| Same opłaty / obrót | £0,2946 / £64,03 = 0,460% |
| Czas do wykonania maker | od kilkunastu sekund do ~12 min (log `paper_state/postonly_measurement.log`) |

Przesłanka z taśmy przewidywała przy 15 min: 76,7% maker i 0,535% na stronę.
Na prawdziwych zleceniach: 85,0% i 0,536%.

## Co z tego wynika — i czego nie wiemy

- **Oszczędność ~0,26 pp na stronę** wobec 0,80%. Przy ~0,6 korekty i ~1,7
  transakcji rocznie to ułamek procenta rocznie na koncie — mało w funtach, ale to
  jedyny koszt, jaki ta strategia ma.
- **Ogon jest prawdziwy:** gdy zlecenie się nie wykona, cena zwykle uciekła i strona
  kosztuje 1,1–1,9%, więcej niż market. Średnia wygrywa, pojedyncza transakcja nie musi.
- Zlecenia stały wieczorem i w nocy (21:07–01:15 UTC), w spokojnym, lekko spadającym
  rynku (~£49 000 → ~£47 600). Bot handluje o 00:10 UTC; dni z gwałtownym ruchem
  mogą mieć gorszy odsetek wykonań. N = 20, przedział niepewności szeroki.
- Okno bez stopu przy sprzedaży (≤ 15 min) w pomiarze nic nie kosztowało; zostaje
  zapisanym ryzykiem.

## Co dalej (zgodnie z projektem)

1. Reguła wchodzi do Lambdy pilota **osobnym commitem** (plan, pozycja 9): wejście,
   korekta i wyjście na sygnał przez `maker_open` / `maker_settle`, termin 15 min;
   wyjścia wymuszone zawsze market.
2. Koszt w backteście i papierze **zostaje 0,80%**, dopóki bramka C na Krakenie nie
   zmierzy kosztu na filach pilota.
3. Wariant 4h wraca jako osobny kandydat z własnym projektem (przy 0,40% przechodził
   3/4 układów „o włos”; zmierzone 0,536% to bliżej 0,40% niż 0,80%, ale to nowe
   pytanie, nie wniosek z tego pomiaru).
