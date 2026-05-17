"""Local all-family event/price association measurement for EventRiskGovernor.

No provider calls, training, activation, broker/account mutation, destructive SQL, or
artifact deletion. Families without measurable local events are still emitted with
an explicit data-gap status so the final answer distinguishes no measured
association from no usable local evidence.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence, TextIO
import glob

from models.model_08_event_risk_governor.event_family_empirical_coverage import FAMILY_KEYWORDS

CONTRACT_TYPE = "event_family_all_association_v1"
SUMMARY_CONTRACT_TYPE = "event_family_all_association_summary_v1"
DEFAULT_COVERAGE_PATH = Path("storage/event_family_empirical_coverage_20260516/event_family_empirical_coverage.json")
DEFAULT_OUTPUT_DIR = Path("storage/event_family_all_association_20260516")
DEFAULT_TRADING_DATA_ROOT = Path("/root/projects/trading-data")
DEFAULT_BAR_ROOT = DEFAULT_TRADING_DATA_ROOT / "storage/monthly_backfill_v1/alpaca_bars"
DEFAULT_SOURCE_ROOT = DEFAULT_TRADING_DATA_ROOT / "storage/monthly_backfill_v1"
DEFAULT_PROXY_SYMBOLS = ("SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLY", "XLP", "XLI", "XLB", "HYG", "LQD")
EVENT_MONTH = "2016-01"

SPECIAL_PREVIOUS_STUDIES: dict[str, dict[str, Any]] = {
    "cpi_inflation_release": {
        "measurement_status": "measured_prior_study_positive_risk_association",
        "association_class": "risk_volatility_association_not_directional_alpha",
        "event_count": 101,
        "label_count": 396,
        "path_range_delta_1d": 0.00464557910991581,
        "abs_return_delta_1d": 0.001488352573286246,
        "return_delta_1d": -0.0038905238244364387,
        "directional_alpha_supported": False,
        "risk_control_supported": True,
        "evidence_note": "Prior CPI surprise study: large actual-vs-forecast/consensus surprises show event-day path/absolute-return expansion and weak conditional risk-off pressure.",
    },
    "earnings_guidance_scheduled_shell": {
        "measurement_status": "measured_prior_study_positive_path_risk_association",
        "association_class": "scheduled_path_risk_association_not_directional_alpha",
        "event_count": 12,
        "label_count": 12,
        "path_range_delta_5d": 0.027598893341921987,
        "return_delta_5d": -0.016930887875746207,
        "directional_alpha_supported": False,
        "risk_control_supported": True,
        "evidence_note": "Prior earnings-shell study: scheduled windows showed elevated 5d path range but unstable/negative direction.",
    },
    "option_derivatives_abnormality": {
        "measurement_status": "measured_prior_study_low_signal",
        "association_class": "current_definition_no_accepted_association",
        "event_count": 152,
        "label_count": 152,
        "path_range_delta_5d": 0.015196242582327461,
        "return_delta_5d": -0.012699997492658266,
        "directional_alpha_supported": False,
        "risk_control_supported": False,
        "evidence_note": "Prior option matched-control work found the current abnormality definition noisy/saturated; not accepted for event association use.",
    },
}


@dataclass(frozen=True)
class DailyBar:
    symbol: str
    day: date
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class FamilyAssociationRow:
    family_key: str
    measurement_status: str
    association_class: str
    event_count: int
    label_count_1d: int
    label_count_5d: int
    label_count_10d: int
    event_dates: tuple[str, ...]
    source_routes: tuple[str, ...]
    return_delta_1d: float | None
    abs_return_delta_1d: float | None
    path_range_delta_1d: float | None
    return_delta_5d: float | None
    abs_return_delta_5d: float | None
    path_range_delta_5d: float | None
    return_delta_10d: float | None
    abs_return_delta_10d: float | None
    path_range_delta_10d: float | None
    directional_alpha_supported: bool
    risk_control_supported: bool
    evidence_note: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        row = self.to_row()
        out: dict[str, str] = {}
        for key, value in row.items():
            if isinstance(value, tuple):
                out[key] = ";".join(value)
            elif value is None:
                out[key] = ""
            else:
                out[key] = str(value)
        return out


@dataclass(frozen=True)
class EventFamilyAllAssociation:
    contract_type: str
    generated_at_utc: str
    source_coverage_path: str
    family_rows: tuple[FamilyAssociationRow, ...]
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
            "family_count": len(self.family_rows),
            "local_screening_universe": {
                "bar_root": str(DEFAULT_BAR_ROOT),
                "event_source_root": str(DEFAULT_SOURCE_ROOT),
                "screening_month": EVENT_MONTH,
                "available_bar_symbol_count": len(_discover_symbols(DEFAULT_BAR_ROOT)),
                "available_bar_symbols": list(_discover_symbols(DEFAULT_BAR_ROOT)),
                "note": "Local keyword/proxy screening uses every available symbol under the local bar root for the screening month; accepted prior CPI/earnings/option studies retain their reviewed source universes.",
            },
            "measurement_status_counts": _counts(row.measurement_status for row in self.family_rows),
            "association_class_counts": _counts(row.association_class for row in self.family_rows),
            "screening_stability_counts": _counts(row["screening_stability_status"] for row in _stability_rows(self.family_rows)),
            "risk_control_supported_families": [row.family_key for row in self.family_rows if row.risk_control_supported],
            "directional_alpha_supported_families": [row.family_key for row in self.family_rows if row.directional_alpha_supported],
            "families_with_measured_event_labels": [row.family_key for row in self.family_rows if row.label_count_1d or row.label_count_5d or row.label_count_10d],
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
            "final_measurement_note": "All 29 families emitted. Measured association is separated from no-local-event/data-gap statuses.",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "source_coverage_path": self.source_coverage_path,
            "family_rows": [row.to_row() for row in self.family_rows],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return dict(sorted(counts.items()))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(pattern: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8", newline="") as handle:
            rows.extend(dict(row) for row in csv.DictReader(handle))
    return rows


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    try:
        out = float(value)
        if math.isfinite(out):
            return out
    except (TypeError, ValueError):
        return None
    return None


def _text(row: Mapping[str, str], fields: Sequence[str]) -> str:
    return " ".join(str(row.get(field) or "") for field in fields).lower()


def _keyword_match(text: str, keywords: Sequence[str]) -> bool:
    return any(re.search(re.escape(keyword.lower()), text) for keyword in keywords)


def _load_sources(source_root: Path) -> dict[str, list[dict[str, str]]]:
    te_rows = _read_csv_rows(str(source_root / "trading_economics_calendar_web/*/runs/*/saved/trading_economics_calendar_event.csv"))
    return {
        "alpaca_news": _read_csv_rows(str(source_root / "alpaca_news/*/runs/*/saved/equity_news.csv")),
        "gdelt_news": _read_csv_rows(str(source_root / "gdelt_news/*/runs/*/saved/gdelt_article.csv")),
        "trading_economics_calendar_web": [row for row in te_rows if re.match(r"^\d{4}-\d{2}-\d{2}T", row.get("event_time") or "")],
        "sec_company_financials": _read_csv_rows(str(source_root / "sec_company_financials/*/runs/*/saved/sec_company_fact.csv")),
    }


def _candidate_dates_for_family(family: str, sources: Mapping[str, list[dict[str, str]]]) -> tuple[tuple[date, str], ...]:
    keywords = FAMILY_KEYWORDS.get(family, ())
    out: list[tuple[date, str]] = []
    if family in {"cpi_inflation_release", "fomc_rates_policy", "nfp_employment_release"}:
        for row in sources["trading_economics_calendar_web"]:
            dt = _parse_dt(row.get("event_time", ""))
            if dt and _keyword_match(_text(row, ("event", "source_event_type")), keywords):
                out.append((dt.date(), "trading_economics_calendar_web"))
    if family in {"treasury_yield_curve_shock", "credit_liquidity_stress", "geopolitical_or_fiscal_shock"}:
        for row in sources["gdelt_news"]:
            dt = _parse_dt(row.get("seen_at", ""))
            if dt and _keyword_match(_text(row, ("title", "source_theme_tags", "organizations", "locations")), keywords):
                out.append((dt.date(), "gdelt_news"))
    if family not in {"cpi_inflation_release", "fomc_rates_policy", "nfp_employment_release", "treasury_yield_curve_shock", "credit_liquidity_stress", "geopolitical_or_fiscal_shock"}:
        for row in sources["alpaca_news"]:
            dt = _parse_dt(row.get("created_at", ""))
            if dt and _keyword_match(_text(row, ("timeline_headline", "summary")), keywords):
                out.append((dt.date(), "alpaca_news"))
        for row in sources["gdelt_news"]:
            dt = _parse_dt(row.get("seen_at", ""))
            if dt and _keyword_match(_text(row, ("title", "source_theme_tags", "organizations", "persons", "locations")), keywords):
                out.append((dt.date(), "gdelt_news"))
    # Unique by date/source to avoid headline saturation dominating date-level tests.
    return tuple(sorted(set(out), key=lambda item: (item[0], item[1])))


def _discover_symbols(bar_root: Path) -> tuple[str, ...]:
    symbols = tuple(sorted(path.name for path in bar_root.iterdir() if path.is_dir())) if bar_root.exists() else ()
    return symbols or DEFAULT_PROXY_SYMBOLS


def _load_daily_bars(bar_root: Path, symbols: Sequence[str] | None = None, month: str = EVENT_MONTH) -> dict[str, list[DailyBar]]:
    symbols = tuple(symbols or _discover_symbols(bar_root))
    by_symbol: dict[str, dict[date, list[tuple[datetime, float, float, float, float]]]] = {symbol: defaultdict(list) for symbol in symbols}
    for symbol in symbols:
        for path in glob.glob(str(bar_root / symbol / month / "runs/*/saved/equity_bar.csv")):
            with open(path, encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    dt = _parse_dt(row.get("timestamp", ""))
                    values = [_parse_float(row.get(key, "")) for key in ("bar_open", "bar_high", "bar_low", "bar_close")]
                    if not dt or any(value is None for value in values):
                        continue
                    if dt.strftime("%Y-%m") != month:
                        continue
                    opn, high, low, close = values
                    by_symbol[symbol][dt.date()].append((dt, opn or 0.0, high or 0.0, low or 0.0, close or 0.0))
    result: dict[str, list[DailyBar]] = {}
    for symbol, day_rows in by_symbol.items():
        bars: list[DailyBar] = []
        for day, rows in sorted(day_rows.items()):
            rows = sorted(rows, key=lambda item: item[0])
            bars.append(DailyBar(symbol=symbol, day=day, open=rows[0][1], high=max(row[2] for row in rows), low=min(row[3] for row in rows), close=rows[-1][4]))
        if bars:
            result[symbol] = bars
    return result


def _labels_for_dates(event_dates: set[date], bars_by_symbol: Mapping[str, list[DailyBar]], horizon: int) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    event_labels: list[dict[str, float]] = []
    control_labels: list[dict[str, float]] = []
    for symbol, bars in bars_by_symbol.items():
        for idx, bar in enumerate(bars):
            if idx + horizon >= len(bars):
                continue
            future = bars[idx + horizon]
            window = bars[idx : idx + horizon + 1]
            if bar.close <= 0:
                continue
            label = {
                "ret": future.close / bar.close - 1.0,
                "abs_ret": abs(future.close / bar.close - 1.0),
                "path_range": (max(item.high for item in window) - min(item.low for item in window)) / bar.close,
            }
            if bar.day in event_dates:
                event_labels.append(label)
            else:
                control_labels.append(label)
    return event_labels, control_labels


def _mean_delta(event_labels: Sequence[Mapping[str, float]], control_labels: Sequence[Mapping[str, float]], field: str) -> float | None:
    if not event_labels or not control_labels:
        return None
    return mean(label[field] for label in event_labels) - mean(label[field] for label in control_labels)


def _classify(row: Mapping[str, Any]) -> tuple[str, str, bool, bool, str]:
    n = int(row["label_count_1d"])
    p1 = row["path_range_delta_1d"]
    a1 = row["abs_return_delta_1d"]
    r1 = row["return_delta_1d"]
    p5 = row["path_range_delta_5d"]
    r5 = row["return_delta_5d"]
    if n == 0:
        return "not_measurable_no_local_event_labels", "not_measured_data_gap", False, False, "No local dated candidate events with aligned proxy bars."
    risk = any(value is not None and value > 0.0025 for value in (p1, a1, p5))
    directional = any(value is not None and abs(value) > 0.015 for value in (r1, r5)) and n >= 24
    if risk and not directional:
        return "measured_local_screening_risk_association", "local_screening_risk_association_unaccepted", False, False, "Local dated candidates show path/absolute-return expansion versus same-month controls, but this is a screening result only and is not accepted for model use."
    if directional:
        return "measured_local_directional_candidate_unreviewed", "local_directional_candidate_unaccepted", False, False, "Local directional delta is large enough to require review, but sample/control/source quality is insufficient for alpha support."
    return "measured_local_no_clear_association", "no_clear_local_association", False, False, "Local dated candidates did not show a clear path-risk or directional delta versus same-month controls."


def _local_association_row(family: str, coverage_row: Mapping[str, Any], sources: Mapping[str, list[dict[str, str]]], bars_by_symbol: Mapping[str, list[DailyBar]]) -> FamilyAssociationRow:
    candidates = _candidate_dates_for_family(family, sources)
    event_dates = {day for day, _source in candidates}
    routes = tuple(sorted({source for _day, source in candidates}))
    labels: dict[int, tuple[list[dict[str, float]], list[dict[str, float]]]] = {
        horizon: _labels_for_dates(event_dates, bars_by_symbol, horizon) for horizon in (1, 5, 10)
    }
    data: dict[str, Any] = {
        "label_count_1d": len(labels[1][0]),
        "label_count_5d": len(labels[5][0]),
        "label_count_10d": len(labels[10][0]),
        "return_delta_1d": _mean_delta(*labels[1], "ret"),
        "abs_return_delta_1d": _mean_delta(*labels[1], "abs_ret"),
        "path_range_delta_1d": _mean_delta(*labels[1], "path_range"),
        "return_delta_5d": _mean_delta(*labels[5], "ret"),
        "abs_return_delta_5d": _mean_delta(*labels[5], "abs_ret"),
        "path_range_delta_5d": _mean_delta(*labels[5], "path_range"),
        "return_delta_10d": _mean_delta(*labels[10], "ret"),
        "abs_return_delta_10d": _mean_delta(*labels[10], "abs_ret"),
        "path_range_delta_10d": _mean_delta(*labels[10], "path_range"),
    }
    status, assoc_class, directional, risk, note = _classify(data)
    # Do not override hard blockers: local keyword coincidences are not valid measurements for families requiring a dedicated detector/baseline.
    blockers = set(coverage_row.get("remaining_blocker_codes") or [])
    if blockers & {"pit_expectation_or_comparable_baseline_required", "residual_over_base_state_required", "liquidity_depth_evidence_required"}:
        status = "not_measurable_blocked_precondition"
        assoc_class = "not_measured_required_precondition_missing"
        directional = False
        risk = False
        note = "Candidate/date scan is not accepted because the family-specific baseline, residual detector, or liquidity-depth route is missing."
    return FamilyAssociationRow(
        family_key=family,
        measurement_status=status,
        association_class=assoc_class,
        event_count=len(event_dates),
        label_count_1d=data["label_count_1d"],
        label_count_5d=data["label_count_5d"],
        label_count_10d=data["label_count_10d"],
        event_dates=tuple(day.isoformat() for day in sorted(event_dates)),
        source_routes=routes,
        return_delta_1d=data["return_delta_1d"],
        abs_return_delta_1d=data["abs_return_delta_1d"],
        path_range_delta_1d=data["path_range_delta_1d"],
        return_delta_5d=data["return_delta_5d"],
        abs_return_delta_5d=data["abs_return_delta_5d"],
        path_range_delta_5d=data["path_range_delta_5d"],
        return_delta_10d=data["return_delta_10d"],
        abs_return_delta_10d=data["abs_return_delta_10d"],
        path_range_delta_10d=data["path_range_delta_10d"],
        directional_alpha_supported=directional,
        risk_control_supported=risk,
        evidence_note=note,
    )


def _numeric(value: float | None) -> float | None:
    return value if value is not None and math.isfinite(value) else None


def _stability_rows(rows: Sequence[FamilyAssociationRow]) -> list[dict[str, Any]]:
    stability_rows: list[dict[str, Any]] = []
    available_symbol_count = len(_discover_symbols(DEFAULT_BAR_ROOT))
    for row in rows:
        risk_values = [
            _numeric(row.abs_return_delta_1d),
            _numeric(row.path_range_delta_1d),
            _numeric(row.abs_return_delta_5d),
            _numeric(row.path_range_delta_5d),
            _numeric(row.abs_return_delta_10d),
            _numeric(row.path_range_delta_10d),
        ]
        risk_positive_count = sum(1 for value in risk_values if value is not None and value > 0)
        risk_material_count = sum(1 for value in risk_values if value is not None and value > 0.0025)
        return_values = [_numeric(row.return_delta_1d), _numeric(row.return_delta_5d), _numeric(row.return_delta_10d)]
        positive_direction_count = sum(1 for value in return_values if value is not None and value > 0)
        negative_direction_count = sum(1 for value in return_values if value is not None and value < 0)
        label_counts = [row.label_count_1d, row.label_count_5d, row.label_count_10d]
        measured_horizon_count = sum(1 for value in label_counts if value > 0)
        max_label_count = max(label_counts) if label_counts else 0
        if row.risk_control_supported:
            stability_status = "accepted_risk_control_prior_study"
        elif row.association_class == "current_definition_no_accepted_association":
            stability_status = "definition_revision_required"
        elif row.association_class.startswith("not_measured"):
            stability_status = "not_threshold_ready_precondition_or_data_gap"
        elif row.association_class == "no_clear_local_association":
            stability_status = "measured_no_clear_local_stability"
        elif row.event_count >= 5 and max_label_count >= 50 and measured_horizon_count >= 2:
            stability_status = "expanded_screening_threshold_review_candidate"
        else:
            stability_status = "thin_unstable_screening"
        stability_rows.append(
            {
                "family_key": row.family_key,
                "association_class": row.association_class,
                "screening_stability_status": stability_status,
                "available_symbol_count": available_symbol_count,
                "event_count": row.event_count,
                "measured_horizon_count": measured_horizon_count,
                "max_label_count": max_label_count,
                "risk_positive_metric_count": risk_positive_count,
                "risk_material_metric_count": risk_material_count,
                "positive_direction_horizon_count": positive_direction_count,
                "negative_direction_horizon_count": negative_direction_count,
                "threshold_grading_ready": str(stability_status in {"accepted_risk_control_prior_study", "expanded_screening_threshold_review_candidate"}).lower(),
                "note": "Preparation-only stability screen; thresholds and grades are not assigned in this artifact.",
            }
        )
    return stability_rows


def _special_row(family: str, data: Mapping[str, Any]) -> FamilyAssociationRow:
    return FamilyAssociationRow(
        family_key=family,
        measurement_status=str(data["measurement_status"]),
        association_class=str(data["association_class"]),
        event_count=int(data["event_count"]),
        label_count_1d=int(data.get("label_count", 0)),
        label_count_5d=int(data.get("label_count", 0)),
        label_count_10d=0,
        event_dates=(),
        source_routes=("prior_reviewed_artifact",),
        return_delta_1d=data.get("return_delta_1d"),
        abs_return_delta_1d=data.get("abs_return_delta_1d"),
        path_range_delta_1d=data.get("path_range_delta_1d"),
        return_delta_5d=data.get("return_delta_5d"),
        abs_return_delta_5d=data.get("abs_return_delta_5d"),
        path_range_delta_5d=data.get("path_range_delta_5d"),
        return_delta_10d=None,
        abs_return_delta_10d=None,
        path_range_delta_10d=None,
        directional_alpha_supported=bool(data["directional_alpha_supported"]),
        risk_control_supported=bool(data["risk_control_supported"]),
        evidence_note=str(data["evidence_note"]),
    )


def build_event_family_all_association(
    *,
    coverage_path: Path = DEFAULT_COVERAGE_PATH,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    bar_root: Path = DEFAULT_BAR_ROOT,
    generated_at_utc: str | None = None,
) -> EventFamilyAllAssociation:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    coverage = _read_json(coverage_path)
    sources = _load_sources(source_root)
    bars_by_symbol = _load_daily_bars(bar_root)
    rows: list[FamilyAssociationRow] = []
    for coverage_row in coverage.get("family_rows", []):
        family = str(coverage_row.get("family_key") or "")
        if family in SPECIAL_PREVIOUS_STUDIES:
            rows.append(_special_row(family, SPECIAL_PREVIOUS_STUDIES[family]))
        else:
            rows.append(_local_association_row(family, coverage_row, sources, bars_by_symbol))
    return EventFamilyAllAssociation(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        source_coverage_path=str(coverage_path),
        family_rows=tuple(rows),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_event_family_all_association_artifacts(association: EventFamilyAllAssociation, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_family_all_association.json").write_text(
        json.dumps(association.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_family_all_association_summary.json").write_text(
        json.dumps(association.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = list(FamilyAssociationRow("", "", "", 0, 0, 0, 0, (), (), None, None, None, None, None, None, None, None, None, False, False, "").csv_row().keys())
    _write_csv(output_dir / "event_family_all_association.csv", [row.csv_row() for row in association.family_rows], fieldnames=fields)
    _write_csv(output_dir / "event_family_expanded_stability.csv", _stability_rows(association.family_rows))
    (output_dir / "README.md").write_text(
        f"""# Event-family all-association measurement

Contract: `{association.contract_type}`

This artifact emits an association row for every EventRiskGovernor family. It separates measured association from no-local-event and blocked-precondition statuses. It uses local source/study artifacts only and performs no provider calls, training, activation, broker/account mutation, destructive SQL, or artifact deletion.

`event_family_expanded_stability.csv` is a preparation-only stability screen for the next threshold/grading step. It does not assign final thresholds or grades.
""",
        encoding="utf-8",
    )


def write_association(association: EventFamilyAllAssociation, *, output: TextIO) -> None:
    json.dump(association.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "EventFamilyAllAssociation",
    "FamilyAssociationRow",
    "build_event_family_all_association",
    "write_association",
    "write_event_family_all_association_artifacts",
]
