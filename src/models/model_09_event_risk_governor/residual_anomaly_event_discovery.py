"""Residual-anomaly to event-family discovery for EventRiskGovernor.

This module starts from Layers 1-7 evaluation labels instead of raw price moves.
It identifies base-stack residual anomalies, then scans nearby point-in-time event
families to propose observation-pool candidates or strategy-promotion review
packets. It is safe/local by default: no provider calls, training, activation,
broker/account mutation, destructive SQL, service daemon start, or artifact
deletion.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from models.model_09_event_risk_governor.price_anomaly_event_discovery import _event_family_dates, _nearby, _parse_dt

CONTRACT_TYPE = "residual_anomaly_event_discovery_v1"
SUMMARY_CONTRACT_TYPE = "residual_anomaly_event_discovery_summary_v1"
PROMOTION_REVIEW_PACKET_CONTRACT_TYPE = "event_family_strategy_promotion_review_packet_v1"
DEFAULT_MODEL_RUNTIME_ROOT = Path("storage/runtime")
DEFAULT_SOURCE_ROOT = Path("/root/projects/trading-data/storage/monthly_backfill_v1")
DEFAULT_OUTPUT_DIR = Path("storage/residual_anomaly_event_discovery_20260516")
DEFAULT_EVALUATION_MONTH = "2016-01"
DEFAULT_EVENT_WINDOW_DAYS = 1
MIN_RESIDUAL_SEVERITY = 0.01


@dataclass(frozen=True)
class LayerSevenLabel:
    target_candidate_id: str
    available_time: str
    available_day: date
    underlying_action_plan_ref: str
    planned_underlying_action_type: str
    planned_action_side: str
    realized_underlying_return_after_entry: float | None
    realized_net_underlying_utility: float | None
    no_trade_opportunity_cost: float | None
    no_trade_missed_positive_utility_rate: float
    no_trade_avoided_negative_utility_rate: float
    base_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ResidualAnomalyRow:
    target_candidate_id: str
    available_time: str
    available_day: str
    underlying_action_plan_ref: str
    base_action_type: str
    base_action_side: str
    residual_type: str
    residual_direction: str
    realized_underlying_return_after_entry: float | None
    realized_net_underlying_utility: float | None
    no_trade_opportunity_cost: float | None
    residual_severity_score: float
    base_reason_codes: tuple[str, ...]
    nearby_event_families: tuple[str, ...]
    nearby_event_sources: tuple[str, ...]
    layer_1_7_basis: str

    def csv_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in asdict(self).items():
            if isinstance(value, tuple):
                out[key] = ";".join(value)
            elif value is None:
                out[key] = ""
            else:
                out[key] = str(value)
        return out


@dataclass(frozen=True)
class ResidualFamilyEnrichmentRow:
    family_key: str
    residual_hit_count: int
    residual_observation_count: int
    residual_hit_rate: float
    control_hit_count: int
    control_observation_count: int
    control_hit_rate: float
    hit_rate_delta: float | None
    lift: float | None
    observation_pool_recommendation: str
    strategy_promotion_recommendation: str
    agent_review_packet_required: bool
    evidence_note: str

    def csv_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in asdict(self).items():
            if isinstance(value, bool):
                out[key] = str(value).lower()
            elif value is None:
                out[key] = ""
            else:
                out[key] = str(value)
        return out


@dataclass(frozen=True)
class EventFamilyStrategyPromotionReviewPacket:
    contract_type: str
    family_key: str
    requested_decision: str
    review_status: str
    evidence_basis: str
    residual_hit_count: int
    residual_observation_count: int
    control_hit_count: int
    control_observation_count: int
    hit_rate_delta: float | None
    lift: float | None
    required_agent_decision: str
    note: str

    def json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True) + "\n"


@dataclass(frozen=True)
class ResidualAnomalyEventDiscovery:
    contract_type: str
    generated_at_utc: str
    evaluation_month: str
    event_window_days: int
    min_residual_severity: float
    residual_rows: tuple[ResidualAnomalyRow, ...]
    enrichment_rows: tuple[ResidualFamilyEnrichmentRow, ...]
    promotion_review_packets: tuple[EventFamilyStrategyPromotionReviewPacket, ...]
    provider_calls: int = 0
    model_training_performed: bool = False
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    service_daemon_started: bool = False
    artifact_deletion_performed: bool = False

    @property
    def summary(self) -> dict[str, Any]:
        residual_count = len(self.residual_rows)
        control_counts = {row.control_observation_count for row in self.enrichment_rows}
        control_status = "available" if any(count > 0 for count in control_counts) else "missing_non_residual_control_labels"
        return {
            "contract_type": SUMMARY_CONTRACT_TYPE,
            "generated_at_utc": self.generated_at_utc,
            "evaluation_month": self.evaluation_month,
            "event_window_days": self.event_window_days,
            "min_residual_severity": self.min_residual_severity,
            "residual_anomaly_count": residual_count,
            "residual_target_candidate_count": len({row.target_candidate_id for row in self.residual_rows}),
            "enriched_family_count": len(self.enrichment_rows),
            "observation_pool_candidates": [
                row.family_key for row in self.enrichment_rows if row.observation_pool_recommendation == "add_to_observation_pool_candidate"
            ],
            "strategy_promotion_review_candidates": [
                row.family_key for row in self.enrichment_rows if row.strategy_promotion_recommendation == "strategy_promotion_review_candidate"
            ],
            "promotion_review_packet_count": len(self.promotion_review_packets),
            "control_label_status": control_status,
            "service_integration_status": "registered_callable_artifact_builder_only_no_daemon_start",
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "service_daemon_started": self.service_daemon_started,
            "artifact_deletion_performed": self.artifact_deletion_performed,
            "discovery_note": "Starts from Layers 1-7 evaluation residuals, then searches nearby PIT event families. Promotion requires an evidence packet plus agent review.",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "evaluation_month": self.evaluation_month,
            "event_window_days": self.event_window_days,
            "min_residual_severity": self.min_residual_severity,
            "residual_rows": [asdict(row) for row in self.residual_rows],
            "enrichment_rows": [asdict(row) for row in self.enrichment_rows],
            "promotion_review_packets": [asdict(packet) for packet in self.promotion_review_packets],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "service_daemon_started": self.service_daemon_started,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def _truthy_rate(value: Any) -> float:
    out = _safe_float(value)
    if out is not None:
        return out
    return 1.0 if value is True else 0.0


def _coerce_reason_codes(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    if isinstance(value, str) and value:
        return tuple(part.strip() for part in value.split(";") if part.strip())
    return ()


def _load_plan_reason_codes(runtime_root: Path, evaluation_month: str) -> dict[str, tuple[str, ...]]:
    path = runtime_root / "model_07_underlying_action" / f"model_rows_{evaluation_month}.jsonl"
    result: dict[str, tuple[str, ...]] = {}
    if not path.exists():
        return result
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            ref = str(row.get("underlying_action_plan_ref") or "")
            if not ref:
                continue
            reasons = _coerce_reason_codes(row.get("8_resolved_reason_codes"))
            if not reasons:
                plan = row.get("underlying_action_plan") if isinstance(row.get("underlying_action_plan"), Mapping) else {}
                reasons = _coerce_reason_codes(plan.get("reason_codes"))
            result.setdefault(ref, reasons)
    return result


def _load_layer_seven_labels(runtime_root: Path, evaluation_month: str) -> list[LayerSevenLabel]:
    path = runtime_root / "model_07_underlying_action" / f"evaluation_summary_{evaluation_month}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    reason_codes = _load_plan_reason_codes(runtime_root, evaluation_month)
    rows: list[LayerSevenLabel] = []
    for raw in payload.get("labels") or []:
        if not isinstance(raw, Mapping):
            continue
        parsed = _parse_dt(str(raw.get("available_time") or ""))
        if not parsed:
            continue
        plan_ref = str(raw.get("underlying_action_plan_ref") or "")
        rows.append(
            LayerSevenLabel(
                target_candidate_id=str(raw.get("target_candidate_id") or ""),
                available_time=parsed.isoformat(),
                available_day=parsed.date(),
                underlying_action_plan_ref=plan_ref,
                planned_underlying_action_type=str(raw.get("planned_underlying_action_type") or "unknown"),
                planned_action_side=str(raw.get("planned_action_side") or raw.get("action_side") or "unknown"),
                realized_underlying_return_after_entry=_safe_float(raw.get("realized_underlying_return_after_entry")),
                realized_net_underlying_utility=_safe_float(raw.get("realized_net_underlying_utility")),
                no_trade_opportunity_cost=_safe_float(raw.get("no_trade_opportunity_cost")),
                no_trade_missed_positive_utility_rate=_truthy_rate(raw.get("no_trade_missed_positive_utility_rate")),
                no_trade_avoided_negative_utility_rate=_truthy_rate(raw.get("no_trade_avoided_negative_utility_rate")),
                base_reason_codes=reason_codes.get(plan_ref, ()),
            )
        )
    return rows


def _residual_type(label: LayerSevenLabel, min_residual_severity: float) -> tuple[str | None, str, float]:
    realized_return = label.realized_underlying_return_after_entry or 0.0
    utility = label.realized_net_underlying_utility or 0.0
    opportunity = label.no_trade_opportunity_cost or 0.0
    severity = max(abs(realized_return), abs(utility), abs(opportunity))
    if severity < min_residual_severity:
        return None, "none", severity
    action_type = label.planned_underlying_action_type.lower()
    if action_type == "no_trade" and label.no_trade_missed_positive_utility_rate > 0:
        direction = "upside_missed" if realized_return >= 0 else "downside_missed"
        return "base_stack_no_trade_missed_move", direction, severity
    if action_type != "no_trade" and utility < -min_residual_severity:
        return "base_stack_action_negative_utility", "adverse", severity
    if abs(realized_return) >= max(0.03, min_residual_severity * 2) and label.no_trade_avoided_negative_utility_rate <= 0:
        direction = "positive_path" if realized_return >= 0 else "negative_path"
        return "base_stack_path_risk_unexplained", direction, severity
    return None, "none", severity


def _classify_enrichment(residual_hits: int, residual_n: int, control_hits: int, control_n: int) -> tuple[str, str, bool, str]:
    residual_rate = residual_hits / residual_n if residual_n else 0.0
    control_rate = control_hits / control_n if control_n else 0.0
    delta = residual_rate - control_rate if control_n else None
    lift = residual_rate / control_rate if control_rate > 0 else None
    if control_n == 0:
        if residual_hits >= 10:
            return (
                "research_only_needs_non_residual_controls",
                "no_strategy_promotion_currently",
                False,
                "Residual labels are saturated or controls are unavailable; build non-residual Layer 1-7 controls before observation-pool or strategy promotion.",
            )
        return ("not_enough_residual_hits", "no_strategy_promotion_currently", False, "Too few residual hits and no controls available.")
    if residual_hits >= 20 and delta is not None and delta >= 0.12 and (lift is None or lift >= 1.5):
        if residual_hits >= 40 and delta >= 0.20 and lift is not None and lift >= 2.0:
            return (
                "add_to_observation_pool_candidate",
                "strategy_promotion_review_candidate",
                True,
                "Family is strongly enriched around base-stack residuals; emit strategy-promotion review packet for agent decision.",
            )
        return (
            "add_to_observation_pool_candidate",
            "no_strategy_promotion_currently",
            False,
            "Family is enriched around base-stack residuals; candidate for realtime observation pool after review.",
        )
    if residual_hits >= 5 and delta is not None and delta > 0:
        return ("probationary_observation_review", "no_strategy_promotion_currently", False, "Positive but thin residual enrichment; hold for more data.")
    return ("not_enriched_or_too_thin", "no_strategy_promotion_currently", False, "No robust residual-enrichment evidence.")


def build_residual_anomaly_event_discovery(
    *,
    runtime_root: Path = DEFAULT_MODEL_RUNTIME_ROOT,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    evaluation_month: str = DEFAULT_EVALUATION_MONTH,
    event_window_days: int = DEFAULT_EVENT_WINDOW_DAYS,
    min_residual_severity: float = MIN_RESIDUAL_SEVERITY,
    generated_at_utc: str | None = None,
) -> ResidualAnomalyEventDiscovery:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    labels = _load_layer_seven_labels(runtime_root, evaluation_month)
    event_dates = _event_family_dates(source_root)
    residual_rows: list[ResidualAnomalyRow] = []
    family_residual_hits: dict[str, int] = defaultdict(int)
    family_control_hits: dict[str, int] = defaultdict(int)
    residual_n = 0
    control_n = 0
    for label in labels:
        residual_kind, residual_direction, severity = _residual_type(label, min_residual_severity)
        families, sources = _nearby(label.available_day, event_dates, event_window_days)
        if residual_kind:
            residual_n += 1
            for family in families:
                family_residual_hits[family] += 1
            residual_rows.append(
                ResidualAnomalyRow(
                    target_candidate_id=label.target_candidate_id,
                    available_time=label.available_time,
                    available_day=label.available_day.isoformat(),
                    underlying_action_plan_ref=label.underlying_action_plan_ref,
                    base_action_type=label.planned_underlying_action_type,
                    base_action_side=label.planned_action_side,
                    residual_type=residual_kind,
                    residual_direction=residual_direction,
                    realized_underlying_return_after_entry=label.realized_underlying_return_after_entry,
                    realized_net_underlying_utility=label.realized_net_underlying_utility,
                    no_trade_opportunity_cost=label.no_trade_opportunity_cost,
                    residual_severity_score=severity,
                    base_reason_codes=label.base_reason_codes,
                    nearby_event_families=families,
                    nearby_event_sources=sources,
                    layer_1_7_basis="model_07_underlying_action_evaluation_labels_over_layers_1_7_inputs",
                )
            )
        else:
            control_n += 1
            for family in families:
                family_control_hits[family] += 1
    enrichment_rows: list[ResidualFamilyEnrichmentRow] = []
    packets: list[EventFamilyStrategyPromotionReviewPacket] = []
    for family in sorted(set(family_residual_hits) | set(family_control_hits)):
        rh = family_residual_hits[family]
        ch = family_control_hits[family]
        rr = rh / residual_n if residual_n else 0.0
        cr = ch / control_n if control_n else 0.0
        delta = rr - cr if control_n else None
        lift = rr / cr if cr > 0 else None
        pool_rec, strategy_rec, packet_required, note = _classify_enrichment(rh, residual_n, ch, control_n)
        row = ResidualFamilyEnrichmentRow(
            family_key=family,
            residual_hit_count=rh,
            residual_observation_count=residual_n,
            residual_hit_rate=rr,
            control_hit_count=ch,
            control_observation_count=control_n,
            control_hit_rate=cr,
            hit_rate_delta=delta,
            lift=lift,
            observation_pool_recommendation=pool_rec,
            strategy_promotion_recommendation=strategy_rec,
            agent_review_packet_required=packet_required,
            evidence_note=note,
        )
        enrichment_rows.append(row)
        if packet_required:
            packets.append(
                EventFamilyStrategyPromotionReviewPacket(
                    contract_type=PROMOTION_REVIEW_PACKET_CONTRACT_TYPE,
                    family_key=family,
                    requested_decision="accept_defer_or_reject_strategy_layer_promotion",
                    review_status="agent_review_required_not_auto_approved",
                    evidence_basis="base_stack_residual_anomaly_enrichment",
                    residual_hit_count=rh,
                    residual_observation_count=residual_n,
                    control_hit_count=ch,
                    control_observation_count=control_n,
                    hit_rate_delta=delta,
                    lift=lift,
                    required_agent_decision="accept_defer_reject",
                    note=note,
                )
            )
    enrichment_rows.sort(
        key=lambda row: (
            row.strategy_promotion_recommendation != "strategy_promotion_review_candidate",
            row.observation_pool_recommendation != "add_to_observation_pool_candidate",
            -(row.hit_rate_delta if row.hit_rate_delta is not None else -1.0),
            -row.residual_hit_count,
            row.family_key,
        )
    )
    return ResidualAnomalyEventDiscovery(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        evaluation_month=evaluation_month,
        event_window_days=event_window_days,
        min_residual_severity=min_residual_severity,
        residual_rows=tuple(residual_rows),
        enrichment_rows=tuple(enrichment_rows),
        promotion_review_packets=tuple(packets),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_residual_anomaly_event_discovery_artifacts(discovery: ResidualAnomalyEventDiscovery, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "residual_anomaly_event_discovery.json").write_text(
        json.dumps(discovery.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "residual_anomaly_event_discovery_summary.json").write_text(
        json.dumps(discovery.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    residual_fields = list(ResidualAnomalyRow("", "", "", "", "", "", "", "", None, None, None, 0, (), (), (), "").csv_row().keys())
    enrichment_fields = list(ResidualFamilyEnrichmentRow("", 0, 0, 0, 0, 0, 0, None, None, "", "", False, "").csv_row().keys())
    _write_csv(output_dir / "residual_anomaly_events.csv", [row.csv_row() for row in discovery.residual_rows], fieldnames=residual_fields)
    _write_csv(
        output_dir / "residual_anomaly_event_family_enrichment.csv",
        [row.csv_row() for row in discovery.enrichment_rows],
        fieldnames=enrichment_fields,
    )
    (output_dir / "event_family_strategy_promotion_review_packets.jsonl").write_text(
        "".join(packet.json_line() for packet in discovery.promotion_review_packets), encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        f"""# Residual anomaly event discovery

Contract: `{discovery.contract_type}`

This artifact starts from Layers 1-7 evaluation residuals, not raw price anomalies. It then searches nearby point-in-time event families for explanations, observation-pool candidates, and strategy-promotion review packets. Strategy promotion remains blocked until an emitted packet receives agent review.

Safety: no provider calls, model training, model activation, broker/account mutation, service daemon start, destructive SQL, or artifact deletion.
""",
        encoding="utf-8",
    )


def write_discovery(discovery: ResidualAnomalyEventDiscovery, *, output: TextIO) -> None:
    json.dump(discovery.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "EventFamilyStrategyPromotionReviewPacket",
    "ResidualAnomalyEventDiscovery",
    "ResidualAnomalyRow",
    "ResidualFamilyEnrichmentRow",
    "build_residual_anomaly_event_discovery",
    "write_discovery",
    "write_residual_anomaly_event_discovery_artifacts",
]
