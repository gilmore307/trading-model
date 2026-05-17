"""Reverse price-anomaly to event-family discovery for EventRiskGovernor.

Starts from local price anomalies, then checks nearby local event artifacts for
common event-family enrichment. This is discovery/evidence triage only: no
provider calls, training, activation, broker/account mutation, destructive SQL,
or artifact deletion.
"""
from __future__ import annotations

import csv
import glob
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence, TextIO

from models.model_09_event_risk_governor.event_family_empirical_coverage import FAMILY_KEYWORDS

CONTRACT_TYPE = "price_anomaly_event_discovery_v1"
SUMMARY_CONTRACT_TYPE = "price_anomaly_event_discovery_summary_v1"
DEFAULT_TRADING_DATA_ROOT = Path("/root/projects/trading-data")
DEFAULT_BAR_ROOT = DEFAULT_TRADING_DATA_ROOT / "storage/monthly_backfill_v1/alpaca_bars"
DEFAULT_SOURCE_ROOT = DEFAULT_TRADING_DATA_ROOT / "storage/monthly_backfill_v1"
DEFAULT_OUTPUT_DIR = Path("storage/price_anomaly_event_discovery_20260516")
EVENT_MONTH = "2016-01"
ANOMALY_Z_THRESHOLD = 1.25
EVENT_WINDOW_DAYS = 1


@dataclass(frozen=True)
class DailyPoint:
    symbol: str
    day: date
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class PriceAnomalyRow:
    symbol: str
    day: str
    return_1d: float
    abs_return_1d: float
    path_range_1d: float
    abs_return_z: float
    path_range_z: float
    anomaly_reason: str
    nearby_event_families: tuple[str, ...]
    nearby_event_sources: tuple[str, ...]

    def csv_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in asdict(self).items():
            if isinstance(value, tuple):
                out[key] = ";".join(value)
            else:
                out[key] = str(value)
        return out


@dataclass(frozen=True)
class EventFamilyEnrichmentRow:
    family_key: str
    anomaly_hit_count: int
    anomaly_observation_count: int
    anomaly_hit_rate: float
    control_hit_count: int
    control_observation_count: int
    control_hit_rate: float
    hit_rate_delta: float
    lift: float | None
    threshold_discovery_status: str
    evidence_note: str

    def csv_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in asdict(self).items():
            out[key] = "" if value is None else str(value)
        return out


@dataclass(frozen=True)
class PriceAnomalyEventDiscovery:
    contract_type: str
    generated_at_utc: str
    price_month: str
    anomaly_z_threshold: float
    event_window_days: int
    anomaly_rows: tuple[PriceAnomalyRow, ...]
    enrichment_rows: tuple[EventFamilyEnrichmentRow, ...]
    provider_calls: int = 0
    model_training_performed: bool = False
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "contract_type": SUMMARY_CONTRACT_TYPE,
            "generated_at_utc": self.generated_at_utc,
            "price_month": self.price_month,
            "anomaly_z_threshold": self.anomaly_z_threshold,
            "event_window_days": self.event_window_days,
            "anomaly_count": len(self.anomaly_rows),
            "symbol_count": len({row.symbol for row in self.anomaly_rows}),
            "enriched_family_count": len(self.enrichment_rows),
            "candidate_common_event_families": [
                row.family_key for row in self.enrichment_rows if row.threshold_discovery_status == "reverse_discovery_candidate"
            ],
            "high_lift_thin_families": [
                row.family_key for row in self.enrichment_rows if row.threshold_discovery_status == "thin_high_lift_review"
            ],
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
            "discovery_note": "Reverse discovery starts from local price anomalies, then checks nearby local event-family mentions. It is not causal proof or model approval.",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "price_month": self.price_month,
            "anomaly_z_threshold": self.anomaly_z_threshold,
            "event_window_days": self.event_window_days,
            "anomaly_rows": [asdict(row) for row in self.anomaly_rows],
            "enrichment_rows": [asdict(row) for row in self.enrichment_rows],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def _text(row: Mapping[str, str], fields: Sequence[str]) -> str:
    return " ".join(str(row.get(field) or "") for field in fields).lower()


def _keyword_match(text: str, keywords: Sequence[str]) -> bool:
    return any(re.search(re.escape(keyword.lower()), text) for keyword in keywords)


