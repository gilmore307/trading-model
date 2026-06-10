"""Build reviewed local inputs for the event-family impact-window backtest.

The builder reads local Trading Economics calendar files and SQL-retained
Alpaca/GDELT rows. It performs no provider calls, SQL writes, model training,
model activation, broker/account mutation, or artifact deletion.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_runtime.config import data_storage_root, model_storage_root, secret_root
from models.model_10_event_risk_governor.event_family_empirical_coverage import FAMILY_KEYWORDS
from models.model_10_event_risk_governor.event_family_impact_window_backtest import (
    build_real_input_event_family_impact_window_backtest,
    write_event_family_impact_window_backtest_artifacts,
)

DEFAULT_OUTPUT_DIR = model_storage_root() / "event_family_impact_window_real_input_backtest_20260610"
DEFAULT_ALL_FAMILY_OUTPUT_DIR = model_storage_root() / "event_family_impact_window_all_family_real_input_backtest_20260610"
DEFAULT_START_DATE = date(2016, 1, 1)
DEFAULT_END_DATE_EXCLUSIVE = date(2026, 3, 1)
DEFAULT_SYMBOLS = ("SPY", "QQQ", "IWM")
DEFAULT_STORAGE_SECRET_ALIAS = "trading_storage_postgres"
EVENT_FIELDS = ("family_key", "event_temporal_form", "event_date", "event_ref", "source_ref")
BAR_FIELDS = ("symbol", "date", "open", "high", "low", "close")
SHOCK_NEWS_PATTERN = re.compile(
    r"(breaking|shock|crisis|war|invasion|missile|sanction|tariff|bank|default|crash|shutdown|cyberattack|federal reserve|inflation)",
    re.IGNORECASE,
)
EXTRA_FAMILY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "earnings_guidance_scheduled_shell": ("earnings", "guidance", "reports results", "quarterly results"),
    "earnings_guidance_result_metrics": ("earnings", "eps", "revenue", "profit"),
    "earnings_guidance_raise_cut_or_withdrawal": ("raises guidance", "cuts guidance", "withdraws guidance", "outlook"),
}
SCHEDULED_DATA_RELEASE_FAMILIES = {
    "cpi_inflation_release",
    "fomc_rates_policy",
    "nfp_employment_release",
}
SCHEDULED_CALENDAR_FAMILIES = {
    "earnings_guidance_scheduled_shell",
    "triple_witching_calendar",
}


@dataclass(frozen=True)
class RealInputBuildResult:
    event_csv: str
    bar_csv: str
    backtest_output_dir: str
    summary_path: str
    start_date: str
    end_date_exclusive: str
    symbols: tuple[str, ...]
    event_counts_by_family: dict[str, int]
    bar_rows: int
    provider_calls: int = 0
    sql_writes: int = 0
    model_training_performed: bool = False
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False
    review_status: str = "requires_review_before_promotion_evidence_use"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _month_iter(start: date, end_exclusive: date) -> list[str]:
    months: list[str] = []
    cursor = date(start.year, start.month, 1)
    while cursor < end_exclusive:
        months.append(f"{cursor.year:04d}-{cursor.month:02d}")
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


def _third_friday(year: int, month: int) -> date:
    day = date(year, month, 1)
    while day.weekday() != 4:
        day += timedelta(days=1)
    return day + timedelta(days=14)


def triple_witching_events(start: date, end_exclusive: date) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in range(start.year, end_exclusive.year + 1):
        for month in (3, 6, 9, 12):
            day = _third_friday(year, month)
            if start <= day < end_exclusive:
                rows.append(
                    {
                        "family_key": "triple_witching_calendar",
                        "event_temporal_form": "scheduled_calendar_event",
                        "event_date": day.isoformat(),
                        "event_ref": f"triple_witching_calendar_{day:%Y%m%d}",
                        "source_ref": "rule://third-friday-quarterly-index-stock-option-futures-expiration",
                    }
                )
    return rows


def cpi_events_from_trading_economics(source_root: Path, start: date, end_exclusive: date) -> list[dict[str, str]]:
    rows_by_date: dict[date, set[str]] = {}
    te_root = source_root / "trading_economics_calendar_web"
    for month in _month_iter(start, end_exclusive):
        for path in sorted((te_root / month).glob("runs/*/saved/trading_economics_calendar_event.csv")):
            with path.open(encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    if str(row.get("country") or "") != "United States":
                        continue
                    event_text = " ".join([str(row.get("event") or ""), str(row.get("source_event_type") or "")]).lower()
                    if "inflation rate" not in event_text or "ppi" in event_text or "expect" in event_text:
                        continue
                    event_time = str(row.get("event_time") or "")
                    if len(event_time) < 10:
                        continue
                    day = _parse_date(event_time)
                    if start <= day < end_exclusive:
                        rows_by_date.setdefault(day, set()).add(str(path))
    return [
        {
            "family_key": "cpi_inflation_release",
            "event_temporal_form": "scheduled_data_release_event",
            "event_date": day.isoformat(),
            "event_ref": f"cpi_inflation_release_{day:%Y%m%d}",
            "source_ref": ";".join(sorted(source_refs)),
        }
        for day, source_refs in sorted(rows_by_date.items())
    ]


def _database_url(explicit: str | None, *, secret_alias: str) -> str:
    if explicit:
        return explicit
    path = secret_root() / f"{secret_alias}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    dsn = str(payload.get("dsn") or "").strip()
    if not dsn:
        raise ValueError(f"secret alias {secret_alias!r} does not contain a dsn field")
    return dsn


def _load_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("psycopg is required for SQL-retained real input export") from exc
    return psycopg, dict_row


def breaking_news_events_from_sql(
    *,
    database_url: str,
    start: date,
    end_exclusive: date,
    max_dates: int,
) -> list[dict[str, str]]:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                  created_at::date AS event_date,
                  count(*) AS matched_rows,
                  min(id) AS sample_id
                FROM trading_data.feed_03_alpaca_news
                WHERE created_at >= %s
                  AND created_at < %s
                  AND (
                    lower(coalesce(timeline_headline, '')) ~ %s
                    OR lower(coalesce(summary, '')) ~ %s
                  )
                GROUP BY created_at::date
                ORDER BY matched_rows DESC, event_date
                LIMIT %s
                """,
                (start.isoformat(), end_exclusive.isoformat(), SHOCK_NEWS_PATTERN.pattern, SHOCK_NEWS_PATTERN.pattern, max_dates),
            )
            alpaca_rows = cursor.fetchall()
            remaining = max(0, max_dates - len(alpaca_rows))
            cursor.execute(
                """
                SELECT
                  seen_at::date AS event_date,
                  count(*) AS matched_rows,
                  min(article_id) AS sample_article_id
                FROM trading_data.feed_05_gdelt_article
                WHERE seen_at >= %s
                  AND seen_at < %s
                  AND (
                    lower(coalesce(title, '')) ~ %s
                    OR lower(coalesce(source_theme_tags, '')) ~ %s
                  )
                GROUP BY seen_at::date
                ORDER BY matched_rows DESC, event_date
                LIMIT %s
                """,
                (start.isoformat(), end_exclusive.isoformat(), SHOCK_NEWS_PATTERN.pattern, SHOCK_NEWS_PATTERN.pattern, remaining),
            )
            gdelt_rows = cursor.fetchall()
    rows: list[dict[str, str]] = [
        {
            "family_key": "breaking_news_shock",
            "event_temporal_form": "instantaneous_unscheduled_event",
            "event_date": row["event_date"].isoformat(),
            "event_ref": f"breaking_news_shock_{row['event_date']:%Y%m%d}",
            "source_ref": f"sql://trading_data.feed_03_alpaca_news/{row['event_date']}?matched_rows={row['matched_rows']}&sample_id={row['sample_id']}",
        }
        for row in alpaca_rows
    ]
    seen_dates = {row["event_date"] for row in rows}
    rows.extend(
        {
            "family_key": "breaking_news_shock",
            "event_temporal_form": "instantaneous_unscheduled_event",
            "event_date": row["event_date"].isoformat(),
            "event_ref": f"breaking_news_shock_{row['event_date']:%Y%m%d}",
            "source_ref": f"sql://trading_data.feed_05_gdelt_article/{row['event_date']}?matched_rows={row['matched_rows']}&sample_article_id={row['sample_article_id']}",
        }
        for row in gdelt_rows
        if row["event_date"].isoformat() not in seen_dates
    )
    return rows[:max_dates]


