# Warsztat scenariuszy — pierwszy przebieg (2026-08-06)

> Cztery kandydaci przez jeden młynek: walk-forward × 4 layouty × 4 poziomy
> prowizji, holdout <2026-07-16 wyegzekwowany w kodzie, reguła decyzyjna
> **pre-rejestrowana przed uruchomieniem**, 64 próby policzone i obciążone karą.
>
> Narzędzie: `scripts/research/scenario_lab.py`. **Nic tu nie dotyka biegnącego
> bota BTC 1d** — przyjęcie kandydata otwiera NOWE okno papierowe, nigdy nie
> modyfikuje mierzonego.

## Reguła (spisana zanim padła pierwsza liczba)

Kandydat wchodzi tylko jeśli **wszystkie cztery** są spełnione:

1. OOS Sharpe ≥ 0,8 przy prowizji 0,2% w ≥3 z 4 layoutów
2. bije buy & hold na Sharpe w ≥3 z 4 layoutów
3. ≥20 zamkniętych trejdów na całym OOS (inaczej pomiar bez mocy)
4. Deflated Sharpe ≥ 0,95 po obciążeniu za liczbę prób

Trzy z czterech to odrzucenie, nie dyskusja.

## Wyniki

| Kandydat | Werdykt | Co go rozstrzygnęło |
|---|---|---|
| `btc_1d_live` *(kontrolka)* | **ACCEPT** | 4/4 — odtwarza audyt kalibracji (Sharpe 1,00–1,14) |
| **`btc_4h`** | **ACCEPT** | 4/4 — ale patrz „kruchość" niżej |
| `eth_1d` | REJECT | nie bije B&H (przegrywa w 3 z 4 layoutów) |
| `btc_1d_short` | REJECT | Sharpe 0,63–0,87 i nigdy nie bije B&H |

### 🔴 Noga SHORT: intuicja była błędna

Hipoteza brzmiała: „bot stał flat, gdy BTC spadał 12,73% — noga short by to
zmonetyzowała". **Dane mówią nie.**

| layout @0,2% | long-only | z shortem | B&H |
|---|---|---|---|
| (730, 180) | **1,00** | 0,71 | 0,87 |
| (500, 125) | **0,99** | 0,63 | 0,97 |
| (1000, 250) | **1,13** | 0,87 | 1,00 |
| (365, 90) | **1,01** | 0,74 | 0,81 |

Short pogarsza wynik w **każdym** layoucie, a drawdown rośnie z −49% do −59…−67%.
I to jest ocena **łagodna**: model ułamkowy zaniża koszt shorta (patrz
`docs/QUANTITY_BOOK_2026-08-06.md` §2), więc prawdziwe liczby są jeszcze gorsze.

Wniosek: **na BTC nie shortujemy.** Trend-following po krótkiej stronie na
aktywie z długoterminowym dryfem w górę oddaje więcej, niż zbiera. Sprawa
zamknięta danymi, nie opinią — i dlatego było warto policzyć, zamiast dyskutować.

### 🟢 BTC 4h: przyjęty, ale kruchy

| layout | fee 0,1% | fee 0,2% | fee 0,3% | fee 0,5% | B&H | trejdy |
|---|---|---|---|---|---|---|
| (730, 180) | 0,99 | 0,91 | 0,82 | 0,65 | 0,86 | 129 |
| (500, 125) | 1,06 | 0,96 | 0,86 | 0,65 | 0,92 | 155 |
| (1000, 250) | 0,89 | 0,81 | 0,73 | 0,57 | 0,75 | 118 |
| (365, 90) | 1,05 | 0,92 | 0,80 | 0,55 | 0,93 | 187 |

**Przechodzi regułę**, ale trzeba widzieć, gdzie stoi:

- przy **0,1%** (tyle bierze giełda) bije B&H w 4/4 layoutach
- przy **0,2%** bije w 3/4 — (365, 90) przegrywa o 0,01
- przy **0,3%** przegrywa z B&H w **4/4** — edge znika
- drawdown gorszy niż 1d: −53…−69% wobec −49%

Czyli **przewidywany haczyk się potwierdził**: 7× częstotliwość to 7× fee drag,
a margines to jeden krok prowizji. Rabat BNB był wyłączony 2026-08-06, więc
realna prowizja to 0,1% — mieścimy się, ale bez zapasu.

**Dlaczego to i tak jest duża sprawa:** 4h robi ~130–190 trejdów na tym samym
oknie, na którym 1d robi 13–31. To jest **7,2× szybszy dowód** — werdykt o
rentowności w miesiącach zamiast w 12–18 miesiącach.

### ETH 1d: przyzwoity, ale nie lepszy od trzymania

Sharpe 0,82–1,03 wygląda dobrze, dopóki nie postawi się obok B&H ETH, który
robi 0,75–1,00 przy zwrotach 2× wyższych. Strategia redukuje drawdown (−62%
wobec −64% B&H), ale nie zarabia więcej. Reguła mówi: nie.

## O liczeniu prób — co ta kara faktycznie zrobiła

64 próby, najlepszy zaobserwowany Sharpe 1,14, oczekiwany najlepszy **czystym
trafem 0,36**. Wszystkie cztery kandydatury przechodzą DSR z wynikiem 1,000.

Uczciwa interpretacja: **DSR mówi „to nie są artefakty przeszukiwania" — i to
jest prawda przy 3240 obserwacjach.** Ale to nie DSR odsiał kandydatów. Odsiało
ich **porównanie z buy & hold** i **siatka prowizji**. Warto to widzieć, bo
przy następnym przebiegu z większą liczbą kandydatów DSR zacznie mieć znaczenie,
a dziś jeszcze go nie ma.

⚠️ Zastrzeżenie zapisane też w samym raporcie: 16 komórek jednego kandydata to
próby **silnie skorelowane**, nie niezależne losowania. Poprzeczka jest przez to
miększa, niż sugeruje liczba 64. To poręcz, nie wyrocznia.

## Co z tego wynika

1. **BTC 4h → nowe okno papierowe.** Zgodnie z regułą: osobny kanał, osobna
   księga, **zero zmian w biegnącym BTC 1d**. To jest jedyna droga do werdyktu
   o rentowności szybciej niż w 2027.
2. **Short skreślony.** Nie wracamy do tematu bez nowej hipotezy — nie samego
   „a może jednak".
3. **ETH odłożony.** Nie odrzucony na zawsze; odrzucony przy tej strategii.
4. **Prowizja jest teraz zmienną krytyczną.** Przy 1d fee drag był strukturalnie
   mały (20 trejdów przez 6,5 roku). Przy 4h jeden krok prowizji zabija edge —
   więc maker orders (F7 z roadmapy) przestają być kosmetyką.

## Jak powtórzyć

```bash
python scripts/research/scenario_lab.py --list
python scripts/research/scenario_lab.py --only btc_4h
python scripts/research/scenario_lab.py --json out.json
```

Dodanie kandydata to jeden wpis w `CANDIDATES`. **Reguły decyzyjnej nie wolno
edytować po zobaczeniu wyników** — jeśli okaże się zła, zmienia się ją osobnym
commitem, z uzasadnieniem, i przelicza wszystko od zera.
