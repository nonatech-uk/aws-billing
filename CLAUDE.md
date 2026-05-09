# CLAUDE.md — project state & handoff

*Read this first. It captures current state for session continuity. Pattern was modelled on `../finance/CLAUDE.md` — read that file too if you're new to the deployment idioms (`mees-shared-py`, Containerfile multi-stage build, Traefik routing, `/zfs/Apps/AppData/...` secrets layout).*

---

## What this is

Internal website at **`https://aws.mees.st`** showing monthly AWS Cost Explorer figures
per account in the Nonatech AWS organisation, plus Tony Shakesby's separately-invoiced
account. Replaces the need to log in to AWS (or to run
`aws-account-maintenance/scripts/billing-report.js` and regenerate static HTML).

Auth via Keycloak OIDC at `kc.mees.st` (no Authelia in front — Keycloak is handled
in-app via Authlib + signed session cookie).

---

## Quick start (local dev)

```bash
cd /Users/stu/Code/aws-billing

# Backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example config/.env       # edit DATABASE_URL + (set AUTH_ENABLED=false for dev)
uvicorn src.api.app:app --reload --port 8000

# UI (separate terminal)
cd ui && npm install && npm run dev   # :5173, proxies /api -> :8000
```

`AUTH_ENABLED=false` bypasses Keycloak and pretends to be `dev@local`
(`DEV_USER_IS_ADMIN=true` so admin-only routes work).

---

## Stack

- **Backend:** Python 3.12, FastAPI, asyncpg, Authlib (Keycloak OIDC), boto3, uvicorn
- **Frontend:** React 19 + Vite 7 + TypeScript + Tailwind v4 + TanStack Query + Recharts
- **DB:** PostgreSQL on `192.168.128.9:5432`, database `aws_billing`
- **Container:** Multi-stage `Containerfile` (Node 22 builds UI → Python 3.12-slim serves API + static)
- **Deploy:** Podman on the NAS, secrets in `/zfs/Apps/AppData/aws-billing/`, Traefik route `aws.mees.st`, systemd timer for daily sync at **04:00** (finance runs 03:00; offset to avoid overlap)

Deliberately **no `mees-shared-py` / `mees-shared-ui` deps** for now — this app stands alone.
If you later want dashboard registration or shared UI components, follow finance's pattern of
copying the peer dirs into the build context (see `finance/build.sh` and `finance/Containerfile`).

---

## Repo layout

```
aws-billing/
├── config/
│   ├── settings.py         # Pydantic settings, reads config/.env
│   ├── accounts.yaml       # Account map: id → slug, name, billing (org|separate), budget
│   └── .env                # gitignored — DB DSN, Keycloak secret, session secret
├── src/
│   ├── api/
│   │   ├── app.py          # FastAPI app, lifespan, SPA static-serve
│   │   ├── auth.py         # Authlib Keycloak OIDC; signed itsdangerous cookie
│   │   ├── deps.py         # re-exports get_current_user, require_admin, get_pool
│   │   ├── models.py       # Pydantic responses
│   │   └── routers/        # accounts, summary, trends, sync
│   ├── ingestion/
│   │   ├── cost_explorer.py  # boto3 CE client (org profile + per-account profile)
│   │   └── sync.py           # upsert monthly_cost + service_cost
│   └── db/
│       ├── pool.py         # asyncpg pool + init_pool/close_pool
│       ├── schema.sql      # idempotent CREATE TABLE IF NOT EXISTS
│       └── queries.py      # read queries (kept thin)
├── scripts/
│   ├── entrypoint.sh       # exec uvicorn (foreground) — runs in container
│   ├── daily_sync.py       # systemd timer entrypoint: refresh current + previous month
│   └── backfill.py         # one-shot N-month backfill
├── ui/                     # React app — Summary, AccountDetail, Settings pages
├── deploy/
│   ├── run.sh              # podman build + run, mounts secrets
│   ├── aws-billing-sync.service
│   └── aws-billing-sync.timer  # OnCalendar=*-*-* 04:00:00
├── Containerfile           # Node ui-build → python:3.12-slim
├── build.sh                # local podman build
└── requirements.txt
```

---

## AWS authentication — IMPORTANT

Two profiles are needed because **Tony Shakesby is invoiced separately**, not on the
consolidated bill:

