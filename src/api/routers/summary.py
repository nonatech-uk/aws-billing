from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_current_user, get_pool
from src.api.models import SummaryAccount, SummaryResponse
from src.db import queries

router = APIRouter()


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    month: str | None = Query(None, description="YYYY-MM (default: current)"),
    _user=Depends(get_current_user),
):
    if month is None:
        today = date.today()
        m = today.replace(day=1)
    else:
        try:
            year, mon = map(int, month.split("-"))
            m = date(year, mon, 1)
        except ValueError:
            raise HTTPException(400, "month must be YYYY-MM")
    total_gross, total_net, rows = await queries.get_summary(get_pool(), m)
    accounts = [
        SummaryAccount(
            account_id=r["account_id"],
            slug=r["slug"],
            name=r["name"],
            billing=r["billing"],
            monthly_budget_usd=r["monthly_budget_usd"],
            cost_usd=r["gross_usd"],
        )
        for r in rows
    ]
    return SummaryResponse(
        month=m,
        total_gross_usd=total_gross,
        total_net_usd=total_net,
        accounts=accounts,
    )
