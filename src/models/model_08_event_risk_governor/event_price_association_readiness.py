"""Safe local event-price association readiness batch.

The batch consumes only already-local catalog/data artifacts. It does not call
providers, train/activate models, mutate broker/account state, or delete files.

This is intentionally a readiness/scouting surface: a family may expose candidate
events and exploratory price labels, but promotion stays blocked until the family
has accepted packets, point-in-time event interpretation, controls, and enough
coverage.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

CONTRACT_TYPE = "event_price_association_readiness_batch_v1"
DEFAULT_CATALOG_PATH = Path("storage/event_family_batch_catalog_20260516/event_family_batch_catalog.json")
DEFAULT_OUTPUT_DIR = Path("storage/event_price_association_readiness_20260516")
DEFAULT_DATA_ROOT = Path("/root/projects/trading-data")
DEFAULT_MONTH = "2016-01"
DEFAULT_FAMILY_KEYS = (
    "equity_offering_dilution",
    "legal_regulatory_investigation",
    "cpi_inflation_release",
    "credit_liquidity_stress",
)
DEFAULT_PRICE_SYMBOLS = ("TLT", "XLF", "XLK", "HYG", "XLE")
HORIZONS = (1, 5)

CPI_KEYWORDS = ("cpi", "consumer price", "inflation rate", "core inflation")
LEGAL_KEYWORDS = (
    "investigation",
    "probe",
    "lawsuit",
    "litigation",
    "regulatory",
    "regulator",
    "subpoena",
    "department of justice",
    "doj",
    "federal trade commission",
    "ftc",
    "antitrust",
    "enforcement action",
    "patent infringement",
)
OFFERING_KEYWORDS = (
    "secondary offering",
    "public offering",
    "shelf registration",
    "shelf offering",
    "convertible note offering",
    "convertible debt offering",
    "atm program",
    "at-the-market offering",
    "equity issuance",
    "common stock offering",
)
STRESS_KEYWORDS = (
    "credit stress",
    "liquidity stress",
    "bank stress",
    "funding stress",
    "credit crunch",
    "liquidity crunch",
    "systemic risk",
    "default risk",
    "contagion",
)


@dataclass(frozen=True)
class CandidateEvent:
    family_key: str
    event_key: str
    event_time: str
    event_name: str
    source_ref: str
    source_type: str
    evidence_text: str
    scope: str
    pit_status: str
    canonical_status: str

    def to_row(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PriceLabel:
    family_key: str
    event_key: str
    symbol: str
    baseline_date: str
    baseline_close: float
    horizon_days: int
    forward_close: float | None
    directional_return: float | None
    absolute_return: float | None
    path_range: float | None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FamilyReadiness:
    family_key: str
    priority: str
    routing_bucket: str
    mechanism_group: str
    readiness_status: str
    association_study_status: str
    candidate_event_count: int
    price_label_count: int
    control_coverage_status: str
    pit_status: str
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    next_action: str

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["blocker_codes"] = list(self.blocker_codes)
        row["evidence_refs"] = list(self.evidence_refs)
        return row

    def csv_row(self) -> dict[str, str]:
        row = self.to_row()
        return {key: ";".join(value) if isinstance(value, list) else str(value) for key, value in row.items()}


@dataclass(frozen=True)
class AssociationReadinessBatch:
    contract_type: str
    generated_at_utc: str
    month: str
    family_keys: tuple[str, ...]
    price_symbols: tuple[str, ...]
    family_readiness: tuple[FamilyReadiness, ...]
    candidate_events: tuple[CandidateEvent, ...]
    price_labels: tuple[PriceLabel, ...]
    provider_calls: int = 0
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "month": self.month,
            "family_keys": list(self.family_keys),
            "price_symbols": list(self.price_symbols),
            "family_readiness": [item.to_row() for item in self.family_readiness],
            "candidate_events": [item.to_row() for item in self.candidate_events],
            "price_labels": [item.to_row() for item in self.price_labels],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "family_count": len(self.family_readiness),
            "candidate_event_count": len(self.candidate_events),
            "price_label_count": len(self.price_labels),
            "readiness_status_counts": _counts(item.readiness_status for item in self.family_readiness),
            "association_study_status_counts": _counts(item.association_study_status for item in self.family_readiness),
            "families_with_price_labels": sorted({label.family_key for label in self.price_labels}),
            "blocked_family_keys": [
                item.family_key
                for item in self.family_readiness
                if item.association_study_status.startswith("blocked")
                or item.association_study_status.startswith("underpowered")
            ],
        }


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _text(row: Mapping[str, Any], *keys: str) -> str:
    return " ".join(str(row.get(key) or "") for key in keys).strip()


def _contains_any(text: str, keywords: Sequence[str]) -> bool:
    value = text.lower()
    return any(keyword in value for keyword in keywords)


def _parse_date(text: str) -> date:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date()


def _fnum(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("%", "").replace("$", "").replace(",", "")
    suffix = 1.0
    if text.endswith("B"):
        suffix = 1_000_000_000.0
        text = text[:-1]
    elif text.endswith("M"):
        suffix = 1_000_000.0
        text = text[:-1]
    elif text.endswith("K"):
        suffix = 1_000.0
        text = text[:-1]
    try:
        return float(text) * suffix
    except ValueError:
        return None


def _catalog_by_key(catalog_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(catalog_path)
    return {str(item["family_key"]): dict(item) for item in payload.get("candidates", [])}


def _completion_receipts(data_root: Path, family_key: str, month: str) -> list[Path]:
    if family_key in {"equity_offering_dilution", "legal_regulatory_investigation"}:
        patterns = [data_root / f"storage/monthly_backfill_v1/sec_company_financials/{month}/completion_receipt.json"]
    elif family_key == "cpi_inflation_release":
        patterns = [data_root / f"storage/monthly_backfill_v1/trading_economics_calendar_web/{month}/completion_receipt.json"]
    elif family_key == "credit_liquidity_stress":
        patterns = [
            data_root / f"storage/monthly_backfill_v1/gdelt_news/{month}/completion_receipt.json",
            data_root / f"storage/monthly_backfill_v1/alpaca_news/{month}/completion_receipt.json",
            data_root / f"storage/monthly_backfill_v1/trading_economics_calendar_web/{month}/completion_receipt.json",
        ]
    else:
        patterns = []
    return [path for path in patterns if path.exists()]


def _receipt_rows(path: Path) -> int:
    try:
        payload = _read_json(path)
    except json.JSONDecodeError:
        return 0
    total = 0
    for run in payload.get("runs", []):
        for value in (run.get("row_counts") or {}).values():
            if isinstance(value, int):
                total += value
    return total


def _source_csvs(data_root: Path, source: str, month: str, filename: str) -> list[Path]:
    root = data_root / f"storage/monthly_backfill_v1/{source}/{month}/runs"
    return sorted(root.glob(f"*/saved/{filename}"))


def _read_macro_events(data_root: Path, month: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for path in _source_csvs(data_root, "trading_economics_calendar_web", month, "trading_economics_calendar_event.csv"):
        for row in _read_csv(path):
            key = (str(row.get("event_time") or ""), str(row.get("event") or ""), str(row.get("reference") or ""))
            if key in seen:
                continue
            seen.add(key)
            row["_source_ref"] = str(path)
            rows.append(row)
    return rows


def _read_news_events(data_root: Path, month: str, keywords: Sequence[str], family_key: str) -> list[CandidateEvent]:
    out: list[CandidateEvent] = []
    sources = [
        ("alpaca_news", "equity_news.csv", ("timeline_headline", "summary"), "alpaca_news"),
        ("gdelt_news", "gdelt_article.csv", ("title", "source_theme_tags", "organizations"), "gdelt_news"),
    ]
    seen: set[str] = set()
    for source, filename, fields, source_type in sources:
        for path in _source_csvs(data_root, source, month, filename):
            for row in _read_csv(path):
                evidence_text = _text(row, *fields)
                if not _contains_any(evidence_text, keywords):
                    continue
                event_time = str(row.get("created_at") or row.get("seen_at") or "")
                event_name = str(row.get("timeline_headline") or row.get("title") or "")
                event_key = f"{family_key}:{source_type}:{event_time}:{event_name}"[:220]
                if event_key in seen:
                    continue
                seen.add(event_key)
                out.append(
                    CandidateEvent(
                        family_key=family_key,
                        event_key=event_key,
                        event_time=event_time,
                        event_name=event_name,
                        source_ref=str(path),
                        source_type=source_type,
                        evidence_text=evidence_text[:500],
                        scope="symbol_or_macro_news_candidate",
                        pit_status="source_timestamp_present_but_interpretation_not_reviewed",
                        canonical_status="not_canonicalized_family_candidate_only",
                    )
                )
    return out


def _cpi_candidate_events(data_root: Path, month: str) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    rows = _read_macro_events(data_root, month)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        text = _text(row, "event", "source_event_type")
        if _contains_any(text, CPI_KEYWORDS):
            grouped[str(row.get("event_time") or "")].append(row)
    for event_time, items in sorted(grouped.items()):
        names = ";".join(str(item.get("event") or "") for item in items)
        surprises = []
        for item in items:
            actual = _fnum(item.get("actual"))
            consensus = _fnum(item.get("consensus"))
            if actual is not None and consensus is not None:
                surprises.append(f"{item.get('event')} actual_minus_consensus={actual - consensus:g}")
        events.append(
            CandidateEvent(
                family_key="cpi_inflation_release",
                event_key=f"cpi_inflation_release:{event_time}",
                event_time=event_time,
                event_name=names,
                source_ref=";".join(sorted({str(item.get("_source_ref") or "") for item in items})),
                source_type="trading_economics_calendar_web",
                evidence_text="; ".join(surprises) if surprises else names,
                scope="macro",
                pit_status="calendar_timestamp_actual_previous_consensus_present",
                canonical_status="candidate_macro_release_not_official_source_canonicalized",
            )
        )
    return events


def _daily_bars(path: Path) -> list[dict[str, Any]]:
    grouped: dict[date, dict[str, Any]] = {}
    for row in _read_csv(path):
        close = _fnum(row.get("bar_close"))
        high = _fnum(row.get("bar_high"))
        low = _fnum(row.get("bar_low"))
        timestamp = str(row.get("timestamp") or "")
        if close is None or high is None or low is None or not timestamp:
            continue
        day = _parse_date(timestamp)
        item = grouped.setdefault(day, {"date": day, "high": high, "low": low, "close": close, "last_timestamp": timestamp})
        item["high"] = max(float(item["high"]), high)
        item["low"] = min(float(item["low"]), low)
        if timestamp >= str(item["last_timestamp"]):
            item["close"] = close
            item["last_timestamp"] = timestamp
    return [grouped[key] for key in sorted(grouped)]


def _bar_path(data_root: Path, symbol: str, month: str) -> Path | None:
    root = data_root / f"storage/monthly_backfill_v1/alpaca_bars/{symbol}/{month}/runs"
    paths = sorted(root.glob("*/saved/equity_bar.csv"))
    if not paths:
        return None
    return max(paths, key=lambda path: (path.stat().st_size, str(path)))


def _baseline_index(rows: Sequence[Mapping[str, Any]], event_day: date) -> int | None:
    previous: int | None = None
    for idx, row in enumerate(rows):
        if row["date"] >= event_day:
            return idx if row["date"] == event_day else previous
        previous = idx
    return previous


def _price_labels(data_root: Path, month: str, events: Sequence[CandidateEvent], symbols: Sequence[str]) -> list[PriceLabel]:
    labels: list[PriceLabel] = []
    bars_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        path = _bar_path(data_root, symbol, month)
        if path is not None:
            bars_by_symbol[symbol] = _daily_bars(path)
    for event in events:
        if not event.event_time:
            continue
        event_day = _parse_date(event.event_time)
        for symbol, rows in bars_by_symbol.items():
            index = _baseline_index(rows, event_day)
            if index is None:
                continue
            baseline = float(rows[index]["close"])
            for horizon in HORIZONS:
                end = index + horizon
                if end >= len(rows):
                    labels.append(
                        PriceLabel(
                            event.family_key,
                            event.event_key,
                            symbol,
                            rows[index]["date"].isoformat(),
                            baseline,
                            horizon,
                            None,
                            None,
                            None,
                            None,
                        )
                    )
                    continue
                window = rows[index + 1 : end + 1]
                forward_close = float(rows[end]["close"])
                directional = forward_close / baseline - 1.0
                path_range = max(float(row["high"]) for row in window) / baseline - min(float(row["low"]) for row in window) / baseline
                labels.append(
                    PriceLabel(
                        event.family_key,
                        event.event_key,
                        symbol,
                        rows[index]["date"].isoformat(),
                        baseline,
                        horizon,
                        forward_close,
                        directional,
                        abs(directional),
                        path_range,
                    )
                )
    return labels


def _candidate_events_for_family(data_root: Path, family_key: str, month: str) -> list[CandidateEvent]:
    if family_key == "cpi_inflation_release":
        return _cpi_candidate_events(data_root, month)
    if family_key == "legal_regulatory_investigation":
        return _read_news_events(data_root, month, LEGAL_KEYWORDS, family_key)
    if family_key == "equity_offering_dilution":
        return _read_news_events(data_root, month, OFFERING_KEYWORDS, family_key)
    if family_key == "credit_liquidity_stress":
        return _read_news_events(data_root, month, STRESS_KEYWORDS, family_key)
    return []


def _status_for_family(family_key: str, candidate_count: int, price_label_count: int) -> tuple[str, str, str, tuple[str, ...], str]:
    if family_key == "cpi_inflation_release" and candidate_count > 0 and price_label_count > 0:
        return (
            "local_event_and_price_labels_available_underpowered",
            "underpowered_single_month_scouting_only",
            "missing_matched_controls_and_multimonth_coverage",
            ("single_month_only", "needs_official_source_canonicalization", "needs_matched_controls", "needs_more_macro_cycles"),
            "Expand CPI family across more months, add official-source precedence, and build matched macro-control windows before any risk/alpha claim.",
        )
    if family_key == "equity_offering_dilution":
        return (
            "source_evidence_present_but_event_extraction_missing",
            "blocked_missing_offering_terms_parser",
            "no_controls_available",
            ("missing_family_packet", "needs_offering_terms_parser", "needs_canonical_filing_or_news_events", "needs_matched_controls"),
            "Build the equity-offering packet and parser for offering type, amount, discount, proceeds, filing time, and balance-sheet context.",
        )
    if family_key == "legal_regulatory_investigation":
        return (
            "candidate_headlines_possible_but_not_canonical",
            "blocked_missing_official_source_and_severity_taxonomy",
            "no_controls_available",
            ("missing_family_packet", "needs_official_source_precedence", "needs_severity_taxonomy", "needs_matched_controls"),
            "Create legal/regulatory packet with official-vs-news source precedence, severity ladder, and review-required rules before study.",
        )
    if family_key == "credit_liquidity_stress":
        return (
            "candidate_headlines_possible_but_not_stress_standardized",
            "blocked_missing_stress_event_standard",
            "no_controls_available",
            ("missing_family_packet", "needs_stress_severity_ladder", "needs_contagion_scope", "needs_matched_controls"),
            "Create credit/liquidity stress packet with severity, scope, official-source precedence, and macro/sector control windows.",
        )
    return (
        "not_evaluated",
        "blocked_not_in_first_batch",
        "no_controls_available",
        ("not_in_first_batch",),
        "Select family for a later readiness batch.",
    )


def build_event_price_association_readiness_batch(
    *,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    data_root: Path = DEFAULT_DATA_ROOT,
    month: str = DEFAULT_MONTH,
    family_keys: Sequence[str] = DEFAULT_FAMILY_KEYS,
    price_symbols: Sequence[str] = DEFAULT_PRICE_SYMBOLS,
    generated_at_utc: str | None = None,
) -> AssociationReadinessBatch:
    catalog = _catalog_by_key(catalog_path)
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    all_events: list[CandidateEvent] = []
    all_labels: list[PriceLabel] = []
    readiness_rows: list[FamilyReadiness] = []

    for family_key in family_keys:
        spec = catalog.get(family_key, {})
        candidate_events = _candidate_events_for_family(data_root, family_key, month)
        labels = _price_labels(data_root, month, candidate_events, price_symbols) if family_key == "cpi_inflation_release" else []
        receipts = _completion_receipts(data_root, family_key, month)
        receipt_refs = tuple(str(path) for path in receipts)
        source_rows = sum(_receipt_rows(path) for path in receipts)
        readiness_status, association_status, control_status, blockers, next_action = _status_for_family(
            family_key,
            len(candidate_events),
            len(labels),
        )
        if source_rows == 0 and not candidate_events:
            blockers = tuple(dict.fromkeys((*blockers, "missing_local_source_evidence")))
        evidence_refs = tuple(dict.fromkeys((*[str(ref) for ref in spec.get("evidence_refs", [])], *receipt_refs)))
        readiness_rows.append(
            FamilyReadiness(
                family_key=family_key,
                priority=str(spec.get("priority") or "unknown"),
                routing_bucket=str(spec.get("routing_bucket") or "unknown"),
                mechanism_group=str(spec.get("mechanism_group") or "unknown"),
                readiness_status=readiness_status,
                association_study_status=association_status,
                candidate_event_count=len(candidate_events),
                price_label_count=len(labels),
                control_coverage_status=control_status,
                pit_status="local_existing_artifacts_only_no_new_provider_calls",
                blocker_codes=blockers,
                evidence_refs=evidence_refs,
                next_action=next_action,
            )
        )
        all_events.extend(candidate_events)
        all_labels.extend(labels)

    return AssociationReadinessBatch(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        month=month,
        family_keys=tuple(family_keys),
        price_symbols=tuple(price_symbols),
        family_readiness=tuple(readiness_rows),
        candidate_events=tuple(all_events),
        price_labels=tuple(all_labels),
    )


def write_batch_artifacts(batch: AssociationReadinessBatch, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_price_association_batch.json").write_text(
        json.dumps(batch.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "event_price_association_family_readiness.csv",
        [row.csv_row() for row in batch.family_readiness],
        fieldnames=list(FamilyReadiness("", "", "", "", "", "", 0, 0, "", "", (), (), "").csv_row().keys()),
    )
    _write_csv(
        output_dir / "event_price_association_candidate_events.csv",
        [row.to_row() for row in batch.candidate_events],
        fieldnames=list(CandidateEvent("", "", "", "", "", "", "", "", "", "").to_row().keys()),
    )
    _write_csv(
        output_dir / "event_price_association_price_labels.csv",
        [row.to_row() for row in batch.price_labels],
        fieldnames=list(PriceLabel("", "", "", "", 0.0, 0, None, None, None, None).to_row().keys()),
    )
    (output_dir / "README.md").write_text(
        f"""# Event-price association readiness batch

Contract: `{batch.contract_type}`

This artifact is a safe local readiness/scouting batch for {', '.join(batch.family_keys)} using month `{batch.month}`.

- Provider calls: {batch.provider_calls}
- Model activation performed: {batch.model_activation_performed}
- Broker execution performed: {batch.broker_execution_performed}
- Account mutation performed: {batch.account_mutation_performed}
- Artifact deletion performed: {batch.artifact_deletion_performed}
- Candidate events: {len(batch.candidate_events)}
- Price labels: {len(batch.price_labels)}

The artifact does not promote any event family. Candidate headlines or macro calendar rows are not accepted canonical event interpretations until family packets, controls, and PIT source rules are reviewed.
""",
        encoding="utf-8",
    )


def write_batch(batch: AssociationReadinessBatch, *, output: TextIO) -> None:
    json.dump(batch.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "AssociationReadinessBatch",
    "CandidateEvent",
    "FamilyReadiness",
    "PriceLabel",
    "build_event_price_association_readiness_batch",
    "write_batch",
    "write_batch_artifacts",
]
