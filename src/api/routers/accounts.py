from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_current_user, get_pool
from src.api.models import AccountDetail, AccountRow, MonthlyPoint, ServiceRow
from src.db import queries

router = APIRouter()


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _prev_month(d: date) -> date:
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)


@router.get("/accounts", response_model=list[AccountRow])
async def list_accounts(_user=Depends(get_current_user)):
    today = date.today()
    rows = await queries.list_accounts_with_recent_totals(
        get_pool(), _first_of_month(today), _prev_month(_first_of_month(today))
    )
    return rows


@router.get("/accounts/{account_id}", response_model=AccountDetail)
async def get_account(account_id: str, _user=Depends(get_current_user)):
    pool = get_pool()
    acct = await queries.get_account(pool, account_id)
    if acct is None:
        raise HTTPException(404, "Account not found")
    monthly = await queries.get_monthly_series(pool, account_id, months=12)
    return AccountDetail(
        **acct,
        monthly=[MonthlyPoint(**m) for m in monthly],
    )


@router.get("/accounts/{account_id}/services", response_model=list[ServiceRow])
async def get_account_services(
    account_id: str,
    month: str = Query(..., description="YYYY-MM"),
    _user=Depends(get_current_user),
):
    try:
        year, mon = map(int, month.split("-"))
        month_date = date(year, mon, 1)
    except ValueError:
        raise HTTPException(400, "month must be YYYY-MM")
    services = await queries.get_services(get_pool(), account_id, month_date)
    total = sum(s["cost_usd"] for s in services if s["cost_usd"] > 0) or 1
    return [
        ServiceRow(service=s["service"], cost_usd=s["cost_usd"], pct=s["cost_usd"] / total * 100)
        for s in services
    ]
