"""Daily sync orchestrator.

Refreshes current + previous month for every account; pings HEALTHCHECK_URL on
success. Triggered from systemd via:

    podman exec aws-billing python scripts/daily_sync.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

import httpx

_root = str(Path(__file__).resolve().parents[1])
if _root not in sys.path:
    sys.path.insert(0, _root)

from config.settings import settings  # noqa: E402
from src.db.pool import close_pool, init_pool  # noqa: E402
from src.ingestion.sync import (  # noqa: E402
    finish_sync_run,
    start_sync_run,
    sync_month,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("daily_sync")


def _current_and_prev_month() -> tuple[date, date]:
    today = date.today().replace(day=1)
    prev = date(today.year, today.month - 1, 1) if today.month > 1 else date(today.year - 1, 12, 1)
    return today, prev


async def main() -> int:
    await init_pool()
    from src.db.pool import get_pool

    pool = get_pool()
    run_id = await start_sync_run(pool)
    rc = 0
    try:
        today, prev = _current_and_prev_month()
        _log.info("syncing %s and %s", prev, today)
        await sync_month(pool, prev)
        await sync_month(pool, today)
        await finish_sync_run(pool, run_id, "ok")
        _log.info("sync ok")
        if settings.healthcheck_url:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.get(settings.healthcheck_url)
            except Exception as e:
                _log.warning("healthcheck ping failed: %s", e)
    except Exception as e:
        _log.exception("sync failed")
        await finish_sync_run(pool, run_id, "error", str(e))
        rc = 1
    finally:
        await close_pool()
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
