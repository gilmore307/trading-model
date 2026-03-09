from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo

BJ = ZoneInfo('Asia/Shanghai')


@dataclass
class ReviewWindow:
    name: str
    start_utc: datetime
    end_utc: datetime
    start_bj: datetime
    end_bj: datetime


def current_bj_week_window(now_utc: datetime | None = None) -> ReviewWindow:
    now_utc = now_utc or datetime.now(UTC)
    now_bj = now_utc.astimezone(BJ)
    weekday = now_bj.weekday()  # Monday=0 ... Sunday=6
    days_since_sunday = weekday + 1 if weekday < 6 else 0
    last_sunday_start = (now_bj - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_bj = last_sunday_start
    start_bj = end_bj - timedelta(days=7)

    return ReviewWindow(
        name='weekly',
        start_utc=start_bj.astimezone(UTC),
        end_utc=end_bj.astimezone(UTC),
        start_bj=start_bj,
        end_bj=end_bj,
    )


def rolling_windows(now_utc: datetime | None = None) -> dict[str, ReviewWindow]:
    weekly = current_bj_week_window(now_utc)
    rolling_4w_start_bj = weekly.end_bj - timedelta(days=28)
    rolling_3m_start_bj = weekly.end_bj - timedelta(days=90)
    return {
        'weekly': weekly,
        'rolling_4w': ReviewWindow(
            name='rolling_4w',
            start_utc=rolling_4w_start_bj.astimezone(UTC),
            end_utc=weekly.end_bj.astimezone(UTC),
            start_bj=rolling_4w_start_bj,
            end_bj=weekly.end_bj,
        ),
        'rolling_3m': ReviewWindow(
            name='rolling_3m',
            start_utc=rolling_3m_start_bj.astimezone(UTC),
            end_utc=weekly.end_bj.astimezone(UTC),
            start_bj=rolling_3m_start_bj,
            end_bj=weekly.end_bj,
        ),
    }
