"""One-shot backfill: refresh the last N months from Cost Explorer."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

_root = str(Path(__file__).resolve().parents[1])
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.db.pool import close_pool, init_pool  # noqa: E402
from src.ingestion.sync import (  # noqa: E402
    finish_sync_run,
    start_sync_run,
    sync_month,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("backfill")


def _months_back(n: int) -> list[date]:
    """Return [n-1 months ago, …, current month] inclusive (first-of-month dates)."""
    today = date.today().replace(day=1)
    out: list[date] = []
    for i in range(n - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        out.append(date(year, month, 1))
    return out


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=12)
    args = parser.parse_args()

    await init_pool()
    from src.db.pool import get_pool

    pool = get_pool()
    run_id = await start_sync_run(pool)
    rc = 0
    try:
        for m in _months_back(args.months):
            _log.info("backfilling %s", m)
            await sync_month(pool, m)
        await finish_sync_run(pool, run_id, "ok")
    except Exception as e:
        _log.exception("backfill failed")
        await finish_sync_run(pool, run_id, "error", str(e))
        rc = 1
    finally:
        await close_pool()
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
