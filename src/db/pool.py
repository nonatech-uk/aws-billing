"""asyncpg connection pool + schema bootstrap."""

from pathlib import Path

import asyncpg

from config.settings import settings

_pool: asyncpg.Pool | None = None
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=10,
    )
    async with _pool.acquire() as conn:
        await conn.execute(_SCHEMA_PATH.read_text())


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised")
    return _pool
