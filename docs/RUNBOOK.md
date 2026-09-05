# RUNBOOK — co robić, gdy coś pójdzie nie tak

> **Dla kogo:** dla siebie za pół roku, o trzeciej w nocy, po e-mailu z alarmem.
> Każda sekcja to: **objaw → co to znaczy → co zrobić**, z komendami do wklejenia.
>
> **Zasada nadrzędna:** nic w tym systemie nie wymaga natychmiastowej reakcji
> *poza* jednym przypadkiem — pozycja otwarta na giełdzie, której bot nie potrafi
> zamknąć. Wszystko inne może poczekać do rana. Pośpiech przy pieniądzach psuje
> więcej, niż naprawia.

---

## 0. Pierwsze 60 sekund — jeden przebieg diagnostyczny

```bash
cd /Applications/TradePuls

# 1. Czy Lambdy żyją i czy zamrożenie M5 trzyma
for f in tradepulse-paper-bot tradepulse-paper-bot-status \
         tradepulse-shadow-bot tradepulse-venue-4h; do
  printf "%-32s " $f
  aws lambda get-function-configuration --function-name $f --region eu-west-2 \
    --query '[State,CodeSha256]' --output text
done
# Obie Lambdy M5 MUSZĄ mieć r8LuxnoJgluluwOEuPP6tk5nRDrhpjNq4emap/stNq0=

# 2. Które alarmy są zapalone
aws cloudwatch describe-alarms --region eu-west-2 --state-value ALARM \
  --query 'MetricAlarms[].[AlarmName,StateReason]' --output text

# 3. Co bot myśli, że ma
curl -s https://tradepulseai.co.uk/api/state | python3 -m json.tool | head -40

# 4. Co bot NAPRAWDĘ ma (u źródła, nie z księgi)
PAPER_STATE_BACKEND=dynamodb AWS_DEFAULT_REGION=eu-west-2 \
  .venv/bin/python -m app.backend.paper_trading.run killswitch --timeframe 4h --capital 200
```

Punkt 4 jest ważniejszy, niż wygląda: **księga i konto to dwie różne rzeczy** i
połowa poniższych scenariuszy to właśnie ich rozjazd.

---

## 1. 🔴 „KILL SWITCH" — bramka bezpieczeństwa zadziałała

**Objaw:** alarm `tradepulse-venue-4h-killswitch`, albo e-mail z dead-man switcha
o niepowodzeniu, albo `"halted": true` w `/api/state`.

**Co to znaczy:** jeden z trzech progów pękł — T1 obsunięcie >25% od szczytu, T2
rozjazd egzekucji >10% kapitału startowego, T3 strata >15% w jednym barze — albo
ocena bezpiecznika sama rzuciła wyjątkiem (`T0_EVALUATION_FAILED`, fail-closed).
Kanał **przestał handlować** i **spłaszczył pozycję**. To jest zachowanie
zamierzone, nie awaria.

**Co zrobić — bez pośpiechu:**

```bash
# 1. Dlaczego
PAPER_STATE_BACKEND=dynamodb AWS_DEFAULT_REGION=eu-west-2 \
  .venv/bin/python -m app.backend.paper_trading.run killswitch --timeframe 4h --capital 200

# 2. Czy pozycja NAPRAWDĘ jest zamknięta (nie wierz księdze)
#    -> saldo BTC powinno wrócić do bazowego 0.05
```

3. **Zrozum przyczynę, zanim wrócisz.** T2 oznacza zepsutą hydraulikę (fille lądują
   daleko od modelu) — to bug albo zmiana po stronie giełdy, nie pech. T1/T3
   oznaczają, że rynek zrobił coś poza kopertą, na którą projektowaliśmy.
4. **Re-arm jest świadomą decyzją człowieka.** Nie ma auto-rearmu i nie ma timera —
   celowo:

```bash
PAPER_STATE_BACKEND=dynamodb AWS_DEFAULT_REGION=eu-west-2 \
  .venv/bin/python -m app.backend.paper_trading.run rearm --timeframe 4h --capital 200 \
    --confirm --note "powód, dla którego to jest bezpieczne — trafia do audytu"
```

