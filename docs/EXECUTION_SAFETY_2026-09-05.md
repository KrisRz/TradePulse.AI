# Bezpieczeństwo egzekucji na kanale 4h — 2026-09-05 (audyt §10 KROK 1)

> **Co to jest:** wykonanie pierwszej pozycji z listy `docs/AUDIT_2026-09-04.md`
> §10. Zamyka 2× CRITICAL i 3× HIGH ze ścieżki pieniędzy plus MEDIUM-3/4 i E3
> z audytu E2E. **Nie zmienia księgowania** i **nie dotyka Lambd M5** — okno
> pomiarowe (dzień 51/56, ocena ≥2026-09-10) biegnie nienaruszone.

---

## 0. Werdykt w trzech zdaniach

Kanał, który 6 razy dziennie składa prawdziwe zlecenia, mógł je złożyć dwa razy
(retry POST bez identyfikatora klienta) i mógł podjąć decyzję na księdze, która
nie opisywała już konta (zlecenie szło przed zapisem `last_bar`) — i **żadna z
tych awarii nie zapaliłaby alarmu**. Obie są zamknięte: giełda sama odrzuca
duplikat, bo identyfikator zlecenia wynika z decyzji, a nie z chwili wysyłki; a
run, który zastanie na koncie nasz wykonany fill nieobecny w księdze, zatrzymuje
się głośno zamiast handlować dalej. Do tego ożył T2 kill-switcha (liczył drag
przed fillem, więc po trzech realnych fillach stał na 0,0), rekoncyliacja jest
fail-closed w obie strony, a stan w DynamoDB ma warunkowy zapis.

---

## 1. Co dokładnie było zepsute i jak jest teraz

### 🔴 CRITICAL-1 — duplikat zlecenia po nieodebranej odpowiedzi

**Było:** `_request` powtarzał **każde** żądanie po błędzie transportu i po 5xx,
łącznie z `POST /api/v3/order`, a zlecenie nie niosło `newClientOrderId`. Timeout
po tym, jak zlecenie już weszło do silnika dopasowań, oznaczał drugie zlecenie —
i podwójną pozycję. To jest klasa awarii, na którą umierają małe boty; nie
strategia.

**Jest:**

| Sytuacja | Zachowanie |
|---|---|
| POST odpowiada | to jest fill |
| timeout / 5xx | pytamy giełdę o `origClientOrderId`; jeśli zlecenie jest — jego fill jest odpowiedzią, **żadnego drugiego zlecenia** |
| timeout, a giełda mówi „nie ma takiego zlecenia" (-2013) | resend **raz**, z tym samym id |
| dwa razy bez odpowiedzi | `OrderSubmissionUncertain` — run pada, alarm, zero zgadywania |
| odrzucenie „duplikat" | pytamy giełdę; jeśli ma zlecenie o tym id, jego fill jest odpowiedzią |
| odrzucenie prawdziwe | rekord do C3 + wyjątek, jak dotąd |

