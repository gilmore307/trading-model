"""EventRiskGovernor closeout report helpers.

This module turns the 2026-05 event-layer redo judgment into a compact,
machine-readable closeout artifact. It performs no training, provider calls,
activation, broker/account mutation, or artifact deletion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
import json

from .contract import MODEL_ID, MODEL_LAYER, MODEL_SURFACE, VECTOR_OUTPUT

FINAL_JUDGMENT_DOC = "trading-model/docs/102_event_layer_final_judgment.md"
EVENT_FAMILY_PACKET_DOC = "trading-model/docs/101_earnings_guidance_event_family_packet.md"
LAYER_CONTRACT_DOC = "trading-model/docs/09_layer_08_event_risk_governor.md"


@dataclass(frozen=True)
class EventFamilyCloseoutStatus:
    family_key: str
    status: str
    accepted_use: str
    blocked_use: str
    blocker_codes: tuple[str, ...]
    next_evidence_gate: str

    def summary_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["blocker_codes"] = list(self.blocker_codes)
        return row


@dataclass(frozen=True)
class EventModelCloseoutReport:
    contract_type: str
    generated_at_utc: str
    model_id: str
    model_layer: int
    model_surface: str
    vector_output: str
    architecture_status: str
    actionable_judgment: str
    accepted_build_boundary: tuple[str, ...]
    rejected_routes: tuple[str, ...]
    family_statuses: tuple[EventFamilyCloseoutStatus, ...]
    downstream_regeneration_policy: str
    storage_lifecycle_hold: str
    required_next_actions: tuple[str, ...]
    source_documents: tuple[str, ...]
    provider_calls: int = 0
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    artifact_deletion_performed: bool = False

    def summary_row(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "model_id": self.model_id,
            "model_layer": self.model_layer,
            "model_surface": self.model_surface,
            "vector_output": self.vector_output,
            "architecture_status": self.architecture_status,
            "actionable_judgment": self.actionable_judgment,
            "accepted_build_boundary": list(self.accepted_build_boundary),
            "rejected_routes": list(self.rejected_routes),
            "family_statuses": [item.summary_row() for item in self.family_statuses],
            "downstream_regeneration_policy": self.downstream_regeneration_policy,
            "storage_lifecycle_hold": self.storage_lifecycle_hold,
            "required_next_actions": list(self.required_next_actions),
            "source_documents": list(self.source_documents),
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def build_event_model_closeout_report(*, generated_at_utc: str | None = None) -> EventModelCloseoutReport:
    """Build the accepted closeout report for the event-layer redo loop."""

    generated = generated_at_utc or datetime.now(UTC).isoformat()
    return EventModelCloseoutReport(
        contract_type="event_model_closeout_report_v1",
        generated_at_utc=generated,
        model_id=MODEL_ID,
        model_layer=MODEL_LAYER,
        model_surface=MODEL_SURFACE,
        vector_output=VECTOR_OUTPUT,
        architecture_status="accepted_bounded_event_risk_governor",
        actionable_judgment=(
            "Close the event-model redo as Layer 8 EventRiskGovernor / EventIntelligenceOverlay: "
            "event evidence may govern risk, uncertainty, review, block/cap/reduce/flatten hints, "
            "but it does not unlock broad event alpha, option-flow alpha, signed earnings/guidance alpha, "
            "model activation, broker execution, or account mutation."
        ),
        accepted_build_boundary=(
            "canonical_event_timeline",
            "point_in_time_event_interpretation_when_reviewed",
            "event_activity_bridge_as_provenance_and_risk_context",
            "risk_governor_intervention_review_block_cap_reduce_flatten_hints",
            "base_layer_1_7_guidance_preserved_side_by_side_with_event_adjusted_guidance",
        ),
        rejected_routes=(
            "broad_news_sentiment_alpha",
            "raw_news_proximity_amplifier",
            "standalone_option_abnormality_alpha",
            "threshold_only_option_flow_model",
            "signed_earnings_guidance_alpha_without_pit_expectation_baselines",
            "broker_order_or_account_mutation_from_event_layer",
        ),
        family_statuses=(
            EventFamilyCloseoutStatus(
                family_key="standalone_option_abnormality",
                status="deferred_low_signal",
                accepted_use="diagnostic_provenance_and_event_activity_bridge_context_only",
                blocked_use="standalone_alpha_or_directional_option_flow_route",
                blocker_codes=("matched_controls_failed", "non_earnings_option_standard_saturated"),
                next_evidence_gate="revise_abnormality_standard_then_revalidate_forward_controls_before_any_alpha_claim",
            ),
            EventFamilyCloseoutStatus(
                family_key="raw_news_proximity",
                status="deferred_low_signal",
                accepted_use="discovery_or_secondary_narrative_residual_when_tied_to_canonical_event",
                blocked_use="raw_headline_keyword_alpha_or_broad_news_amplifier",
                blocker_codes=("news_proximity_saturated", "canonical_source_required"),
                next_evidence_gate="family_specific_canonical_source_led_packet_with_event_interpretation_v1",
            ),
            EventFamilyCloseoutStatus(
                family_key="earnings_guidance_event_family",
                status="scouting_direction_neutral_context_only",
                accepted_use="scheduled_shells_official_results_and_reviewed_guidance_context_as_event_risk_context",
                blocked_use="signed_guidance_raise_cut_alpha_or_stronger_intervention",
                blocker_codes=(
                    "missing_current_comparable_guidance_context",
                    "missing_pit_revenue_consensus_baseline",
                    "missing_accepted_signed_result_guidance_comparison",
                ),
                next_evidence_gate="reviewed_current_prior_guidance_comparison_plus_pit_expectation_baselines_before_signed_claims",
            ),
            EventFamilyCloseoutStatus(
                family_key="event_risk_governor_structure",
                status="accepted_architecture",
                accepted_use="bounded_risk_intelligence_overlay_after_base_layer_1_7_guidance",
                blocked_use="entry_selection_position_sizing_contract_selection_order_routing_or_account_mutation",
                blocker_codes=("activation_requires_manager_promotion_review", "execution_mutation_out_of_scope"),
                next_evidence_gate="rebuild_source_08_feature_08_model_08_over_reviewed_event_feeds_then_evaluate_without_activation",
            ),
        ),
        downstream_regeneration_policy=(
            "Invalidate/rebuild only event-risk-governor-dependent outputs after reviewed source_08/feature_08 coverage; "
            "do not make base Layers 1-7 wait on event feeds, and do not delete legacy evidence artifacts."
        ),
        storage_lifecycle_hold=(
            "Keep dashboard snapshot/model-run metadata deletion on hold until event-risk-governor regeneration and downstream review are complete."
        ),
        required_next_actions=(
            "prepare_or_verify_required_event_feed_artifacts_for_each_fold_month",
            "materialize_source_08_event_risk_governor_from_reviewed_local_event_feeds",
            "generate_feature_08_event_risk_governor_and_model_08_event_risk_governor_outputs",
            "evaluate_event_risk_governor_with_direction_neutral_risk_labels_before_directional_claims",
            "record_manager_promotion_review_as_deferred_unless_real_gates_pass",
            "revisit_storage_lifecycle_deletion_holds_only_after_reviewed_regeneration_closeout",
        ),
        source_documents=(FINAL_JUDGMENT_DOC, EVENT_FAMILY_PACKET_DOC, LAYER_CONTRACT_DOC),
    )


def write_report(report: EventModelCloseoutReport, *, output: TextIO) -> None:
    json.dump(report.summary_row(), output, indent=2, sort_keys=True)
    output.write("\n")


def write_report_file(report: EventModelCloseoutReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.summary_row(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "EventFamilyCloseoutStatus",
    "EventModelCloseoutReport",
    "build_event_model_closeout_report",
    "write_report",
    "write_report_file",
]