Szczyt equity resetuje się do bieżącego, inaczej T1 odpaliłby natychmiast znowu.

---

## 2. 🔴 `BookOutOfSync` — księga jest za kontem

**Objaw:** alarm `-errors`, w logach `the venue holds N executed order(s) this book
never recorded` albo `book holds X BTC but the account only has Y free`.

**Co to znaczy:** **to jest ten jeden przypadek, który wymaga uwagi.** Bot zastał na
giełdzie swój wykonany fill, którego nie ma w księdze (albo księga twierdzi, że ma
więcej, niż konto naprawdę trzyma). Odmówił podjęcia decyzji — celowo, bo następne
zlecenie byłoby liczone na fikcji. Kanał **stoi** i **nie handluje**, dopóki tego nie
rozstrzygniesz.

**Co zrobić:**

1. Znajdź w logu id zlecenia i clientOrderId, które bot uznał za niezaksięgowane.
2. Zapytaj giełdę, co się naprawdę stało — to jest źródło prawdy:

```bash
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "/Applications/TradePuls")
import boto3
from app.backend.paper_trading.binance_demo import BinanceDemoExecutor
from app.backend.paper_trading.venue_handler import CLIENT_PREFIX
v = {p["Name"]: p["Value"] for p in boto3.client("ssm", region_name="eu-west-2")
     .get_parameters(Names=["/tradepulse/demo/key", "/tradepulse/demo/secret"],
                     WithDecryption=True)["Parameters"]}
ex = BinanceDemoExecutor(api_key=v["/tradepulse/demo/key"],
                         api_secret=v["/tradepulse/demo/secret"],
                         symbol="BTCUSDT", client_prefix=CLIENT_PREFIX)
ex.sync_time()
print("saldo:", ex.balances())
for o in ex.orders_since(limit=10):
    print(o["orderId"], o["side"], o["status"], o["executedQty"],
          o.get("clientOrderId"), "NASZE" if ex.is_ours(o.get("clientOrderId")) else "")
PY
```

3. **Ustal, która strona ma rację**, i dopiero wtedy działaj:
   - **Fill jest prawdziwy, księga go nie ma** → księgę trzeba doprowadzić do stanu
     konta. Nie ma na to automatu i celowo nie będzie: to operacja księgowa,
     wykonywana raz, ręcznie, z zapisem w `docs/`. Do tego czasu kanał stoi — i
     dobrze, bo stoi bezpiecznie.
   - **Zlecenie nie jest nasze** (inny bot na tym samym koncie) → sprawdź prefiks
     `clientOrderId`. `tpv4h-` = kanał 4h, `tpsh-` = heartbeat. Cudze zlecenie nie
     powinno tu wpaść; jeśli wpadło, to jest bug w `is_ours`.
4. Nie „odblokowuj" kanału przez skasowanie stanu. To zamienia problem widoczny
   w problem niewidoczny.

---

## 3. 🟠 `OrderSubmissionUncertain` — nie wiadomo, czy zlecenie weszło

**Objaw:** alarm `-errors`, w logach `could not be confirmed: ... reconcile against
the account before trading again`.

**Co to znaczy:** POST zlecenia dwa razy z rzędu nie dostał odpowiedzi, a giełda
zapytana o `origClientOrderId` powiedziała, że takiego zlecenia nie ma. Bot
**odmówił zgadywania**. Pozycja może być otwarta albo nie.

**Co zrobić:** dokładnie procedura z §2 punkt 2 — zapytaj giełdę o saldo i ostatnie
zlecenia. Zwykle okazuje się, że zlecenia naprawdę nie ma i następne wywołanie z
harmonogramu (co 4h) po prostu je złoży, z tym samym `clientOrderId`. **Nie składaj
zlecenia ręcznie** — złamałbyś idempotencję, na której stoi cała ochrona przed
duplikatem.

---

