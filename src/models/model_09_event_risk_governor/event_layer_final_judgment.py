"""Finalize the EventRiskGovernor model posture from local evidence.

This module does not train or activate anything. It consolidates the reviewed
local scouting artifacts into an explicit final architecture judgment so the
project can decide what the event layer is allowed to be now.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

CONTRACT_TYPE = "event_layer_final_judgment_v1"
SUMMARY_CONTRACT_TYPE = "event_layer_final_judgment_summary_v1"
DEFAULT_COVERAGE_PATH = Path("storage/event_family_empirical_coverage_20260516/event_family_empirical_coverage.json")
DEFAULT_OUTPUT_DIR = Path("storage/event_layer_final_judgment_20260516")

EARNINGS_EVENT_ALONE_REPORT = Path("storage/earnings_guidance_event_alone_q4_2025_20260515/report.json")
CPI_SURPRISE_REPORT = Path("storage/cpi_surprise_correlation_study_20260516/cpi_surprise_summary.json")
TE_CPI_SURPRISE_REPORT = Path("storage/te_cpi_surprise_correlation_study_20260516/te_cpi_surprise_summary.json")
OPTION_MATCHED_CONTROL_REPORT = Path("storage/option_activity_matched_control_study_20260515/report.json")

FINAL_MODEL_POSTURE = "build_event_risk_governor_not_standalone_event_alpha"
FINAL_ALPHA_DECISION = "reject_standalone_directional_event_alpha_for_current_evidence"
FINAL_RISK_DECISION = "accept_bounded_event_risk_intelligence_overlay"
FINAL_TRAINING_DECISION = "do_not_train_or_activate_event_alpha_model"

ALLOWED_OUTPUTS = (
    "canonical_event_presence_and_lifecycle_state",
    "event_family_identity_and_evidence_quality",
    "event_risk_score_or_bucket",
    "uncertainty_increase_hint",
    "path_volatility_or_gap_risk_hint",
    "liquidity_or_execution_risk_hint_when_evidence_exists",
    "human_review_required_flag",
    "entry_block_or_exposure_cap_hint",
    "reduce_or_flatten_review_candidate",
    "audit_explanation_and_source_refs",
)

PROHIBITED_OUTPUTS = (
    "standalone_buy_sell_hold",
    "directional_alpha_override",
    "position_size",
    "target_exposure",
    "option_contract_selection",
    "order_type_or_broker_instruction",
    "broker_account_mutation",
    "automatic_model_activation",
    "artifact_deletion_or_sql_lifecycle_mutation",
)


@dataclass(frozen=True)
class FamilyFinalDisposition:
    family_key: str
    final_disposition: str
    current_use: str
    promotion_status: str
    evidence_basis: tuple[str, ...]
    blockers: tuple[str, ...]
    next_required_evidence: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        row = self.to_row()
        return {key: ";".join(value) if isinstance(value, tuple) else str(value) for key, value in row.items()}


@dataclass(frozen=True)
class EventLayerFinalJudgment:
    contract_type: str
    generated_at_utc: str
    source_coverage_path: str
    final_model_posture: str
    final_alpha_decision: str
    final_risk_decision: str
    final_training_decision: str
    final_short_answer: str
    allowed_outputs: tuple[str, ...]
    prohibited_outputs: tuple[str, ...]
    family_dispositions: tuple[FamilyFinalDisposition, ...]
    headline_evidence: dict[str, Any]
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
            "final_model_posture": self.final_model_posture,
            "final_alpha_decision": self.final_alpha_decision,
            "final_risk_decision": self.final_risk_decision,
            "final_training_decision": self.final_training_decision,
            "final_short_answer": self.final_short_answer,
            "family_count": len(self.family_dispositions),
            "family_disposition_counts": _counts(row.final_disposition for row in self.family_dispositions),
            "promotion_status_counts": _counts(row.promotion_status for row in self.family_dispositions),
            "risk_or_control_families_now": [
                row.family_key for row in self.family_dispositions if row.promotion_status == "accepted_for_risk_or_control_only"
            ],
            "standalone_alpha_families_now": [
                row.family_key for row in self.family_dispositions if row.promotion_status == "accepted_for_standalone_alpha"
            ],
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
            "source_coverage_path": self.source_coverage_path,
            "final_model_posture": self.final_model_posture,
            "final_alpha_decision": self.final_alpha_decision,
            "final_risk_decision": self.final_risk_decision,
            "final_training_decision": self.final_training_decision,
            "final_short_answer": self.final_short_answer,
            "allowed_outputs": list(self.allowed_outputs),
            "prohibited_outputs": list(self.prohibited_outputs),
            "family_dispositions": [row.to_row() for row in self.family_dispositions],
            "headline_evidence": self.headline_evidence,
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _first_stat(report: Mapping[str, Any]) -> Mapping[str, Any]:
    stats = report.get("group_stats") or report.get("summary") or []
    if isinstance(stats, list) and stats:
        return stats[0]
    return {}


def _evidence_tuple(*items: str | None) -> tuple[str, ...]:
    return tuple(item for item in items if item)


def _family_disposition(row: Mapping[str, Any]) -> FamilyFinalDisposition:
    family = str(row.get("family_key") or "")
    coverage = str(row.get("coverage_status") or "")
    readiness = str(row.get("association_readiness_status") or "")
    artifacts = tuple(str(item) for item in row.get("existing_empirical_artifacts", []) if str(item))
    blockers = tuple(str(item) for item in row.get("remaining_blocker_codes", []) if str(item))
    candidates = int(row.get("local_candidate_count") or 0)

    if family == "cpi_inflation_release":
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="risk_control_feature_accepted_not_alpha",
            current_use="macro_event_risk_and_surprise_control",
            promotion_status="accepted_for_risk_or_control_only",
            evidence_basis=_evidence_tuple(
                "actual_vs_expectation_surprise_has_path_risk_relevance",
                "TE_fields_confirmed_but_visible_history_sparse",
                *artifacts,
            ),
            blockers=("fuller_te_expectation_history_required_before_canonical_replacement",),
            next_required_evidence="Complete fuller TE expectation-history path before using TE as the only canonical CPI surprise source.",
        )
    if family == "earnings_guidance_scheduled_shell":
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="direction_neutral_event_risk_context_only",
            current_use="scheduled_event_window_risk_and_path_volatility_context",
            promotion_status="accepted_for_risk_or_control_only",
            evidence_basis=_evidence_tuple("earnings_shell_path_range_elevated_direction_not_supported", *artifacts),
            blockers=("underpowered_sample", "missing_current_comparable_guidance", "missing_pit_expectation_baseline"),
            next_required_evidence="Expand across seasons/symbols and join accepted current guidance/result interpretation plus PIT baselines.",
        )
    if family == "option_derivatives_abnormality":
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="deferred_low_signal_revise_definition",
            current_use="provenance_and_risk_context_only",
            promotion_status="rejected_for_current_alpha_or_risk_promotion",
            evidence_basis=_evidence_tuple("matched_controls_do_not_clear_current_abnormality_definition", *artifacts),
            blockers=("current_option_abnormality_standard_saturated_or_noisy", "clean_control_design_failed"),
            next_required_evidence="Revise abnormality definition and rerun matched controls before any event-model use beyond provenance.",
        )
    if "pit_expectation_or_comparable_baseline_required" in blockers:
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="blocked_missing_pit_baseline",
            current_use="not_usable_for_model_output_now",
            promotion_status="blocked_no_promotion",
            evidence_basis=artifacts or (f"local_candidate_count={candidates}",),
            blockers=blockers,
            next_required_evidence="Build PIT expectation/comparable baseline artifacts before signed or abnormal association claims.",
        )
    if "residual_over_base_state_required" in blockers:
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="blocked_missing_residual_detector",
            current_use="not_usable_for_model_output_now",
            promotion_status="blocked_no_promotion",
            evidence_basis=(f"local_candidate_count={candidates}",),
            blockers=blockers,
            next_required_evidence="Define residual-over-base-state detector and then rerun family labels/controls.",
        )
    if "liquidity_depth_evidence_required" in blockers:
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="blocked_missing_liquidity_depth_evidence",
            current_use="not_usable_for_model_output_now",
            promotion_status="blocked_no_promotion",
            evidence_basis=(f"local_candidate_count={candidates}",),
            blockers=blockers,
            next_required_evidence="Build liquidity/depth evidence route before any model output use.",
        )
    if coverage == "local_candidates_found_interpretation_required":
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="candidate_events_found_needs_family_study",
            current_use="research_queue_only",
            promotion_status="blocked_no_promotion",
            evidence_basis=(f"local_candidate_count={candidates}", readiness),
            blockers=("needs_canonical_interpretation", "needs_dedup", "needs_matched_controls", "needs_price_path_labels"),
            next_required_evidence="Interpret candidate events, deduplicate canonical events, and run matched-control association study.",
        )
    if coverage == "no_local_candidate_events_found_under_current_sources":
        return FamilyFinalDisposition(
            family_key=family,
            final_disposition="source_or_parser_gap",
            current_use="not_usable_for_model_output_now",
            promotion_status="blocked_no_promotion",
            evidence_basis=("no_local_candidate_events_under_current_sources",),
            blockers=("source_or_parser_gap",),
            next_required_evidence="Add accepted source/parser coverage and rerun empirical coverage before association.",
        )
    return FamilyFinalDisposition(
        family_key=family,
        final_disposition="blocked_no_final_family_claim",
        current_use="not_usable_for_model_output_now",
        promotion_status="blocked_no_promotion",
        evidence_basis=_evidence_tuple(coverage, readiness, *artifacts),
        blockers=blockers or ("insufficient_family_specific_evidence",),
        next_required_evidence=str(row.get("next_action") or "Run accepted family-specific empirical association study."),
    )


def _headline_evidence(model_root: Path, coverage: Mapping[str, Any]) -> dict[str, Any]:
    earnings = _read_json(model_root / EARNINGS_EVENT_ALONE_REPORT)
    earnings_stat = _first_stat(earnings)
    cpi = _read_json(model_root / CPI_SURPRISE_REPORT)
    cpi_large = next((row for row in cpi.get("summary", []) if row.get("subset") == "large_surprise_0_2pp_h1"), {})
    te_cpi = _read_json(model_root / TE_CPI_SURPRISE_REPORT)
    option = _read_json(model_root / OPTION_MATCHED_CONTROL_REPORT)
    option_stat = _first_stat(option)
    return {
        "coverage_summary": coverage.get("summary", {}),
        "earnings_guidance_scheduled_shell": {
            "event_window_count": earnings.get("event_window_count"),
            "control_window_count": earnings.get("control_window_count"),
            "avg_delta_path_range_5d": earnings_stat.get("avg_delta_path_range_5d"),
            "avg_delta_directional_fwd_5d": earnings_stat.get("avg_delta_directional_fwd_5d"),
            "judgment": "direction_neutral_path_risk_context_not_directional_alpha",
        },
        "cpi_inflation_release": {
            "investing_release_dates": cpi.get("release_dates"),
            "large_surprise_0_2pp_dates": cpi.get("large_surprise_0_2pp_dates"),
            "large_surprise_0_2pp_mean_path_delta": cpi_large.get("mean_path_delta"),
            "large_surprise_0_2pp_mean_abs_delta": cpi_large.get("mean_abs_delta"),
            "large_surprise_0_2pp_mean_ret_delta": cpi_large.get("mean_ret_delta"),
            "te_release_dates_with_expectations": te_cpi.get("release_dates"),
            "te_metric_rows_with_expectation": te_cpi.get("cpi_metric_rows_with_expectation"),
            "judgment": "macro_event_risk_control_not_standalone_alpha",
        },
        "option_derivatives_abnormality": {
            "abnormal_window_count": option.get("abnormal_window_count"),
            "control_window_count": option.get("control_window_count"),
            "avg_delta_path_range_5d": option_stat.get("avg_delta_path_range_5d"),
            "avg_delta_directional_fwd_5d": option_stat.get("avg_delta_directional_fwd_5d"),
            "judgment": "deferred_low_signal_current_definition_not_promoted",
        },
    }


def build_event_layer_final_judgment(
    *,
    coverage_path: Path = DEFAULT_COVERAGE_PATH,
    model_root: Path = Path("."),
    generated_at_utc: str | None = None,
) -> EventLayerFinalJudgment:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    coverage = _read_json(coverage_path)
    rows = coverage.get("family_rows", [])
    dispositions = tuple(_family_disposition(row) for row in rows)
    return EventLayerFinalJudgment(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        source_coverage_path=str(coverage_path),
        final_model_posture=FINAL_MODEL_POSTURE,
        final_alpha_decision=FINAL_ALPHA_DECISION,
        final_risk_decision=FINAL_RISK_DECISION,
        final_training_decision=FINAL_TRAINING_DECISION,
        final_short_answer=(
            "Build the event layer now only as EventRiskGovernor/EventIntelligenceOverlay. "
            "Do not build or train a standalone event alpha model under current evidence."
        ),
        allowed_outputs=ALLOWED_OUTPUTS,
        prohibited_outputs=PROHIBITED_OUTPUTS,
        family_dispositions=dispositions,
        headline_evidence=_headline_evidence(model_root.resolve(), coverage),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_event_layer_final_judgment_artifacts(judgment: EventLayerFinalJudgment, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_layer_final_judgment.json").write_text(
        json.dumps(judgment.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_layer_final_judgment_summary.json").write_text(
        json.dumps(judgment.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = list(FamilyFinalDisposition("", "", "", "", (), (), "").csv_row().keys())
    _write_csv(
        output_dir / "event_family_final_dispositions.csv",
        [row.csv_row() for row in judgment.family_dispositions],
        fieldnames=fields,
    )
    _write_csv(
        output_dir / "event_layer_allowed_prohibited_outputs.csv",
        [{"kind": "allowed", "output": item} for item in judgment.allowed_outputs]
        + [{"kind": "prohibited", "output": item} for item in judgment.prohibited_outputs],
        fieldnames=["kind", "output"],
    )
    (output_dir / "README.md").write_text(
        f"""# Event layer final judgment

Contract: `{judgment.contract_type}`

Final posture: `{judgment.final_model_posture}`

Short answer: {judgment.final_short_answer}

This artifact finalizes the current event-model decision from local reviewed evidence. It does not perform provider calls, model training, model activation, broker/account mutation, destructive SQL, or artifact deletion.

Standalone alpha families accepted now: `{len(judgment.summary['standalone_alpha_families_now'])}`.
Risk/control families accepted now: `{';'.join(judgment.summary['risk_or_control_families_now'])}`.
""",
        encoding="utf-8",
    )


def write_judgment(judgment: EventLayerFinalJudgment, *, output: TextIO) -> None:
    json.dump(judgment.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "EventLayerFinalJudgment",
    "FamilyFinalDisposition",
    "build_event_layer_final_judgment",
    "write_event_layer_final_judgment_artifacts",
    "write_judgment",
]