def _read_csv_rows(pattern: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8", newline="") as handle:
            rows.extend(dict(row) for row in csv.DictReader(handle))
    return rows


def _load_daily_points(bar_root: Path, month: str) -> dict[str, list[DailyPoint]]:
    result: dict[str, list[DailyPoint]] = {}
    for symbol_dir in sorted(path for path in bar_root.iterdir() if path.is_dir()):
        symbol = symbol_dir.name
        by_day: dict[date, list[tuple[datetime, float, float, float, float]]] = defaultdict(list)
        for path in glob.glob(str(symbol_dir / month / "runs/*/saved/equity_bar.csv")):
            with open(path, encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    dt = _parse_dt(row.get("timestamp", ""))
                    values = [_parse_float(row.get(key, "")) for key in ("bar_open", "bar_high", "bar_low", "bar_close")]
                    if not dt or any(value is None for value in values) or dt.strftime("%Y-%m") != month:
                        continue
                    opn, high, low, close = values
                    by_day[dt.date()].append((dt, opn or 0.0, high or 0.0, low or 0.0, close or 0.0))
        points: list[DailyPoint] = []
        for day, rows in sorted(by_day.items()):
            rows = sorted(rows, key=lambda item: item[0])
            points.append(DailyPoint(symbol, day, rows[0][1], max(row[2] for row in rows), min(row[3] for row in rows), rows[-1][4]))
        if len(points) >= 5:
            result[symbol] = points
    return result


def _event_family_dates(source_root: Path) -> dict[date, dict[str, set[str]]]:
    by_day: dict[date, dict[str, set[str]]] = defaultdict(lambda: {"families": set(), "sources": set()})
    source_specs = [
        (
            "alpaca_news",
            _read_csv_rows(str(source_root / "alpaca_news/*/runs/*/saved/equity_news.csv")),
            "created_at",
            ("timeline_headline", "summary"),
        ),
        (
            "gdelt_news",
            _read_csv_rows(str(source_root / "gdelt_news/*/runs/*/saved/gdelt_article.csv")),
            "seen_at",
            ("title", "source_theme_tags", "organizations", "persons", "locations"),
        ),
        (
            "trading_economics_calendar_web",
            _read_csv_rows(str(source_root / "trading_economics_calendar_web/*/runs/*/saved/trading_economics_calendar_event.csv")),
            "event_time",
            ("event", "source_event_type"),
        ),
    ]
    for source_name, rows, dt_field, fields in source_specs:
        for row in rows:
            dt = _parse_dt(row.get(dt_field, ""))
            if not dt:
                continue
            text = _text(row, fields)
            for family, keywords in FAMILY_KEYWORDS.items():
                if _keyword_match(text, keywords):
                    by_day[dt.date()]["families"].add(family)
                    by_day[dt.date()]["sources"].add(source_name)
    return by_day


def _daily_observations(points_by_symbol: Mapping[str, Sequence[DailyPoint]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for symbol, points in points_by_symbol.items():
        metrics: list[dict[str, Any]] = []
        for prev, current in zip(points, points[1:]):
            if prev.close <= 0:
                continue
            ret = current.close / prev.close - 1.0
            path = (current.high - current.low) / prev.close
            metrics.append({"symbol": symbol, "day": current.day, "ret": ret, "abs_ret": abs(ret), "path": path})
        if not metrics:
            continue
        abs_values = [row["abs_ret"] for row in metrics]
        path_values = [row["path"] for row in metrics]
        abs_mean = mean(abs_values)
        path_mean = mean(path_values)
        abs_std = pstdev(abs_values) or 1.0
        path_std = pstdev(path_values) or 1.0
        for row in metrics:
            row["abs_z"] = (row["abs_ret"] - abs_mean) / abs_std
            row["path_z"] = (row["path"] - path_mean) / path_std
            observations.append(row)
    return observations


def _nearby(day: date, event_dates: Mapping[date, Mapping[str, set[str]]], window_days: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    families: set[str] = set()
    sources: set[str] = set()
    for offset in range(-window_days, window_days + 1):
        event = event_dates.get(day + timedelta(days=offset))
        if not event:
            continue
        families.update(event["families"])
        sources.update(event["sources"])
    return tuple(sorted(families)), tuple(sorted(sources))


def _classify_enrichment(anomaly_hits: int, anomaly_n: int, control_hits: int, control_n: int) -> tuple[str, str]:
    anomaly_rate = anomaly_hits / anomaly_n if anomaly_n else 0.0
    control_rate = control_hits / control_n if control_n else 0.0
    lift = (anomaly_rate / control_rate) if control_rate > 0 else None
    delta = anomaly_rate - control_rate
    if anomaly_hits >= 20 and delta >= 0.10 and (lift is None or lift >= 1.5):
        return "reverse_discovery_candidate", "Event family is materially enriched around price anomalies versus non-anomaly observations; requires canonical family review before causal use."
    if anomaly_hits >= 5 and delta > 0 and lift is not None and lift >= 2.0:
        return "thin_high_lift_review", "High lift but thin hit count; review only after more data."
    return "not_enriched_or_too_thin", "No robust reverse-discovery enrichment under this local screen."


def build_price_anomaly_event_discovery(
    *,
    bar_root: Path = DEFAULT_BAR_ROOT,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    month: str = EVENT_MONTH,
    anomaly_z_threshold: float = ANOMALY_Z_THRESHOLD,
    event_window_days: int = EVENT_WINDOW_DAYS,
    generated_at_utc: str | None = None,
) -> PriceAnomalyEventDiscovery:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    points_by_symbol = _load_daily_points(bar_root, month)
    event_dates = _event_family_dates(source_root)
    observations = _daily_observations(points_by_symbol)
    anomaly_rows: list[PriceAnomalyRow] = []
    family_anomaly_hits: dict[str, int] = defaultdict(int)
    family_control_hits: dict[str, int] = defaultdict(int)
    anomaly_n = 0
    control_n = 0
    for obs in observations:
        is_anomaly = obs["abs_z"] >= anomaly_z_threshold or obs["path_z"] >= anomaly_z_threshold
        families, sources = _nearby(obs["day"], event_dates, event_window_days)
        if is_anomaly:
            anomaly_n += 1
            for family in families:
                family_anomaly_hits[family] += 1
            reasons = []
            if obs["abs_z"] >= anomaly_z_threshold:
                reasons.append("abs_return_z")
            if obs["path_z"] >= anomaly_z_threshold:
                reasons.append("path_range_z")
            anomaly_rows.append(
                PriceAnomalyRow(
                    symbol=str(obs["symbol"]),
                    day=obs["day"].isoformat(),
                    return_1d=float(obs["ret"]),
                    abs_return_1d=float(obs["abs_ret"]),
                    path_range_1d=float(obs["path"]),
                    abs_return_z=float(obs["abs_z"]),
                    path_range_z=float(obs["path_z"]),
                    anomaly_reason=";".join(reasons),
                    nearby_event_families=families,
                    nearby_event_sources=sources,
                )
            )
        else:
            control_n += 1
            for family in families:
                family_control_hits[family] += 1
    enrichment_rows: list[EventFamilyEnrichmentRow] = []
    for family in sorted(set(family_anomaly_hits) | set(family_control_hits)):
        ah = family_anomaly_hits[family]
        ch = family_control_hits[family]
        ar = ah / anomaly_n if anomaly_n else 0.0
        cr = ch / control_n if control_n else 0.0
        lift = ar / cr if cr > 0 else None
        status, note = _classify_enrichment(ah, anomaly_n, ch, control_n)
        enrichment_rows.append(
            EventFamilyEnrichmentRow(
                family_key=family,
                anomaly_hit_count=ah,
                anomaly_observation_count=anomaly_n,
                anomaly_hit_rate=ar,
                control_hit_count=ch,
                control_observation_count=control_n,
                control_hit_rate=cr,
                hit_rate_delta=ar - cr,
                lift=lift,
                threshold_discovery_status=status,
                evidence_note=note,
            )
        )
    enrichment_rows.sort(key=lambda row: (row.threshold_discovery_status != "reverse_discovery_candidate", -(row.hit_rate_delta), row.family_key))
    return PriceAnomalyEventDiscovery(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        price_month=month,
        anomaly_z_threshold=anomaly_z_threshold,
        event_window_days=event_window_days,
        anomaly_rows=tuple(anomaly_rows),
        enrichment_rows=tuple(enrichment_rows),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_price_anomaly_event_discovery_artifacts(discovery: PriceAnomalyEventDiscovery, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "price_anomaly_event_discovery.json").write_text(
        json.dumps(discovery.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "price_anomaly_event_discovery_summary.json").write_text(
        json.dumps(discovery.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    anomaly_fields = list(PriceAnomalyRow("", "", 0, 0, 0, 0, 0, "", (), ()).csv_row().keys())
    enrichment_fields = list(EventFamilyEnrichmentRow("", 0, 0, 0, 0, 0, 0, 0, None, "", "").csv_row().keys())
    _write_csv(output_dir / "price_anomaly_events.csv", [row.csv_row() for row in discovery.anomaly_rows], fieldnames=anomaly_fields)
    _write_csv(output_dir / "price_anomaly_event_family_enrichment.csv", [row.csv_row() for row in discovery.enrichment_rows], fieldnames=enrichment_fields)
    (output_dir / "README.md").write_text(
        f"""# Price anomaly event discovery

Contract: `{discovery.contract_type}`

This artifact reverses the prior direction: it starts from local price anomalies, then scans nearby event-family mentions for commonality/enrichment. It is discovery evidence only and does not prove causality, train models, activate models, call providers, mutate broker/account state, run destructive SQL, or delete artifacts.
""",
        encoding="utf-8",
    )


def write_discovery(discovery: PriceAnomalyEventDiscovery, *, output: TextIO) -> None:
    json.dump(discovery.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "PriceAnomalyEventDiscovery",
    "PriceAnomalyRow",
    "EventFamilyEnrichmentRow",
    "build_price_anomaly_event_discovery",
    "write_price_anomaly_event_discovery_artifacts",
    "write_discovery",
]
