"""M03 event-state governance acceptance report helpers.

This module turns the 2026-05 event-layer redo judgment into a compact,
machine-readable acceptance artifact. It performs no training, provider calls,
activation, broker/account mutation, or artifact deletion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
import json

from ..contract import MODEL_ID, MODEL_STEP, MODEL_SURFACE, PRIMARY_OUTPUT

FINAL_JUDGMENT_DOC = "trading-model/docs/53_event_state_final_judgment.md"
EVENT_FAMILY_PACKET_DOC = "trading-model/docs/52_earnings_guidance_event_family_packet.md"
LAYER_CONTRACT_DOC = "trading-model/docs/12_model_03_event_state.md"


@dataclass(frozen=True)
class EventFamilyAcceptanceStatus:
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
class EventModelAcceptanceReport:
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
    family_statuses: tuple[EventFamilyAcceptanceStatus, ...]
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


def build_event_model_acceptance_report(*, generated_at_utc: str | None = None) -> EventModelAcceptanceReport:
    """Build the accepted acceptance report for the event-layer redo loop."""

    generated = generated_at_utc or datetime.now(UTC).isoformat()
    return EventModelAcceptanceReport(
        contract_type="event_model_acceptance_report",
        generated_at_utc=generated,
        model_id=MODEL_ID,
        model_layer=int(MODEL_STEP.removeprefix("M")),
        model_surface=MODEL_SURFACE,
        vector_output=PRIMARY_OUTPUT,
        architecture_status="accepted_m03_event_effect_model_governance",
        actionable_judgment=(
            "Close the event-model redo as M03 event-effect-model governance: "
            "event evidence may govern distribution shape, uncertainty, gate pressure, and reviewed directional channels, "
            "but it does not unlock broad event alpha, option-flow alpha, signed earnings/guidance alpha, "
            "component-control authority, model activation, broker execution, or account mutation."
        ),
        accepted_build_boundary=(
            "canonical_event_timeline",
            "point_in_time_event_interpretation_when_reviewed",
            "event_activity_bridge_as_provenance_and_risk_context",
            "event_effect_model_distribution_and_gate_channels",
            "explicit_no_impact_event_effect_disposition",
            "component_owned_block_cap_reduce_flatten_controls",
            "m01_m05_probability_stack_preserved_with_m03_event_operator",
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
            EventFamilyAcceptanceStatus(
                family_key="standalone_option_abnormality",
                status="deferred_low_signal",
                accepted_use="diagnostic_provenance_and_event_activity_bridge_context_only",
                blocked_use="standalone_alpha_or_directional_option_flow_route",
                blocker_codes=("matched_controls_failed", "non_earnings_option_standard_saturated"),
                next_evidence_gate="revise_abnormality_standard_then_revalidate_forward_controls_before_any_alpha_claim",
            ),
            EventFamilyAcceptanceStatus(
                family_key="raw_news_proximity",
                status="deferred_low_signal",
                accepted_use="discovery_or_secondary_narrative_residual_when_tied_to_canonical_event",
                blocked_use="raw_headline_keyword_alpha_or_broad_news_amplifier",
                blocker_codes=("news_proximity_saturated", "canonical_source_required"),
                next_evidence_gate="family_specific_canonical_source_led_packet_with_event_interpretation",
            ),
            EventFamilyAcceptanceStatus(
                family_key="earnings_guidance_event_family",
                status="scouting_direction_neutral_context_only",
                accepted_use="scheduled_shells_official_results_and_reviewed_guidance_context_as_event_risk_context",
                blocked_use="signed_guidance_raise_cut_alpha_or_stronger_effect_model",
                blocker_codes=(
                    "missing_current_comparable_guidance_context",
                    "missing_pit_revenue_consensus_baseline",
                    "missing_accepted_signed_result_guidance_comparison",
                ),
                next_evidence_gate="reviewed_current_prior_guidance_comparison_plus_pit_expectation_baselines_before_signed_claims",
            ),
            EventFamilyAcceptanceStatus(
                family_key="event_effect_model_governance_structure",
                status="accepted_architecture",
                accepted_use="m03_distribution_operator_and_event_effect_model_evidence",
                blocked_use="entry_selection_position_sizing_contract_selection_order_routing_or_account_mutation",
                blocker_codes=("activation_requires_manager_promotion_review", "execution_mutation_out_of_scope"),
                next_evidence_gate="materialize_model_03_event_state_event_inputs_generate_m03_event_distribution_channels_then_evaluate_without_activation",
            ),
        ),
        downstream_regeneration_policy=(
            "Invalidate/rebuild only M03-event-dependent outputs after reviewed event-feed coverage and "
            "model_03_event_state regeneration; do not make M01/M02 background or target surfaces "
            "wait on event feeds, and do not delete historical evidence artifacts."
        ),
        storage_lifecycle_hold=(
            "Keep dashboard snapshot/model-run metadata deletion on hold until event-risk-governor regeneration and downstream review are complete."
        ),
        required_next_actions=(
            "prepare_or_verify_required_event_feed_artifacts_for_each_fold_month",
            "materialize_model_03_event_state_event_inputs_from_reviewed_local_event_feeds",
            "generate_model_03_event_state_distribution_operator_outputs",
            "evaluate_m03_event_effect_model_channels_before_directional_claims",
            "record_manager_promotion_review_as_deferred_unless_real_gates_pass",
            "revisit_storage_lifecycle_deletion_holds_only_after_reviewed_regeneration_acceptance",
        ),
        source_documents=(FINAL_JUDGMENT_DOC, EVENT_FAMILY_PACKET_DOC, LAYER_CONTRACT_DOC),
    )


def write_report(report: EventModelAcceptanceReport, *, output: TextIO) -> None:
    json.dump(report.summary_row(), output, indent=2, sort_keys=True)
    output.write("\n")


def write_report_file(report: EventModelAcceptanceReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.summary_row(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "EventFamilyAcceptanceStatus",
    "EventModelAcceptanceReport",
    "build_event_model_acceptance_report",
    "write_report",
    "write_report_file",
]
