# Security — TradePulse.AI

## ⚠️ Action required: rotate leaked credentials

The following secrets were previously committed to this (private) repo and must
be treated as **compromised**. Rotate them even though the repo is private.

### 1. AWS IAM access key
- Leaked key id: `AKIAYS2NQFN2UDYJX5PC` (was in `NAPRAWA.md` and
  `app/backend/scripts/analyze_closed_positions.py`, still present in git history).
- **Do:** AWS Console → IAM → Users → Security credentials → deactivate & delete
  this access key, create a new one. Store it via `aws configure` / environment
  variables / an IAM role — never in source.

### 2. Binance API key
- The live key in `app/backend/config/development.env`
  (`BINANCE_TESTNET=false`, `ENABLE_LIVE_TRADING=true`) must be revoked.
- **Do:** Binance → API Management → delete the exposed key, create a new one.
  For local development use **testnet** keys (`BINANCE_TESTNET=true`).

### 3. Backend SECRET_KEY (JWT signing)
- The default `dev-secret-key-change-in-production` was publicly known, so any
  JWT signed with it could be forged (including admin tokens).
- **Do:** generate a strong value and set `SECRET_KEY` in SSM / production env:
  ```
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- The app now **refuses to boot in production** if `SECRET_KEY` is left at an
  insecure default (see `app/backend/core/config.py::_validate_security`).

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
