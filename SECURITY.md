# Security — TradePulse.AI

## Rotation status (verified 2026-08-07)

The secrets below were previously committed to this (private) repo and are
treated as **compromised**. Status verified against AWS/SSM/git, not from memory.

### 1. AWS IAM access key — ✅ DONE
- Leaked key id: `AKIA…UDYJX5PC` (user `Kris`; was in `NAPRAWA.md` and
  `app/backend/scripts/analyze_closed_positions.py`, still present in git history).
- **Rotated 2026-07-16** — replacement key `…V2CYG5UJ` created the day after the
  Phase 0 cleanup. The leaked key was deactivated, last used 2025-12-27
  (`access-analyzer`, `us-west-2`), and **deleted 2026-08-07**. User `Kris` now
  holds exactly one active key.
- Note: the leaked key never belonged to a Lambda. Nothing in production uses
  static AWS keys — the four Lambdas authenticate through their IAM roles.

### 2. Binance API key — ⬜ OPEN, but far less severe than first assessed
- The live key sat in `app/backend/config/development.env` with
  `BINANCE_TESTNET=false` and `ENABLE_LIVE_TRADING=true`, and a copy remains in
  git history. That flag pair is what made this look like the worst of the three.
- **Correction (2026-08-07, from the live API Management page):** the live
  account holds exactly one key, `TradePulseAI` (HMAC), and it is **read-only** —
  `Enable Reading` is the only permission granted. Spot & Margin Trading,
  Withdrawals, Universal Transfer, Margin Loan and Prediction Trading are all
  **off**. `ENABLE_LIVE_TRADING=true` was an *application* flag, never a Binance
  permission: the app was configured to trade with a key that had no right to.
- So the real blast radius is **read access to the live account** — balances,
  positions, trade history. **No funds could ever have been moved.** A privacy
  leak, not a financial one.
- **Do:** Binance → API Management → Delete `TradePulseAI`. Hygiene, not an
  emergency. Nothing in production depends on it — the bot reads **demo**
  credentials from SSM (`/tradepulse/demo/{key,secret}`, created 2026-08-06), so
  deleting the live key cannot break the running channels.
- ⚠️ **Do not create a replacement live key yet.** Real money is gated by
  Gate B (12–18 months out), and a key created now would sit unused. See the M6
  blocker in `plan.md`: a key with trading permission requires an IP whitelist,
  which Lambda's dynamic egress addresses cannot satisfy.
- Rotating the SSM demo keys is equally safe: `shadow_handler` /
  `venue_handler` call `ssm.get_parameters` on **every invocation** with no
  caching, so a new value takes effect on the next scheduled run.

### 3. Backend SECRET_KEY (JWT signing) — ✅ NOTHING TO ROTATE
- The default `dev-secret-key-change-in-production` was publicly known, so any
  JWT signed with it could be forged (including admin tokens).
- Verified 2026-08-07: **the monolith is not deployed anywhere.** Production is
  four Lambdas (`paper-bot`, `paper-bot-status`, `shadow-bot`, `venue-4h`), none
  of which imports `app.backend.core.config`. There is no local `.env` either —
  only `.env.example`. So no live JWT was ever signed with the weak default.
- The app **refuses to boot in production** if `SECRET_KEY` is left at an
  insecure default (`app/backend/core/config.py::_validate_security`).
- **Before the monolith is ever deployed**, generate one:
  ```
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

## What was fixed in code (Phase 0)

- `app/backend/config/development.env` and `production.env` are no longer tracked
  by git; only `*.env.example` templates remain. Real files are git-ignored.
- Hard-coded AWS keys removed from `analyze_closed_positions.py` (now uses the
  boto3 default credential provider chain) and redacted in `NAPRAWA.md`.
- Frontend no longer fabricates an admin JWT for every production visitor
  (`api-client.ts` — `generateProductionAdminToken` removed).
- The `enterprise_admin_token` literal-string admin bypass is now honoured
  **only in development** (`dependencies.py`, `system_control.py`,
  `notifications.py`). In production it is rejected.
- `.gitleaks.toml` no longer blanket-allowlists `*.md` / `*test*` (that is how
  the AWS key slipped past). A CI secret scan runs on every push/PR
  (`.github/workflows/security-scan.yml`).

## Still open (tracked as follow-ups)

- **Real auth wiring**: several admin components still send the literal
  `enterprise_admin_token`; they work in dev but will 401 in production until
  wired to the real login/JWT flow. The admin dashboard also hard-codes
  `isAdmin = true` (`app/frontend/src/pages/admin/dashboard.astro`).
- **Git history scrub**: the leaked keys remain in git history. After rotating
  them this is low-risk, but history can be rewritten with `git filter-repo`
  (rewrites all commit hashes; requires a force-push and coordination).
- Enable an image vulnerability scan (Trivy) in `backend-deploy.yml` (currently
  a commented-out placeholder).
