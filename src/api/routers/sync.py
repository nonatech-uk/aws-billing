import asyncio
import logging
from datetime import date

from fastapi import APIRouter, Depends

from src.api.deps import get_current_user, get_pool, require_admin
from src.api.models import SyncRunRow
from src.db import queries
from src.ingestion.sync import finish_sync_run, start_sync_run, sync_month

router = APIRouter()
_log = logging.getLogger(__name__)


def _current_and_prev_month() -> tuple[date, date]:
    today = date.today().replace(day=1)
    prev = date(today.year, today.month - 1, 1) if today.month > 1 else date(today.year - 1, 12, 1)
    return today, prev


@router.get("/sync/status", response_model=SyncRunRow | None)
async def sync_status(_user=Depends(get_current_user)):
    return await queries.last_sync_run(get_pool())


@router.get("/sync/runs", response_model=list[SyncRunRow])
async def sync_runs(_user=Depends(get_current_user)):
    return await queries.recent_sync_runs(get_pool(), limit=7)


@router.post("/sync/run", response_model=SyncRunRow)
async def sync_run(_admin=Depends(require_admin)):
    pool = get_pool()
    run_id = await start_sync_run(pool)

    async def _bg():
        try:
            today, prev = _current_and_prev_month()
            await sync_month(pool, prev)
            await sync_month(pool, today)
            await finish_sync_run(pool, run_id, "ok")
        except Exception as e:
            _log.exception("sync failed")
            await finish_sync_run(pool, run_id, "error", str(e))

    asyncio.create_task(_bg())
    return await queries.last_sync_run(pool)
