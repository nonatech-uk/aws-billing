"""Read queries — kept thin so routers stay small."""

from datetime import date

import asyncpg


async def list_accounts_with_recent_totals(
    pool: asyncpg.Pool, current_month: date, prev_month: date
) -> list[dict]:
    sql = """
        SELECT a.account_id, a.slug, a.name, a.billing, a.monthly_budget_usd,
               COALESCE(curr.gross_usd, 0)::float8 AS current_month_usd,
               COALESCE(prev.gross_usd, 0)::float8 AS prev_month_usd
        FROM account a
        LEFT JOIN monthly_cost curr
          ON curr.account_id = a.account_id AND curr.month = $1
        LEFT JOIN monthly_cost prev
          ON prev.account_id = a.account_id AND prev.month = $2
        ORDER BY current_month_usd DESC, a.name
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, current_month, prev_month)
    return [dict(r) for r in rows]


async def get_account(pool: asyncpg.Pool, account_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT account_id, slug, name, billing, monthly_budget_usd FROM account WHERE account_id = $1",
            account_id,
        )
    return dict(row) if row else None


async def get_monthly_series(
    pool: asyncpg.Pool, account_id: str, months: int
) -> list[dict]:
    sql = """
        SELECT month, gross_usd::float8 AS gross_usd, net_usd::float8 AS net_usd
        FROM monthly_cost
        WHERE account_id = $1
        ORDER BY month DESC
        LIMIT $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, account_id, months)
    return list(reversed([dict(r) for r in rows]))


async def get_services(
    pool: asyncpg.Pool, account_id: str, month: date
) -> list[dict]:
    sql = """
        SELECT service, cost_usd::float8 AS cost_usd
        FROM service_cost
        WHERE account_id = $1 AND month = $2
        ORDER BY cost_usd DESC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, account_id, month)
    return [dict(r) for r in rows]


async def get_summary(pool: asyncpg.Pool, month: date) -> tuple[float, float, list[dict]]:
    sql = """
        SELECT a.account_id, a.slug, a.name, a.billing, a.monthly_budget_usd,
               COALESCE(mc.gross_usd, 0)::float8 AS gross_usd,
               COALESCE(mc.net_usd, 0)::float8 AS net_usd
        FROM account a
        LEFT JOIN monthly_cost mc
          ON mc.account_id = a.account_id AND mc.month = $1
        ORDER BY gross_usd DESC, a.name
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, month)
    accounts = [dict(r) for r in rows]
    total_gross = sum(r["gross_usd"] for r in accounts)
    total_net = sum(r["net_usd"] for r in accounts)
    return total_gross, total_net, accounts


async def get_trends(pool: asyncpg.Pool, months: int) -> list[dict]:
    sql = """
        SELECT mc.month, a.slug, mc.gross_usd::float8 AS gross_usd
        FROM monthly_cost mc
        JOIN account a ON a.account_id = mc.account_id
        WHERE mc.month >= (date_trunc('month', current_date) - ($1::int - 1) * interval '1 month')::date
        ORDER BY mc.month
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, months)
    by_month: dict[date, dict[str, float]] = {}
    for r in rows:
        by_month.setdefault(r["month"], {})[r["slug"]] = r["gross_usd"]
    out = []
    for month in sorted(by_month):
        per = by_month[month]
        out.append({
            "month": month,
            "total_gross_usd": sum(per.values()),
            "by_account": per,
        })
    return out


async def last_sync_run(pool: asyncpg.Pool) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, started_at, finished_at, status, error FROM sync_run ORDER BY id DESC LIMIT 1"
        )
    return dict(row) if row else None


async def recent_sync_runs(pool: asyncpg.Pool, limit: int = 7) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, started_at, finished_at, status, error FROM sync_run ORDER BY id DESC LIMIT $1",
            limit,
        )
    return [dict(r) for r in rows]