## 4. 🟠 `ConcurrentStateWrite` — dwóch piszących do księgi

**Objaw:** `... was written by another run since this one read it`.

**Co to znaczy:** ktoś (najpewniej Ty, z CLI z `PAPER_STATE_BACKEND=dynamodb`)
zapisał stan w tym samym czasie co Lambda. Zapis warunkowy odrzucił ten drugi
zamiast po cichu nadpisać. **Nic nie zostało utracone** — to jest sukces mechanizmu,
nie awaria.

**Co zrobić:** nic. Następne wywołanie z harmonogramu przeczyta świeży stan.
Unikaj uruchamiania `run step` na produkcyjnym stanie równolegle z harmonogramem.

---

## 5. 🟠 Bot nie handluje / brak wywołań

**Objaw:** alarm `-no-invocation`, albo cisza z dead-man switcha (patrz §8).

**Diagnoza:**

```bash
aws scheduler list-schedules --region eu-west-2 --query 'Schedules[].[Name,State]' --output text
aws logs tail /aws/lambda/tradepulse-venue-4h --since 6h --region eu-west-2
```

**Najczęstsze przyczyny:** harmonogram `DISABLED` (ktoś go wyłączył), Lambda
przekracza limit czasu, wyczerpana zarezerwowana współbieżność (jest 1 — jeśli
poprzednie wywołanie wisi, następne dostaje throttle).

**Ryzyko:** jeśli w tym czasie jest otwarta pozycja, **nikt nie ocenia wyjścia**.
To jest dokładnie ten scenariusz, dla którego alarm `no-invocation` istnieje.

---

## 6. 🟠 Pozycja w księdze ≠ pozycja na giełdzie

**Objaw:** liczby w `/api/state` nie zgadzają się z saldem konta.

**Uwaga na fałszywy alarm:** konto demo jest **wstępnie zasilone 0,05 BTC**, których
bot nigdy nie kupił. Poprawne równanie to
`saldo konta = 0,05 bazowe + qty bota`, **nie** `saldo = qty bota`.

Od 2026-09-05 prawdziwy rozjazd zatrzymuje run sam z siebie (§2) — jeśli więc bot
handluje normalnie, a liczby wyglądają dziwnie, najpierw sprawdź, czy nie porównujesz
equity mark-to-market z zaksięgowanym (`realized`).

---

## 7. 🔴 Klucz API wyciekł

1. **Skasuj klucz w panelu Binance.** Najpierw to, potem wszystko inne.
2. Wygeneruj nowy i wgraj do SSM (nigdy do repo, nigdy do Terraforma):

```bash
aws ssm put-parameter --name /tradepulse/demo/key    --type SecureString --overwrite --value '...'
aws ssm put-parameter --name /tradepulse/demo/secret --type SecureString --overwrite --value '...'
```

3. Lambdy czytają SSM przy każdym wywołaniu — **redeploy nie jest potrzebny**.
4. Sprawdź, czy klucz nie wszedł do gita: `gitleaks detect --no-banner`.
   Jeśli wszedł, **przepisz gałąź** — CI skanuje cały zakres PR-a, więc zredagowanie
   go późniejszym commitem niczego nie czyści.

---

## 8. 🟡 Dead-man switch zapiszczał (cisza z bota)

**Objaw:** e-mail z healthchecks.io, że nie było pingu.

**Co to znaczy:** bot nie **dokończył** żadnego runu w oknie. Ping idzie dopiero po
zapisaniu księgi, logu decyzji i stanu bezpiecznika, więc brak pingu przy działającej
Lambdzie oznacza, że runy **padają**, a nie że są pomijane.

Jest to jedyny sygnał, który przetrwa zniknięcie konta albo regionu AWS — wszystkie
pozostałe alarmy siedzą w tym samym koncie, którego dotyczą. Jeśli przyszedł ten
e-mail, a konsola AWS jest niedostępna, **to jest ta awaria, dla której go
zakładaliśmy**.

