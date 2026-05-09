"""Sync orchestrator — ports CE results into Postgres.

Splits services into gross (cost > 0) and credits/refunds (cost < 0); writes
gross_usd + net_usd onto monthly_cost; writes one row per service into
service_cost.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import asyncpg
import yaml

from config.settings import settings
from src.ingestion.cost_explorer import (
    fetch_account_costs,
    fetch_account_usage,
    fetch_org_costs,
    fetch_org_usage,
)

_log = logging.getLogger(__name__)
_ACCOUNTS_PATH = Path(__file__).resolve().parents[2] / "config" / "accounts.yaml"


def load_accounts() -> list[dict]:
    return yaml.safe_load(_ACCOUNTS_PATH.read_text())["accounts"]


async def upsert_accounts(pool: asyncpg.Pool, accounts: list[dict]) -> None:
    sql = """
        INSERT INTO account (account_id, slug, name, billing, monthly_budget_usd)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (account_id) DO UPDATE SET
            slug = EXCLUDED.slug,
            name = EXCLUDED.name,
            billing = EXCLUDED.billing,
            monthly_budget_usd = EXCLUDED.monthly_budget_usd
    """
    async with pool.acquire() as conn:
        for a in accounts:
            await conn.execute(
                sql,
                a["account_id"],
                a["slug"],
                a["name"],
                a["billing"],
                a.get("monthly_budget_usd"),
            )


async def _write_month(
    pool: asyncpg.Pool,
    account_id: str,
    month: date,
    services: dict[str, float],
    usage: dict[str, tuple[float, str]] | None = None,
) -> None:
    gross = sum(c for c in services.values() if c > 0)
    net = sum(services.values())
    usage = usage or {}
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO monthly_cost (account_id, month, gross_usd, net_usd, fetched_at)
                VALUES ($1, $2, $3, $4, now())
                ON CONFLICT (account_id, month) DO UPDATE SET
                    gross_usd = EXCLUDED.gross_usd,
                    net_usd = EXCLUDED.net_usd,
                    fetched_at = now()
                """,
                account_id,
                month,
                gross,
                net,
            )
            await conn.execute(
                "DELETE FROM service_cost WHERE account_id = $1 AND month = $2",
                account_id,
                month,
            )
            for service, cost in services.items():
                if cost == 0:
                    continue
                qty_unit = usage.get(service)
                qty = qty_unit[0] if qty_unit else None
                unit = qty_unit[1] if qty_unit else None
                await conn.execute(
                    """
                    INSERT INTO service_cost (account_id, month, service, cost_usd, usage_qty, usage_unit)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    account_id,
                    month,
                    service,
                    cost,
                    qty,
                    unit,
                )


async def sync_month(pool: asyncpg.Pool, month: date) -> None:
    """Sync one month for all accounts."""
    accounts = load_accounts()
    await upsert_accounts(pool, accounts)

    org_accounts = {a["account_id"] for a in accounts if a["billing"] == "org"}
    separate_accounts = [a for a in accounts if a["billing"] == "separate"]

    if org_accounts:
        _log.info("CE org profile %s for %s", settings.aws_profile_org, month)
        org_data = fetch_org_costs(settings.aws_profile_org, month)
        org_usage = fetch_org_usage(settings.aws_profile_org, month)
        for account_id in org_accounts:
            services = org_data.get(account_id, {})
            usage = org_usage.get(account_id, {})
            await _write_month(pool, account_id, month, services, usage)

    for a in separate_accounts:
        _log.info("CE separate profile %s for %s (%s)", settings.aws_profile_separate, month, a["slug"])
        services = fetch_account_costs(settings.aws_profile_separate, month)
        usage = fetch_account_usage(settings.aws_profile_separate, month)
        await _write_month(pool, a["account_id"], month, services, usage)


async def start_sync_run(pool: asyncpg.Pool) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO sync_run (status) VALUES ('running') RETURNING id"
        )
    return row["id"]


async def finish_sync_run(
    pool: asyncpg.Pool, run_id: int, status: str, error: str | None = None
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sync_run SET finished_at = now(), status = $2, error = $3 WHERE id = $1",
            run_id,
            status,
            error,
        )