| Profile | Account | Purpose |
|---|---|---|
| `org` | `975363675991` (NonaTech mgmt) | `GetCostAndUsage` grouped by `LINKED_ACCOUNT × SERVICE` returns rows for all 9 consolidated accounts in one call |
| `tony` | `519904985655` (Tony Shakesby) | `GetCostAndUsage` grouped by `SERVICE` only, returns Tony's own bill |

Each profile is an IAM user with this policy:
```json
{ "Version": "2012-10-17", "Statement": [{
  "Effect": "Allow",
  "Action": ["ce:GetCostAndUsage", "ce:GetCostForecast"],
  "Resource": "*"
}]}
```

Credentials live at `/zfs/Apps/AppData/aws-billing/aws-credentials`
(standard `~/.aws/credentials` format with `[org]` + `[tony]` sections),
mounted **read-only** into the container at `/root/.aws/credentials`. **No keys in git, no keys in env.**

---

## Keycloak setup (one-time, manual)

In Keycloak admin at `https://kc.mees.st`:

1. Create client **`aws-billing`**
   - Client type: **Confidential**
   - Standard flow enabled
   - Valid redirect URIs: `https://aws.mees.st/auth/callback`
   - Valid post-logout redirect URIs: `https://aws.mees.st/`
   - Web origins: `https://aws.mees.st`
2. Add a **Group Membership** mapper on the client → token claim name `groups`, full-path off.
3. Create groups **`aws-billing-viewers`** and **`aws-billing-admins`**, assign yourself.
4. Copy the client secret into `/zfs/Apps/AppData/aws-billing/.env` as `KEYCLOAK_CLIENT_SECRET`.

The auth code at `src/api/auth.py` handles login/callback/logout/me, signs the session
cookie with `SESSION_SECRET` (generate via `openssl rand -hex 32`), enforces viewer-group
membership for any `/api/v1/*` (except `/health`), and gates admin endpoints
(`POST /sync/run`) on the admin group.

---

## Database

```bash
# One-time:
psql -h 192.168.128.9 -U postgres -c 'CREATE DATABASE aws_billing;'
psql -h 192.168.128.9 -U postgres -c "CREATE USER aws_billing WITH PASSWORD '...';"
psql -h 192.168.128.9 -U postgres -c 'GRANT ALL PRIVILEGES ON DATABASE aws_billing TO aws_billing;'
```

Schema is auto-applied on `init_pool()` from `src/db/schema.sql` — idempotent
`CREATE TABLE IF NOT EXISTS`. No migrations system; just edit `schema.sql` and add
backfill SQL inline if needed.

Tables:
- `account` — account_id (PK), slug, name, billing, monthly_budget_usd
- `monthly_cost` — (account_id, month) PK, gross_usd, net_usd, fetched_at
- `service_cost` — (account_id, month, service) PK, cost_usd
- `sync_run` — id, started_at, finished_at, status, error

---

## API endpoints (FastAPI on :8000, all under `/api/v1/`)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/auth/{login,callback,logout,me}` | varies | Keycloak OIDC |
| GET | `/accounts` | viewer | List with current + previous month totals |
| GET | `/accounts/{id}` | viewer | Detail + last 12 months |
| GET | `/accounts/{id}/services?month=YYYY-MM` | viewer | Service breakdown |
| GET | `/summary?month=` | viewer | Org-wide totals |
| GET | `/trends?months=` | viewer | Stacked monthly totals |
| GET | `/sync/{status,runs}` | viewer | Last run + recent runs |
| POST | `/sync/run` | **admin** | Manual sync trigger (background task) |
| GET | `/health` | none | Liveness |

---

## Daily sync

Triggered by `aws-billing-sync.timer` at 04:00:
```
podman exec aws-billing python scripts/daily_sync.py
```

Logic (see `scripts/daily_sync.py` + `src/ingestion/sync.py`):
1. Insert `sync_run` row → `running`
2. Upsert account map from `config/accounts.yaml`
3. CE call (org profile) for prev + current month, grouped account × service → upsert
4. CE call (tony profile) for prev + current month, grouped service → upsert
5. Update `sync_run` → `ok` / `error` + msg
6. Optional `HEALTHCHECK_URL` ping

Cost-Explorer pricing: ~$0.01/req. Daily refresh of 2 months × 2 profiles = ~$1.20/mo. Trivial.

**Backfill** (one-shot, run once after first deploy):
```bash
podman exec aws-billing python scripts/backfill.py --months 12
```

---

