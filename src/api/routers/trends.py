from fastapi import APIRouter, Depends, Query

from src.api.deps import get_current_user, get_pool
from src.api.models import TrendPoint
from src.db import queries

router = APIRouter()


@router.get("/trends", response_model=list[TrendPoint])
async def get_trends(
    months: int = Query(12, ge=1, le=24),
    _user=Depends(get_current_user),
):
    rows = await queries.get_trends(get_pool(), months)
    return [TrendPoint(**r) for r in rows]
