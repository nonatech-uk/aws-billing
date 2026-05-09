"""boto3 Cost Explorer client wrappers.

Two flavours:
  - org profile: groups by LINKED_ACCOUNT x SERVICE — covers all consolidated accounts
  - separate profile (per separately-invoiced account): groups by SERVICE only
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import boto3


def _month_window(month: date) -> tuple[str, str]:
    """CE expects [start, end) — start = first of month, end = first of next month."""
    start = month.replace(day=1).isoformat()
    if month.month == 12:
        end = date(month.year + 1, 1, 1).isoformat()
    else:
        end = date(month.year, month.month + 1, 1).isoformat()
    return start, end


def fetch_org_costs(profile: str, month: date) -> dict[str, dict[str, float]]:
    """Returns {account_id: {service: cost_usd}} for one month, via the mgmt account."""
    session = boto3.Session(profile_name=profile)
    ce = session.client("ce", region_name="us-east-1")
    start, end = _month_window(month)

    out: dict[str, dict[str, float]] = defaultdict(dict)
    next_token: str | None = None
    while True:
        kwargs = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": "MONTHLY",
            "Metrics": ["UnblendedCost"],
            "GroupBy": [
                {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
                {"Type": "DIMENSION", "Key": "SERVICE"},
            ],
        }
        if next_token:
            kwargs["NextPageToken"] = next_token
        resp = ce.get_cost_and_usage(**kwargs)
        for result in resp.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                account_id, service = group["Keys"]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                out[account_id][service] = out[account_id].get(service, 0.0) + amount
        next_token = resp.get("NextPageToken")
        if not next_token:
            break
    return dict(out)


def fetch_account_costs(profile: str, month: date) -> dict[str, float]:
    """Returns {service: cost_usd} for the account behind `profile`, one month."""
    session = boto3.Session(profile_name=profile)
    ce = session.client("ce", region_name="us-east-1")
    start, end = _month_window(month)

    out: dict[str, float] = {}
    next_token: str | None = None
    while True:
        kwargs = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": "MONTHLY",
            "Metrics": ["UnblendedCost"],
            "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        }
        if next_token:
            kwargs["NextPageToken"] = next_token
        resp = ce.get_cost_and_usage(**kwargs)
        for result in resp.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                (service,) = group["Keys"]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                out[service] = out.get(service, 0.0) + amount
        next_token = resp.get("NextPageToken")
        if not next_token:
            break
    return out


# Headline-usage rules: for these services, sum the matching usage_types to a
# single (qty, unit) headline. CE returns each region's usage as a separate
# usage_type, so we sum across regions per account/month.
_USAGE_RULES = (
    {
        "service": "Amazon Simple Storage Service",
        "match": lambda ut: "TimedStorage" in ut and "ByteHrs" in ut,
        "unit": "GB-Month",
    },
    {
        "service": "AWS Secrets Manager",
        "match": lambda ut: ut.endswith("-AWSSecretsManager-Secrets"),
        "unit": "Secrets",
    },
)
_USAGE_SERVICES = [r["service"] for r in _USAGE_RULES]


def _aggregate_usage(usage_type: str, qty: float, into: dict[str, tuple[float, str]]) -> None:
    for rule in _USAGE_RULES:
        if rule["match"](usage_type):
            cur_qty, _ = into.get(rule["service"], (0.0, rule["unit"]))
            into[rule["service"]] = (cur_qty + qty, rule["unit"])
            return


def fetch_org_usage(profile: str, month: date) -> dict[str, dict[str, tuple[float, str]]]:
    """Returns {account_id: {service: (qty, unit)}} for headline-usage services."""
    session = boto3.Session(profile_name=profile)
    ce = session.client("ce", region_name="us-east-1")
    start, end = _month_window(month)

    out: dict[str, dict[str, tuple[float, str]]] = defaultdict(dict)
    next_token: str | None = None
    while True:
        kwargs = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": "MONTHLY",
            "Metrics": ["UsageQuantity"],
            "Filter": {"Dimensions": {"Key": "SERVICE", "Values": _USAGE_SERVICES}},
            "GroupBy": [
                {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
                {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
            ],
        }
        if next_token:
            kwargs["NextPageToken"] = next_token
        resp = ce.get_cost_and_usage(**kwargs)
        for result in resp.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                account_id, usage_type = group["Keys"]
                qty = float(group["Metrics"]["UsageQuantity"]["Amount"])
                _aggregate_usage(usage_type, qty, out[account_id])
        next_token = resp.get("NextPageToken")
        if not next_token:
            break
    return {k: dict(v) for k, v in out.items()}


def fetch_account_usage(profile: str, month: date) -> dict[str, tuple[float, str]]:
    """Returns {service: (qty, unit)} for headline-usage services on this profile."""
    session = boto3.Session(profile_name=profile)
    ce = session.client("ce", region_name="us-east-1")
    start, end = _month_window(month)

    out: dict[str, tuple[float, str]] = {}
    next_token: str | None = None
    while True:
        kwargs = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": "MONTHLY",
            "Metrics": ["UsageQuantity"],
            "Filter": {"Dimensions": {"Key": "SERVICE", "Values": _USAGE_SERVICES}},
            "GroupBy": [{"Type": "DIMENSION", "Key": "USAGE_TYPE"}],
        }
        if next_token:
            kwargs["NextPageToken"] = next_token
        resp = ce.get_cost_and_usage(**kwargs)
        for result in resp.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                (usage_type,) = group["Keys"]
                qty = float(group["Metrics"]["UsageQuantity"]["Amount"])
                _aggregate_usage(usage_type, qty, out)
        next_token = resp.get("NextPageToken")
        if not next_token:
            break
    return out
