from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo('America/New_York')


def now_business() -> datetime:
    return datetime.now(UTC).astimezone(BUSINESS_TZ)


def to_business(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(BUSINESS_TZ)


def business_midnight(dt: datetime) -> datetime:
    local = to_business(dt)
    return datetime(local.year, local.month, local.day, tzinfo=BUSINESS_TZ)


def business_month_start(dt: datetime) -> datetime:
    local = to_business(dt)
    return datetime(local.year, local.month, 1, tzinfo=BUSINESS_TZ)


def previous_business_month_start(dt: datetime) -> datetime:
    current = business_month_start(dt)
    if current.month == 1:
        return datetime(current.year - 1, 12, 1, tzinfo=BUSINESS_TZ)
    return datetime(current.year, current.month - 1, 1, tzinfo=BUSINESS_TZ)


def business_quarter_start(dt: datetime) -> datetime:
    local = to_business(dt)
    month = ((local.month - 1) // 3) * 3 + 1
    return datetime(local.year, month, 1, tzinfo=BUSINESS_TZ)


def previous_business_quarter_start(dt: datetime) -> datetime:
    current = business_quarter_start(dt)
    if current.month == 1:
        return datetime(current.year - 1, 10, 1, tzinfo=BUSINESS_TZ)
    return datetime(current.year, current.month - 3, 1, tzinfo=BUSINESS_TZ)


def previous_business_week_start(dt: datetime) -> datetime:
    local = to_business(dt)
    weekday = local.weekday()  # Mon=0
    monday = datetime(local.year, local.month, local.day, tzinfo=BUSINESS_TZ) - timedelta(days=weekday)
    return monday