**Uwaga:** bot 1d (kanał M5) **nie ma** własnego pingu, bo jest zamrożony do M6.
Jest pokryty pośrednio — siedzi w tym samym koncie i regionie co pozostałe dwa.

---

## 9. 🟡 Wiadomość w DLQ

**Objaw:** alarm `-dlq`.

**Co to znaczy:** scheduler wyczerpał 3 próby i odłożył zdarzenie. Wywołanie
**nie** doszło do skutku — bar mógł zostać pominięty.

```bash
aws sqs receive-message --region eu-west-2 \
  --queue-url $(aws sqs get-queue-url --queue-name tradepulse-venue-4h-dlq \
                 --region eu-west-2 --output text)
```

Po naprawie przyczyny bot **sam nadrobi**: pominięty bar zostanie przetworzony przy
następnym wywołaniu, a log decyzji leczy lukę (`_heal_decision_log`). Nie odtwarzaj
zdarzeń z DLQ ręcznie — ryzykujesz przehandlowanie starego bara.

---

## 10. 🟡 Giełda leży w chwili sygnału

**Co robi bot:** ponawia bezpieczne żądania (5xx, 429, rozjazd zegara), ale
**nigdy nie ponawia ślepo zlecenia**. Jeśli się nie uda — run pada, alarm dzwoni,
a następne wywołanie z harmonogramu spróbuje z tym samym `clientOrderId`.

**Co robić:** nic. Sprawdź `https://www.binance.com/en/support/announcement` i
poczekaj. Ręczne handlowanie „za bota" psuje pomiar M5 i księgę.

---

## 11. 🟢 Strona nie działa

Strona jest **czysto prezentacyjna** — jej awaria nie dotyka bota w żaden sposób.

```bash
curl -sI https://tradepulseai.co.uk | head -3
curl -s  https://tradepulseai.co.uk/api/state | head -c 200
./scripts/deploy_site.sh      # Z KORZENIA REPO, nie z web/
```

`infra-site/` to **osobny root Terraforma** — `apply` tam fizycznie nie może
dotknąć Lambd M5.

---

## 12. Czego NIGDY nie robić

- **Nie handluj ręcznie na koncie bota.** Księga tego nie zobaczy, a od 2026-09-05
  zatrzyma kanał jako rozjazd (§2). Jeśli musisz — zapisz to i uzgodnij księgę.
- **Nie redeployuj Lambd M5** przed końcem okna pomiarowego. Chroni je
  `ignore_changes` w `main.tf`; przy M6 trzeba go **świadomie** usunąć, inaczej
  deploy po cichu nic nie zrobi.
- **Nie zmieniaj `gate.py`** przed oceną. Progi są pre-rejestrowane; zaostrzenie
  wolno zapowiedzieć przed danymi (`docs/GATE_B_PREREGISTRATION_2026-09-05.md`),
  poluzowanie nigdy.
- **Nie kasuj stanu w DynamoDB**, żeby „odblokować" bota. Stan JEST księgą.
- **Nie ufaj księdze przy rozjeździe.** Giełda jest źródłem prawdy dla tego, co
  posiadasz; księga jest źródłem prawdy dla tego, co zamierzaliśmy.

---

## 13. Gdzie co jest

| Co | Gdzie |
|---|---|
| Stan, log decyzji, fille, odrzucenia | DynamoDB `tradepulse_paper_bot` (`pk` = `BTCUSDT_1d` / `BTCUSDT_4h` / `SHADOW_BTCUSDT_1d`) |
| Klucze | SSM `/tradepulse/demo/{key,secret}` (SecureString) |
| Ping dead-man | SSM `/tradepulse/healthcheck/{venue-4h,shadow}` (opcjonalne) |
| Logi | CloudWatch `/aws/lambda/tradepulse-*`, retencja 30 dni |
| Infra bota | `infra-serverless/` (zamrożone M5) |
| Infra strony | `infra-site/` (osobny root) |
| Plan i status | `plan.md` → sekcja `⏯ WZNOWIENIE` |
| Archiwum | `~/TradePulse_safety/` — **nie kasować** |
