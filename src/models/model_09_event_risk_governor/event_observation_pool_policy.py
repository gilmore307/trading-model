"""Event observation-pool and promotion policy for EventRiskGovernor.

Historical research may scan all point-in-time events to explain residual anomalies.
Realtime operation observes only reviewed event families in the observation pool.
Highly stable/predictive families may be proposed for strategy-layer promotion, but
final promotion requires an agent review decision.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

CONTRACT_TYPE = "event_observation_pool_policy_v1"
SUMMARY_CONTRACT_TYPE = "event_observation_pool_policy_summary_v1"
DEFAULT_OUTPUT_DIR = Path("storage/event_observation_pool_policy_20260516")


@dataclass(frozen=True)
class ObservationPoolRow:
    family_key: str
    realtime_pool_status: str
    layer_role: str
    evidence_basis: str
    realtime_action: str
    promotion_status: str
    agent_review_required: bool
    note: str

    def csv_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in asdict(self).items():
            out[key] = str(value).lower() if isinstance(value, bool) else str(value)
        return out


@dataclass(frozen=True)
class PromotionRuleRow:
    rule_key: str
    applies_to: str
    minimum_requirement: str
    allowed_result: str
    agent_review_required: bool

    def csv_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in asdict(self).items():
            out[key] = str(value).lower() if isinstance(value, bool) else str(value)
        return out


@dataclass(frozen=True)
class EventObservationPoolPolicy:
    contract_type: str
    generated_at_utc: str
    observation_pool_rows: tuple[ObservationPoolRow, ...]
    promotion_rule_rows: tuple[PromotionRuleRow, ...]
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
            "historical_research_scope": "scan_all_point_in_time_events_to_explain_residual_anomalies",
            "realtime_operation_scope": "observe_reviewed_event_observation_pool_only",
            "active_realtime_observation_pool": [
                row.family_key for row in self.observation_pool_rows if row.realtime_pool_status == "active_observation_pool"
            ],
            "probationary_realtime_observation_pool": [
                row.family_key for row in self.observation_pool_rows if row.realtime_pool_status == "probationary_observation_pool"
            ],
            "strategy_promotion_candidates": [
                row.family_key for row in self.observation_pool_rows if row.promotion_status == "strategy_promotion_candidate"
            ],
            "agent_review_required_for_strategy_promotion": True,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "observation_pool_rows": [asdict(row) for row in self.observation_pool_rows],
            "promotion_rule_rows": [asdict(row) for row in self.promotion_rule_rows],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def build_event_observation_pool_policy(*, generated_at_utc: str | None = None) -> EventObservationPoolPolicy:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    observation_rows = (
        ObservationPoolRow(
            family_key="cpi_inflation_release",
            realtime_pool_status="active_observation_pool",
            layer_role="risk_correction_layer",
            evidence_basis="accepted_actual_vs_expectation_surprise_risk_volatility_association",
            realtime_action="monitor_calendar_and_surprise_fields_for_warning_path_risk_and_risk_off_correction",
            promotion_status="not_strategy_promotion_currently",
            agent_review_required=True,
            note="Accepted for event-risk/control observation, not standalone alpha.",
        ),
        ObservationPoolRow(
            family_key="earnings_guidance_scheduled_shell",
            realtime_pool_status="active_observation_pool",
            layer_role="risk_correction_layer",
            evidence_basis="accepted_scheduled_path_risk_association",
            realtime_action="monitor_scheduled_earnings_or_guidance_windows_for_gap_path_risk_and_review_hints",
            promotion_status="not_strategy_promotion_currently",
            agent_review_required=True,
            note="Accepted as scheduled path-risk context only; signed result/guidance alpha remains blocked.",
        ),
        ObservationPoolRow(
            family_key="legal_regulatory_investigation",
            realtime_pool_status="probationary_observation_pool",
            layer_role="event_explanation_candidate",
            evidence_basis="reverse_price_anomaly_discovery_enrichment_candidate",
            realtime_action="monitor as candidate explanation source while canonical parser, dedup, and relevance controls are built",
            promotion_status="not_strategy_promotion_currently",
            agent_review_required=True,
            note="Reverse-discovery candidate; not accepted for intervention until canonical event interpretation and matched controls pass.",
        ),
    )
    promotion_rules = (
        PromotionRuleRow(
            rule_key="historical_discovery_uses_all_events",
            applies_to="training_and_research",
            minimum_requirement="all point-in-time event/news/filing/macro candidates may be searched to explain residual anomalies",
            allowed_result="new family may be proposed for observation pool",
            agent_review_required=False,
        ),
        PromotionRuleRow(
            rule_key="realtime_observes_pool_only",
            applies_to="production_realtime_monitoring",
            minimum_requirement="family is active or probationary observation-pool member with reviewed evidence basis",
            allowed_result="event may be monitored for warnings/explanations/corrections",
            agent_review_required=True,
        ),
        PromotionRuleRow(
            rule_key="correction_layer_acceptance",
            applies_to="event_risk_governor",
            minimum_requirement="residual anomaly explanation, canonical event clocks, relevance, matched controls, and stability support risk/path correction",
            allowed_result="warning, uncertainty, path-risk, entry-block, cap, reduce/flatten-review, or human-review hint",
            agent_review_required=True,
        ),
        PromotionRuleRow(
            rule_key="strategy_layer_promotion",
            applies_to="strategy_decision_layer",
            minimum_requirement="stable predictive reaction across splits, controls, base-stack residuals, regimes, and no leakage; improvement over base strategy is material",
            allowed_result="event family may become strategy-decision input rather than correction-only overlay",
            agent_review_required=True,
        ),
        PromotionRuleRow(
            rule_key="agent_final_decision",
            applies_to="script_requested_promotion_or_demotion",
            minimum_requirement="script emits evidence packet and calls agent review for final accept/defer/reject decision",
            allowed_result="manager records reviewed decision before production scope changes",
            agent_review_required=True,
        ),
    )
    return EventObservationPoolPolicy(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        observation_pool_rows=observation_rows,
        promotion_rule_rows=promotion_rules,
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_event_observation_pool_policy_artifacts(policy: EventObservationPoolPolicy, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_observation_pool_policy.json").write_text(
        json.dumps(policy.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_observation_pool_policy_summary.json").write_text(
        json.dumps(policy.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    observation_fields = list(ObservationPoolRow("", "", "", "", "", "", False, "").csv_row().keys())
    rule_fields = list(PromotionRuleRow("", "", "", "", False).csv_row().keys())
    _write_csv(output_dir / "event_observation_pool.csv", [row.csv_row() for row in policy.observation_pool_rows], fieldnames=observation_fields)
    _write_csv(output_dir / "event_promotion_rules.csv", [row.csv_row() for row in policy.promotion_rule_rows], fieldnames=rule_fields)
    (output_dir / "README.md").write_text(
        f"""# Event observation-pool policy

Contract: `{policy.contract_type}`

This artifact separates research from realtime operations. Historical research may scan all point-in-time events to explain residual anomalies. Realtime operation should observe only reviewed event families in the observation pool. Strategy-layer promotion requires a script-emitted evidence packet and final agent review.
""",
        encoding="utf-8",
    )


def write_policy(policy: EventObservationPoolPolicy, *, output: TextIO) -> None:
    json.dump(policy.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "EventObservationPoolPolicy",
    "ObservationPoolRow",
    "PromotionRuleRow",
    "build_event_observation_pool_policy",
    "write_event_observation_pool_policy_artifacts",
    "write_policy",
]
