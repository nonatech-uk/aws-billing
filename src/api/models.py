"""Pydantic response models."""

from datetime import date, datetime

from pydantic import BaseModel


class CurrentUser(BaseModel):
    email: str
    name: str
    is_admin: bool


class AccountRow(BaseModel):
    account_id: str
    slug: str
    name: str
    billing: str
    monthly_budget_usd: float | None
    current_month_usd: float
    prev_month_usd: float


class MonthlyPoint(BaseModel):
    month: date
    gross_usd: float
    net_usd: float


class AccountDetail(BaseModel):
    account_id: str
    slug: str
    name: str
    billing: str
    monthly_budget_usd: float | None
    monthly: list[MonthlyPoint]


class ServiceRow(BaseModel):
    service: str
    cost_usd: float
    pct: float
    usage_qty: float | None = None
    usage_unit: str | None = None


class SummaryAccount(BaseModel):
    account_id: str
    slug: str
    name: str
    billing: str
    monthly_budget_usd: float | None
    cost_usd: float


class SummaryResponse(BaseModel):
    month: date
    total_gross_usd: float
    total_net_usd: float
    accounts: list[SummaryAccount]


class TrendPoint(BaseModel):
    month: date
    total_gross_usd: float
    by_account: dict[str, float]


class SyncRunRow(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    error: str | None