def _family_keyword_map() -> dict[str, tuple[str, ...]]:
    keywords = {family: tuple(values) for family, values in FAMILY_KEYWORDS.items()}
    keywords.update(EXTRA_FAMILY_KEYWORDS)
    keywords["breaking_news_shock"] = tuple(SHOCK_NEWS_PATTERN.pattern.strip("()").split("|"))
    return dict(sorted(keywords.items()))


def _pattern_for_keywords(keywords: Sequence[str]) -> str:
    return "|".join(sorted({keyword.lower().replace("'", "''") for keyword in keywords if keyword.strip()}, key=len, reverse=True))


def _temporal_form_for_family(family: str) -> str:
    if family in SCHEDULED_DATA_RELEASE_FAMILIES:
        return "scheduled_data_release_event"
    if family in SCHEDULED_CALENDAR_FAMILIES:
        return "scheduled_calendar_event"
    return "instantaneous_unscheduled_event"


def _sql_source_ref(feed: str, event_day: date, matched_rows: int, sample_ref: Any) -> str:
    sample_key = "sample_id" if feed == "feed_03_alpaca_news" else "sample_article_id"
    return f"sql://trading_data.{feed}/{event_day}?matched_rows={matched_rows}&{sample_key}={sample_ref}"


def family_candidate_events_from_sql(
    *,
    database_url: str,
    start: date,
    end_exclusive: date,
    max_dates_per_family: int,
    include_families: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    """Build fold-calibration candidate events from retained point-in-time SQL rows.

    The route is intentionally conservative: it emits dated canonical candidate
    event instances per family, deduped by family/date, and leaves promotion
    approval to downstream review.
    """
    psycopg, dict_row = _load_psycopg()
    family_keywords = _family_keyword_map()
    if include_families is not None:
        allowed = set(include_families)
        family_keywords = {family: keywords for family, keywords in family_keywords.items() if family in allowed}
    rows: list[dict[str, str]] = []
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            for family, keywords in family_keywords.items():
                pattern = _pattern_for_keywords(keywords)
                if not pattern:
                    continue
                cursor.execute(
                    """
                    SELECT
                      created_at::date AS event_date,
                      count(*) AS matched_rows,
                      min(id) AS sample_id
                    FROM trading_data.feed_03_alpaca_news
                    WHERE created_at >= %s
                      AND created_at < %s
                      AND (
                        lower(coalesce(timeline_headline, '')) ~ %s
                        OR lower(coalesce(summary, '')) ~ %s
                      )
                    GROUP BY created_at::date
                    ORDER BY matched_rows DESC, event_date
                    LIMIT %s
                    """,
                    (start.isoformat(), end_exclusive.isoformat(), pattern, pattern, max_dates_per_family),
                )
                alpaca_rows = cursor.fetchall()
                remaining = max(0, max_dates_per_family - len(alpaca_rows))
                cursor.execute(
                    """
                    SELECT
                      seen_at::date AS event_date,
                      count(*) AS matched_rows,
                      min(article_id) AS sample_article_id
                    FROM trading_data.feed_05_gdelt_article
                    WHERE seen_at >= %s
                      AND seen_at < %s
                      AND (
                        lower(coalesce(title, '')) ~ %s
                        OR lower(coalesce(source_theme_tags, '')) ~ %s
                      )
                    GROUP BY seen_at::date
                    ORDER BY matched_rows DESC, event_date
                    LIMIT %s
                    """,
                    (start.isoformat(), end_exclusive.isoformat(), pattern, pattern, remaining),
                )
                gdelt_rows = cursor.fetchall()
                dated_rows: list[tuple[date, str]] = [
                    (
                        row["event_date"],
                        _sql_source_ref("feed_03_alpaca_news", row["event_date"], int(row["matched_rows"]), row["sample_id"]),
                    )
                    for row in alpaca_rows
                ]
                existing_dates = {event_day for event_day, _source_ref in dated_rows}
                dated_rows.extend(
                    (
                        row["event_date"],
                        _sql_source_ref("feed_05_gdelt_article", row["event_date"], int(row["matched_rows"]), row["sample_article_id"]),
                    )
                    for row in gdelt_rows
                    if row["event_date"] not in existing_dates
                )
                for event_day, source_ref in dated_rows[:max_dates_per_family]:
                    rows.append(
                        {
                            "family_key": family,
                            "event_temporal_form": _temporal_form_for_family(family),
                            "event_date": event_day.isoformat(),
                            "event_ref": f"{family}_{event_day:%Y%m%d}",
                            "source_ref": source_ref,
                        }
                    )
    return sorted(rows, key=lambda row: (row["family_key"], row["event_date"], row["event_ref"]))


def daily_bars_from_sql(
    *,
    database_url: str,
    symbols: Sequence[str],
    start: date,
    end_exclusive: date,
) -> list[dict[str, Any]]:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                  symbol,
                  (timestamp AT TIME ZONE 'America/New_York')::date AS day,
                  (array_agg(bar_open ORDER BY timestamp))[1] AS open,
                  max(bar_high) AS high,
                  min(bar_low) AS low,
                  (array_agg(bar_close ORDER BY timestamp DESC))[1] AS close
                FROM trading_data.m01_market_regime_data_acquisition
                WHERE symbol = ANY(%s)
                  AND timeframe = '1Min'
                  AND timestamp >= %s
                  AND timestamp < %s
                GROUP BY symbol, day
                ORDER BY symbol, day
                """,
                (list(symbols), start.isoformat(), end_exclusive.isoformat()),
            )
            rows = cursor.fetchall()
    return [
        {
            "symbol": str(row["symbol"]),
            "date": row["day"].isoformat(),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
        }
        for row in rows
    ]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _counts_by_family(rows: Sequence[Mapping[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        family = str(row["family_key"])
        counts[family] = counts.get(family, 0) + 1
    return dict(sorted(counts.items()))


def build_real_input_backtest_artifacts(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    database_url: str | None = None,
    storage_secret_alias: str = DEFAULT_STORAGE_SECRET_ALIAS,
    source_root: Path | None = None,
    start_date: date = DEFAULT_START_DATE,
    end_date_exclusive: date = DEFAULT_END_DATE_EXCLUSIVE,
    symbols: Sequence[str] = DEFAULT_SYMBOLS,
    max_breaking_news_dates: int = 24,
) -> RealInputBuildResult:
    source_root = source_root or (data_storage_root() / "monthly_backfill")
    dsn = _database_url(database_url, secret_alias=storage_secret_alias)
    event_rows = [
        *cpi_events_from_trading_economics(source_root, start_date, end_date_exclusive),
        *triple_witching_events(start_date, end_date_exclusive),
        *breaking_news_events_from_sql(database_url=dsn, start=start_date, end_exclusive=end_date_exclusive, max_dates=max_breaking_news_dates),
    ]
    event_rows = sorted(event_rows, key=lambda row: (row["family_key"], row["event_date"], row["event_ref"]))
    min_bar_date = start_date - timedelta(days=14)
    max_bar_date = end_date_exclusive + timedelta(days=14)
    bar_rows = daily_bars_from_sql(database_url=dsn, symbols=tuple(symbols), start=min_bar_date, end_exclusive=max_bar_date)

    input_dir = output_dir / "inputs"
    event_csv = input_dir / "reviewed_event_instances.csv"
    bar_csv = input_dir / "point_in_time_price_bars.csv"
    _write_csv(event_csv, event_rows, EVENT_FIELDS)
    _write_csv(bar_csv, bar_rows, BAR_FIELDS)

    backtest_dir = output_dir / "backtest"
    backtest = build_real_input_event_family_impact_window_backtest(event_paths=(event_csv,), bar_paths=(bar_csv,))
    write_event_family_impact_window_backtest_artifacts(backtest, backtest_dir)

    result = RealInputBuildResult(
        event_csv=str(event_csv),
        bar_csv=str(bar_csv),
        backtest_output_dir=str(backtest_dir),
        summary_path=str(output_dir / "input_summary.json"),
        start_date=start_date.isoformat(),
        end_date_exclusive=end_date_exclusive.isoformat(),
        symbols=tuple(symbols),
        event_counts_by_family=_counts_by_family(event_rows),
        bar_rows=len(bar_rows),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "input_summary.json").write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def build_all_family_real_input_backtest_artifacts(
    *,
    output_dir: Path = DEFAULT_ALL_FAMILY_OUTPUT_DIR,
    database_url: str | None = None,
    storage_secret_alias: str = DEFAULT_STORAGE_SECRET_ALIAS,
    source_root: Path | None = None,
    start_date: date = DEFAULT_START_DATE,
    end_date_exclusive: date = DEFAULT_END_DATE_EXCLUSIVE,
    symbols: Sequence[str] = DEFAULT_SYMBOLS,
    max_dates_per_family: int = 80,
) -> RealInputBuildResult:
    source_root = source_root or (data_storage_root() / "monthly_backfill")
    dsn = _database_url(database_url, secret_alias=storage_secret_alias)
    sql_rows = family_candidate_events_from_sql(
        database_url=dsn,
        start=start_date,
        end_exclusive=end_date_exclusive,
        max_dates_per_family=max_dates_per_family,
    )
    keyed = {(row["family_key"], row["event_date"]): dict(row) for row in sql_rows}
    for row in cpi_events_from_trading_economics(source_root, start_date, end_date_exclusive):
        keyed[(row["family_key"], row["event_date"])] = row
    for row in triple_witching_events(start_date, end_date_exclusive):
        keyed[(row["family_key"], row["event_date"])] = row
    event_rows = sorted(keyed.values(), key=lambda row: (row["family_key"], row["event_date"], row["event_ref"]))

    min_bar_date = start_date - timedelta(days=14)
    max_bar_date = end_date_exclusive + timedelta(days=14)
    bar_rows = daily_bars_from_sql(database_url=dsn, symbols=tuple(symbols), start=min_bar_date, end_exclusive=max_bar_date)

    input_dir = output_dir / "inputs"
    event_csv = input_dir / "reviewed_event_instances.csv"
    bar_csv = input_dir / "point_in_time_price_bars.csv"
    _write_csv(event_csv, event_rows, EVENT_FIELDS)
    _write_csv(bar_csv, bar_rows, BAR_FIELDS)

    backtest_dir = output_dir / "backtest"
    backtest = build_real_input_event_family_impact_window_backtest(event_paths=(event_csv,), bar_paths=(bar_csv,))
    write_event_family_impact_window_backtest_artifacts(backtest, backtest_dir)

    result = RealInputBuildResult(
        event_csv=str(event_csv),
        bar_csv=str(bar_csv),
        backtest_output_dir=str(backtest_dir),
        summary_path=str(output_dir / "input_summary.json"),
        start_date=start_date.isoformat(),
        end_date_exclusive=end_date_exclusive.isoformat(),
        symbols=tuple(symbols),
        event_counts_by_family=_counts_by_family(event_rows),
        bar_rows=len(bar_rows),
        review_status="fold_calibration_complete_requires_cross_fold_and_promotion_review",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "input_summary.json").write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = [
    "DEFAULT_ALL_FAMILY_OUTPUT_DIR",
    "DEFAULT_OUTPUT_DIR",
    "RealInputBuildResult",
    "build_all_family_real_input_backtest_artifacts",
    "build_real_input_backtest_artifacts",
    "cpi_events_from_trading_economics",
    "daily_bars_from_sql",
    "breaking_news_events_from_sql",
    "family_candidate_events_from_sql",
    "triple_witching_events",
]