Identyfikator: `tpv4h-<20 znaków sha256(symbol|strona|decyzja)>` (26 znaków,
limit Binance'a to 36). Hash, bo `2026-09-05 12:00:00+00:00` nie mieści się w
alfabecie `^[\.A-Za-z0-9_-]{1,36}$`. Deterministyczny, więc **jeden bar może
wyprodukować najwyżej jedno kupno i jedną sprzedaż — na zawsze**.

Duplikatu **nie rozpoznajemy po treści komunikatu**: `-2010` to zarówno
„Duplicate order sent", jak i „insufficient balance". Pytamy giełdę. Bot, który
by tu zgadywał, albo handlowałby dwa razy, albo połykał prawdziwą awarię.

Odzyskany fill dociąga prowizje z `GET /api/v3/myTrades` — `GET /order` ich nie
zwraca. Zweryfikowane na żywo: dla realnego filla z 18.08 `myTrades` zwraca
`0.00024844 BNB`, **co do cyfry** tyle, ile ma w księdze log fillów.

### 🔴 CRITICAL-2 — bar przehandlowany drugi raz po retry Lambdy

**Było:** zlecenie idzie w `bot.py:120`, `last_bar` zapisuje się w `:164`.
Scheduler ma `maximum_retry_attempts = 3`, a Lambda swoje domyślne 2 — retry
widział niezmieniony `last_bar` i handlował ten sam bar jeszcze raz.

**Jest — dwie niezależne warstwy:**

1. **Klucz idempotencji** (wyżej) sprawia, że powtórzony bar prosi giełdę o *to
   samo* zlecenie. Retry przestaje być groźny.
2. **Skan sierot** w `attach_venue`, przed jakąkolwiek decyzją: `allOrders` od
   znacznika; jeśli giełda trzyma NASZE wykonane zlecenie, którego księga nie
   zapisała → `BookOutOfSync`, run pada, alarm.

Sercem drugiej warstwy jest to, że **nie wymaga ona żadnej dodatkowej
księgowości**: `bot.step()` zapisuje księgę i `last_bar` jednym zapisem, już PO
fillu. Więc zlecenie, którego id jest tym, które kanał wygenerowałby dla
ostatniego zapisanego bara, jest z definicji zaksięgowane. Cokolwiek innego —
nie jest.

Dwie pułapki, które trzeba było domknąć, bo cichy błąd tutaj jest gorszy niż brak
sprawdzenia:

- **Okno skanu.** Binance na `orderId` odpowiada **najstarszymi** pasującymi
  zleceniami. Znacznik ruszający się tylko na NASZYCH fillach (≈2 razy w roku)
  zostawiłby okno rosnące o 2 zlecenia heartbeatu dziennie, aż przekroczyłoby
  stronę zwracaną przez giełdę — i sprawdzenie raportowałoby „czysto", bo
  przestałoby widzieć. Znacznik jedzie więc do przodu w **każdym** czystym runie.
- **Zasiew.** Pierwszy run nie ma znacznika. Gdyby zasiew brał po prostu
  najnowsze id, run, który złożył zlecenie i padł przed zapisem, zostałby
  zaadoptowany po cichu. Zasiew więc też skanuje: przed tą zmianą **żadne**
  zlecenie na koncie nie miało naszego prefiksu (potwierdzone na żywo — id
  Binance'a w rodzaju `xWWcKwu9oaEa3C80TNuVKb`), więc nasze zlecenie w stronie
  zasiewu może być wyłącznie sierotą.

### 🟠 HIGH-1 — T2 kill-switcha nie mógł zadziałać

`drag` był liczony **przed** `bot.step()` i ta sama wartość szła do `observe()`.
Fill z tego runu nigdy do niej nie wchodził, więc `execution_drag` stał na 0,0 w
DynamoDB po trzech realnych fillach. Teraz `observe()` dostaje wartość
przeliczoną **po** kroku. `evaluate()` dalej patrzy na stan sprzed bara — to jest
poprawne, bezpiecznik ocenia dowody, które już były.

### 🟠 HIGH-2 — rekoncyliacja tylko logowała, i tylko w jedną stronę

Teraz obie strony są fail-closed:

- **baza:** księga trzyma więcej BTC niż konto ma wolnego → wyjątek (noga wyjścia
  nie mogłaby się wypełnić nawet w zasadzie);
- **quote:** księga twierdzi, że ma USDT, których konto nie ma → wyjątek. Dziś
  bezczynne, bo `cash = −1,81` (to jest HIGH-4, księga v2), i **nośne w chwili,
  gdy sizing zacznie brać z `book.cash`**.

### 🟠 HIGH-3 — wspólny sekret i zaszyty adres giełdy

`VENUE_CREDENTIALS_PATH` i `BINANCE_BASE_URL` z env (dziś obie wskazują na te
same wartości demo; przełączenie kanału na własny klucz to zmiana zmiennej, nie
kodu). Nazwy kluczy bez „DEMO": `BINANCE_API_KEY` / `BINANCE_API_SECRET`, stary
zapis nadal akceptowany, żeby przemianowanie zmiennej nie mogło unieruchomić
wdrożonej funkcji. Polityka IAM venue obejmuje oba prefiksy — po utworzeniu
własnych parametrów skasować z listy prefiks shadow.

### 🟡 MEDIUM-3 — dwóch piszących do jednej księgi

`reserved_concurrent_executions = 1` na obu funkcjach **oraz** warunkowy zapis
stanu: element w DynamoDB niesie `state_version`, a zapis musi trafić w wersję,
którą ten proces odczytał. Przegrany dostaje `ConcurrentStateWrite` zamiast po
cichu nadpisać cudzy fill. Współbieżność 1 to ustawienie AWS; księgowość nie może
zależeć od ustawienia.

### 🟡 MEDIUM-4 — halt gubiony w locie

Halt zapisuje się **przed** zleceniem flatten. Klucz flattenu to `halt@<ostatni
bar>`, nie zegar — powtórzony halt pyta giełdę o to samo zlecenie zamiast
sprzedawać drugi raz.

### ℹ️ E3 — dwie warstwy retry

Jawny `aws_lambda_function_event_invoke_config` z `maximum_retry_attempts = 0` na
obu funkcjach. Retry należy do schedulera (3 próby + DLQ) — jedna polityka, w
jednym miejscu, widoczna w planie.

### Heartbeat (shadow)

Nogi rundy dostały deterministyczne nazwy: run z harmonogramu używa nazw dnia,
więc retry po zgubionej odpowiedzi pyta o **to samo** zlecenie. Noga odzyskania
ma własną nazwę, bo to inne zlecenie tego samego dnia i tej samej strony. Run
wymuszony (`{"force": true}`, sprawdzenie deployu) dostaje nazwy z zegarem — ma
naprawdę handlować, a nie rozwiązać się po cichu do porannych fillów i zaraportować
sukces, którego nie było.

---

## 2. Testy, które łapią awarię

30 nowych przypadków w `app/backend/tests/test_execution_safety.py`, każdy pisany
tak, żeby **padać na kodzie sprzed naprawy**. Sprawdzone mutacją — kod cofnięty
do stanu z 2026-09-04, test uruchomiony:

| Mutacja | Wynik |
|---|---|
| `drag` liczony przed `bot.step()` | 🔴 ZŁAPANE |
| ślepy retry `POST /order` po 5xx | 🔴 ZŁAPANE |
| usunięty `newClientOrderId` | 🔴 ZŁAPANE |
| ostrzeżenie zamiast zatrzymania w rekoncyliacji | 🔴 ZŁAPANE |
| usunięty skan sierot | 🔴 ZŁAPANE |

Cały pakiet: **444 testy zielone**, w tym złoty wzorzec księgi
(`test_portfolio_golden.py`, `test_portfolio_quantity.py`) — arytmetyka księgi
nie drgnęła, bo klucz zlecenia jest przekazywany przez `reconcile` i ignorowany
przez ścieżkę modelowaną.

---

## 3. Weryfikacja na żywo przed deployem (tylko odczyt, zero zleceń)

| Sprawdzenie | Wynik |
|---|---|
| `allOrders(limit=5)` — ścieżka zasiewu | 5 zleceń, wszystkie heartbeatu, `ours=0` |
| `allOrders(orderId>=…)` — ścieżka skanu | działa, potwierdza kolejność rosnącą |
| `lookup_order(nieistniejące id)` | `None` (Binance odpowiada -2013, obsłużone) |
| `myTrades(57633837013)` | `0.00024844 BNB` = dokładnie tyle, co w logu fillów |
| dry-run `attach_venue` na realnej księdze i koncie | obie strony przechodzą; pozycja 0,00309 odtworzona; znacznik zasiany na 62079703526 |

Stan konta w chwili sprawdzenia: 0,05309 BTC i 4798,23 USDT wolnego — zgodny z
księgą (0,00309 bota + 0,05 bazowe).

---

## 4. Deploy

`terraform plan` na `infra-serverless/`: **2 do dodania, 2 do zmiany, 0 do
usunięcia** — wyłącznie `venue_4h` i `shadow_bot` plus ich `event_invoke_config`.
**Żadnego zasobu M5 w planie.** `dist/paper_bot_lambda.zip` nietknięty
(bajt w bajt z 2026-08-05), więc `source_code_hash` M5 nie może się ruszyć.

Po `apply` do sprawdzenia:

```bash
# 1. sha M5 musi być dalej r8Luxno…tNq0=
for f in tradepulse-paper-bot tradepulse-paper-bot-status; do
  aws lambda get-function-configuration --function-name $f --region eu-west-2 \
    --query CodeSha256 --output text
done

# 2. heartbeat na nowym kodzie, wymuszony (ma naprawdę handlować)
aws lambda invoke --function-name tradepulse-shadow-bot --region eu-west-2 \
  --cli-binary-format raw-in-base64-out --payload '{"force":true}' /tmp/o.json

# 3. kill-switch czysty
PAPER_STATE_BACKEND=dynamodb AWS_DEFAULT_REGION=eu-west-2 \
  .venv/bin/python -m app.backend.paper_trading.run killswitch --timeframe 4h --capital 200
```

Pierwszy run `venue-4h` po deployu zasieje znacznik zleceń i zapisze go razem z
księgą. Od następnego filla `execution_drag` zacznie akumulować — dziś stoi na
0,0 i to jest właśnie objaw, który naprawiamy.

---

## 5. Czego ta sesja świadomie NIE ruszyła

- **HIGH-4 sizing z konta zamiast z księgi** (stąd `cash = −1,81`), prowizja BNB
  poza equity, resztka qty — to jest **księga v2**, wymaga decyzji usera i
  dyscypliny złotego wzorca. Rekomendacja audytu: razem z tym krokiem albo zaraz
  po; wybrana opcja: **zaraz po**, żeby nie mieszać bezpieczeństwa z księgowaniem
  w jednym diffie w trakcie zbierania bramki C.
- **Wszystko w `gate.py`** — ocena 2026-09-10 idzie kodem JAK JEST
  (pre-rejestracja). Poprawki DSR i walk-forward to KROK 2, po ocenie.
- **Cokolwiek na Lambdach M5.**

---

## 6. Źródła

- `docs/AUDIT_2026-09-04.md` §2 (CRITICAL-1/2, HIGH-1..4), §10 KROK 1
- `docs/ANALIZA_E2E_2026-09-04.md` E3 (dwie warstwy retry)
- Binance API: `POST /api/v3/order` (`newClientOrderId`), `GET /api/v3/order`
  (`origClientOrderId`, -2013), `GET /api/v3/myTrades`, `GET /api/v3/allOrders`
  (`orderId` = od najstarszych)