## Pre-deploy checklist (before `./deploy/run.sh`)

- [ ] Postgres database `aws_billing` + user created on `192.168.128.9`
- [ ] Keycloak client `aws-billing` configured (see above)
- [ ] IAM users + access keys created in mgmt (`975363675991`) and Tony (`519904985655`)
- [ ] `/zfs/Apps/AppData/aws-billing/.env` populated (DSN, Keycloak client/secret, session secret)
- [ ] `/zfs/Apps/AppData/aws-billing/aws-credentials` populated with `[org]` + `[tony]` profiles
- [ ] Traefik route `aws.mees.st` → container port 8000 (no forward-auth — Keycloak handled in-app)
- [ ] DNS for `aws.mees.st` pointing at the NAS

---

## Deployment

```bash
# On the NAS (192.168.128.9):
cd /path/to/aws-billing
./deploy/run.sh

# Backfill the last 12 months:
podman exec aws-billing python scripts/backfill.py --months 12

# Install systemd timer:
sudo cp deploy/aws-billing-sync.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aws-billing-sync.timer

# Manual smoke test of the timer:
sudo systemctl start aws-billing-sync.service
psql -h 192.168.128.9 -U aws_billing -c 'SELECT * FROM sync_run ORDER BY id DESC LIMIT 3;'
```

Logs:
```bash
podman logs -f aws-billing
journalctl -u aws-billing-sync.service -n 50
```

---

## Known gotchas / context

- **Tony's name discrepancy:** memory `aws_org.md` previously said "Tony Amerone"; the local YAML in `aws-account-maintenance/clients/tony-shakesby.yaml` and this repo's `config/accounts.yaml` say **Tony Shakesby**. The local YAMLs are authoritative — update memory if it's still stale.
- **Cost Explorer numbers shift:** AWS finalises invoices on the 2nd of the following month. Current-month figures are estimates and will revise downward slightly when credits land. The sync re-fetches prev + current month every day so the DB stays close to ground truth.
- **TypeScript strict mode:** the Containerfile build runs `tsc -b && vite build` which is stricter than `vite dev`. Common breakage: unused imports/vars (TS6133). Fix in source before rebuilding (don't loosen tsconfig).
- **Auth redirect loop risk:** the SPA catch-all in `app.py` returns `index.html` for unknown paths. The UI's `api/client.ts` redirects to `/api/v1/auth/login` on 401. Make sure you don't add a 401 path that matches the SPA fallback or you'll loop.
- **No mees-shared deps:** if you want to add the dashboard registration that finance has (`mees_shared.dashboard.register_with_dashboard`), copy the relevant code from finance into this repo or wire up the shared-dir copy in `build.sh` like finance does.
- **Source of accounts:** `config/accounts.yaml` was seeded from `aws-account-maintenance/clients/*.yaml`. To add/remove/rename an account, edit `accounts.yaml` here — the next sync will UPSERT the change. Don't introduce a runtime dep on the sibling repo.

---

## Reference patterns (read these for context)

| What | Where |
|---|---|
| Multi-stage Containerfile (Node UI → Python API) | `../finance/Containerfile` |
| Podman run flags + secrets-mount | `../finance/deploy/run.sh` |
| FastAPI lifespan + SPA static-serve | `../finance/src/api/app.py` |
| React/Vite/Tailwind v4 setup | `../finance/ui/` (we mirrored the package.json deps) |
| Original CE call shape (Node SDK, ported to Python) | `../aws-account-maintenance/scripts/billing-report.js:253-296` |
| Definitive AWS account list | `../aws-account-maintenance/clients/*.yaml` and the `aws_org` memory |

---

## What to do next

1. Provision the Postgres DB + user on the NAS.
2. Configure the Keycloak client + groups.
3. Provision the two IAM users (mgmt + Tony) and stash their access keys in `aws-credentials`.
4. Populate `/zfs/Apps/AppData/aws-billing/.env`.
5. `./deploy/run.sh`, then `python scripts/backfill.py --months 12`, then enable the timer.
6. Verify Summary page loads at `https://aws.mees.st` after Keycloak login.

Future ideas (not on the critical path):
- Email/Slack alert when an account exceeds its budget mid-month
- Forecast endpoint using `ce:GetCostForecast`
- Per-account ownership tags so non-admins can be limited to their own client
- Add to the `mees-shared` dashboard registry (mirror finance's `register_with_dashboard` call)
