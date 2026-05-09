# aws-billing

Internal website at `https://aws.mees.st` showing monthly AWS Cost Explorer figures
per linked account in the Nonatech organisation, plus Tony Amerone's separately
invoiced account. Auth via Keycloak OIDC (`kc.mees.st`).

## Stack

- FastAPI + asyncpg + boto3
- React 19 + Vite + TypeScript + Tailwind v4 + TanStack Query + Recharts
- PostgreSQL on `192.168.128.9`
- Podman + systemd timer on the NAS

## Local development

```bash
# 1. Postgres database
psql -h 192.168.128.9 -U postgres -c 'CREATE DATABASE aws_billing;'

# 2. Backend (Python 3.12)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example config/.env  # then edit secrets
# AUTH_ENABLED=false in config/.env to skip Keycloak during dev
uvicorn src.api.app:app --reload --port 8000

# 3. UI (separate terminal)
cd ui
npm install
npm run dev   # :5173, proxies /api -> :8000
```

## First-time data load

```bash
python scripts/backfill.py --months 12
```

## Deployment

Secrets live in `/zfs/Apps/AppData/aws-billing/`:
- `.env`              — DB DSN, Keycloak client secret, session secret
- `aws-credentials`   — `~/.aws/credentials`-format file with `org` + `tony` profiles

```bash
./deploy/run.sh
sudo cp deploy/aws-billing-sync.{service,timer} /etc/systemd/system/
sudo systemctl enable --now aws-billing-sync.timer
```

## Endpoints

All under `/api/v1/`:

| Path | Notes |
|------|-------|
| `/auth/{login,callback,logout,me}` | Keycloak OIDC |
| `/accounts` | List with current + previous month totals |
| `/accounts/{id}` | Detail + 12-month series |
| `/accounts/{id}/services?month=` | Service breakdown |
| `/summary?month=` | Org-wide totals |
| `/trends?months=` | Stacked monthly totals |
| `/sync/{status,run}` | Last run + manual trigger (admin) |
| `/health` | Liveness, no auth |
