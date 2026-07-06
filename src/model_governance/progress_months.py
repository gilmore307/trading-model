"""Month-level progress helpers for chronological model-generation jobs."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Mapping

MONTH_RE = re.compile(r"^(\d{4})-(\d{2})")


def month_key(value: Any) -> str | None:
    """Return a YYYY-MM key from a datetime/date/string value."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return f"{value.year:04d}-{value.month:02d}"
    if isinstance(value, date):
        return f"{value.year:04d}-{value.month:02d}"
    match = MONTH_RE.match(str(value).strip())
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}"


def month_keys_between(start: Any, end: Any) -> list[str]:
    """Return inclusive start, exclusive end YYYY-MM keys."""

    start_key = month_key(start)
    end_key = month_key(end)
    if not start_key or not end_key:
        return []
    start_year, start_month = (int(part) for part in start_key.split("-", 1))
    end_year, end_month = (int(part) for part in end_key.split("-", 1))
    months: list[str] = []
    year, month = start_year, start_month
    while (year, month) < (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year += 1
            month = 1
    return months


def month_progress(
    *,
    source_start: Any,
    source_end: Any,
    current_time: Any = None,
    completed: bool = False,
) -> dict[str, Any] | None:
    """Build a compact month-progress payload for dashboard row generators."""

    months = month_keys_between(source_start, source_end)
    if not months:
        return None
    current_month = month_key(current_time) or months[0]
    if completed:
        completed_months = len(months)
        current_month = months[-1]
    elif current_month in months:
        completed_months = months.index(current_month)
    elif current_month < months[0]:
        completed_months = 0
        current_month = months[0]
    else:
        completed_months = len(months)
        current_month = months[-1]
    return {
        "current_month": current_month,
        "completed_months": completed_months,
        "expected_months": len(months),
        "unit_label": "dataset months",
        "months": months,
    }


def month_progress_from_rows(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    source_start: Any,
    source_end: Any,
    completed: bool = False,
) -> dict[str, Any] | None:
    current_time = None
    for row in reversed(rows):
        current_time = row.get("available_time") or row.get("tradeable_time")
        if current_time is not None:
            break
    return month_progress(source_start=source_start, source_end=source_end, current_time=current_time, completed=completed)
