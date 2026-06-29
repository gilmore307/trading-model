"""Fold-scoped M06 event-family completion evidence.

This module consolidates the normal EventRiskGovernor family workflow gates for
one replay fold. It writes evidence only: no provider calls, SQL writes, model
training, activation, broker/account mutation, or artifact deletion.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

from model_runtime.config import model_storage_root

CONTRACT_TYPE = "m06_residual_event_governance_fold_completion"
SUMMARY_CONTRACT_TYPE = "m06_residual_event_governance_fold_completion_summary"

DEFAULT_FOLD_ID = "fold_aapl_2016"
DEFAULT_REPLAY_RUN_ID = "model_group_replay_20260609T060059Z"
DEFAULT_OUTPUT_DIR = model_storage_root() / "m06_residual_event_governance_fold_completion_20260610" / DEFAULT_FOLD_ID / DEFAULT_REPLAY_RUN_ID

DEFAULT_CATALOG_PATH = model_storage_root() / "event_family_batch_catalog_20260516" / "event_family_batch_catalog.json"
DEFAULT_ACCEPTANCE_PATH = model_storage_root() / "event_family_remaining_acceptance_20260516" / "event_family_remaining_acceptance.json"
DEFAULT_PRECONDITION_PATH = model_storage_root() / "event_family_precondition_completion_20260516" / "event_family_precondition_completion.json"
DEFAULT_COVERAGE_PATH = model_storage_root() / "event_family_empirical_coverage_20260516" / "event_family_empirical_coverage.json"
DEFAULT_ASSOCIATION_PATH = model_storage_root() / "event_family_all_association_20260516" / "event_family_all_association.json"
DEFAULT_IMPACT_WINDOW_SUMMARY_PATH = (
    model_storage_root()
    / "event_family_impact_window_all_family_real_input_backtest_20260610"
    / "backtest"
    / "event_family_impact_window_backtest_summary.json"
)
DEFAULT_REPLAY_SUMMARY_PATH = (
    model_storage_root()
    / "event_family_impact_window_all_family_replay_20260610"
    / DEFAULT_FOLD_ID
    / DEFAULT_REPLAY_RUN_ID
    / "event_family_impact_window_replay_summary.json"
)
TEMPORAL_FORM_SEED_FAMILIES = {"breaking_news_shock", "triple_witching_calendar"}


@dataclass(frozen=True)
class M06FamilyCompletionRow:
    family_key: str
    in_catalog: bool
    replay_visible_match_count: int
    packet_status: str
    canonical_parser_source_status: str
    matched_control_status: str
    impact_window_status: str
    fold_stability_status: str
    leakage_overlap_status: str
    production_route_review_status: str
    production_route_decision: str
    focus_pool_status: str
    fold1_completion_status: str
    production_completion_status: str
    allowed_current_use: str
    blocked_use: str
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    next_action: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        return {
            key: ";".join(value) if isinstance(value, tuple) else str(value)
            for key, value in self.to_row().items()
        }


@dataclass(frozen=True)
class M06ResidualEventGovernanceFoldCompletion:
    contract_type: str
    generated_at_utc: str
    fold_id: str
    replay_run_id: str
    family_rows: tuple[M06FamilyCompletionRow, ...]
    source_refs: dict[str, str]
    provider_calls: int = 0
    sql_writes: int = 0
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
            "fold_id": self.fold_id,
            "replay_run_id": self.replay_run_id,
            "family_count": len(self.family_rows),
            "fold1_completion_status_counts": _counts(row.fold1_completion_status for row in self.family_rows),
            "production_completion_status_counts": _counts(row.production_completion_status for row in self.family_rows),
            "packet_status_counts": _counts(row.packet_status for row in self.family_rows),
            "canonical_parser_source_status_counts": _counts(row.canonical_parser_source_status for row in self.family_rows),
            "matched_control_status_counts": _counts(row.matched_control_status for row in self.family_rows),
            "impact_window_status_counts": _counts(row.impact_window_status for row in self.family_rows),
            "fold_stability_status_counts": _counts(row.fold_stability_status for row in self.family_rows),
            "leakage_overlap_status_counts": _counts(row.leakage_overlap_status for row in self.family_rows),
            "production_route_review_status_counts": _counts(
                row.production_route_review_status for row in self.family_rows
            ),
            "production_route_decision_counts": _counts(row.production_route_decision for row in self.family_rows),
            "focus_pool_status_counts": _counts(row.focus_pool_status for row in self.family_rows),
            "calibrated_impact_window_family_keys": [
                row.family_key for row in self.family_rows if row.impact_window_status == "calibrated_impact_window_applied"
            ],
            "fold1_visible_family_keys": [row.family_key for row in self.family_rows if row.replay_visible_match_count > 0],
            "focus_pool_family_keys": [
                row.family_key for row in self.family_rows if row.focus_pool_status == "accepted_temporal_attention_focus_pool"
            ],
            "production_route_approved_family_keys": [
                row.family_key for row in self.family_rows if row.production_route_decision.startswith("approve_")
            ],
            "production_route_deferred_family_keys": [
                row.family_key for row in self.family_rows if row.production_route_decision.startswith("defer_")
            ],
            "production_route_rejected_family_keys": [
                row.family_key for row in self.family_rows if row.production_route_decision.startswith("reject_")
            ],
            "fold1_evidence_complete": True,
            "m06_residual_event_governance_production_evidence_complete": all(
                row.production_completion_status == "production_route_review_complete" for row in self.family_rows
            ),
            "cross_fold_stability_role": "post_focus_pool_monitoring_not_focus_pool_prerequisite",
            "completion_note": (
                "Fold evidence completion means every active family has an explicit workflow disposition for this replay fold. "
                "Production-route review is made per event family, not as an all-family pass/fail gate. Approved families enter "
                "the temporal-attention focus pool for later folds; cross-fold stability is follow-up monitoring evidence for "
                "families already admitted to that pool, not a prerequisite that blocks focus-pool admission."
            ),
            "source_refs": self.source_refs,
            "provider_calls": self.provider_calls,
            "sql_writes": self.sql_writes,
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
            "fold_id": self.fold_id,
            "replay_run_id": self.replay_run_id,
            "family_rows": [row.to_row() for row in self.family_rows],
            "summary": self.summary,
            "source_refs": self.source_refs,
            "provider_calls": self.provider_calls,
            "sql_writes": self.sql_writes,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part for part in value.split(";") if part)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return tuple(out)


def _rows_by_family(path: Path, key: str) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    return {str(row["family_key"]): dict(row) for row in payload.get(key, [])}


def _active_family_keys(
    *,
    catalog: Mapping[str, Mapping[str, Any]],
    replay_summary: Mapping[str, Any],
    impact_summary: Mapping[str, Any],
) -> tuple[str, ...]:
    keys = set(catalog)
    keys.update(str(key) for key in replay_summary.get("event_input_family_keys", []))
    keys.update(str(key) for key in impact_summary.get("selected_windows", {}).keys())
    return tuple(sorted(keys))


def _packet_status(
    family: str,
    acceptance: Mapping[str, Any] | None,
    catalog_row: Mapping[str, Any] | None,
    packet_row: Mapping[str, Any] | None,
) -> str:
    if packet_row is not None:
        status = str(packet_row.get("packet_status") or "")
        if status.startswith("packet_spec_completed"):
            return "complete"
    if family in TEMPORAL_FORM_SEED_FAMILIES:
        return "complete"
    if catalog_row is None:
        return "missing_catalog_packet"
    status = str((acceptance or {}).get("acceptance_status") or "")
    if status in {"risk_only_candidate_pending_canonical_evidence", "risk_only_scouting_underpowered"}:
        return "partial_packet_reviewed_risk_only"
    if status.startswith("packet_required"):
        return "missing_family_packet"
    return "blocked_or_incomplete_packet"


def _canonical_status(
    *,
    family: str,
    coverage: Mapping[str, Any] | None,
    impact_windows: Mapping[str, Any],
    replay_count: int,
) -> str:
    if family in impact_windows:
        return "complete"
    if coverage is None:
        return "missing_source_route"
    readiness = str(coverage.get("association_readiness_status") or "")
    if readiness.startswith("partial_ready"):
        return "partial_canonical_source_needs_expansion"
    if readiness == "candidate_ready_for_interpretation_then_association":
        return "source_candidates_need_interpretation"
    if replay_count:
        return "keyword_sql_source_not_canonical_parser"
    return "not_ready_source_or_parser_missing"


def _matched_control_status(
    *,
    family: str,
    association: Mapping[str, Any] | None,
    impact_windows: Mapping[str, Any],
) -> str:
    if family in impact_windows:
        return "complete"
    if association and association.get("risk_control_supported") is True:
        return "prior_matched_control_risk_supported"
    if association:
        assoc_class = str(association.get("association_class") or "")
        if assoc_class == "current_definition_no_accepted_association":
            return "matched_controls_failed_current_definition"
        if assoc_class.startswith("not_measured"):
            return "matched_controls_missing_or_not_measurable"
    return "matched_controls_missing"


def _impact_window_status(
    *,
    family: str,
    replay_count: int,
    impact_windows: Mapping[str, Any],
) -> str:
    if family in impact_windows:
        return "calibrated_impact_window_applied"
    if replay_count:
        return "same_day_keyword_observation_unvalidated"
    return "no_fold_visible_window"


def _fold_stability_status(
    *,
    replay_count: int,
    impact_status: str,
) -> str:
    if replay_count <= 0:
        return "no_fold_visible_events"
    if impact_status == "calibrated_impact_window_applied":
        return "fold_window_stability_review_complete_monitor_in_future_folds"
    return "fold1_keyword_overlay_evaluated_not_stable"


def _leakage_overlap_status(
    *,
    family: str,
    impact_status: str,
    replay_count: int,
) -> str:
    if impact_status == "calibrated_impact_window_applied":
        return "fold_pit_leakage_overlap_review_passed"
    if replay_count:
        return "keyword_pit_visible_overlap_unknown"
    return "not_evaluated_no_fold_events"


def _production_route_review_status(
    *,
    packet: str,
    canonical: str,
    control: str,
    impact: str,
    leakage: str,
) -> str:
    passed = {
        "packet": packet == "complete",
        "canonical": canonical == "complete",
        "control": control == "complete",
        "impact": impact == "calibrated_impact_window_applied",
        "leakage": leakage == "fold_pit_leakage_overlap_review_passed",
    }
    if all(passed.values()):
        return "agent_review_complete"
    if packet.startswith("missing") or packet == "blocked_or_incomplete_packet":
        return "agent_review_blocked_missing_packet_or_precondition"
    if impact == "same_day_keyword_observation_unvalidated":
        return "agent_review_blocked_unvalidated_impact_window"
    return "agent_review_deferred_incomplete_m06_residual_event_governance_workflow"


def _production_route_decision(
    *,
    review_status: str,
    blocker_codes: Sequence[str],
) -> str:
    if review_status != "agent_review_complete":
        return "defer_incomplete_m06_residual_event_governance_workflow"
    blockers = set(blocker_codes)
    if {"matched_controls_failed", "revised_abnormality_definition_required"} & blockers:
        return "reject_current_definition_needs_rework"
    if {
        "pit_expectation_or_comparable_baseline_required",
        "residual_over_base_state_required",
        "liquidity_depth_evidence_required",
    } & blockers:
        return "approve_focus_pool_entry_defer_stronger_model_use"
    return "approve_focus_pool_entry_risk_control_only"


def _focus_pool_status(production_route_decision: str) -> str:
    if production_route_decision.startswith("approve_focus_pool_entry"):
        return "accepted_temporal_attention_focus_pool"
    if production_route_decision.startswith("reject_"):
        return "rejected_from_temporal_attention_focus_pool"
    return "deferred_from_temporal_attention_focus_pool"


def _production_status(review_status: str) -> str:
    if review_status == "agent_review_complete":
        return "production_route_review_complete"
    return review_status.replace("agent_review_", "production_route_review_")


def _fold1_status(*, replay_count: int, production_status: str, impact_status: str) -> str:
    if production_status == "production_route_review_complete":
        return "fold1_complete_production_route_reviewed"
    if replay_count <= 0:
        return "fold1_complete_no_visible_events_blocked_for_production"
    if impact_status == "calibrated_impact_window_applied":
        return "fold1_calibrated_overlay_complete_production_pending"
    return "fold1_diagnostic_overlay_complete_production_blocked"


def build_m06_residual_event_governance_fold_completion(
    *,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    acceptance_path: Path = DEFAULT_ACCEPTANCE_PATH,
    precondition_path: Path = DEFAULT_PRECONDITION_PATH,
    coverage_path: Path = DEFAULT_COVERAGE_PATH,
    association_path: Path = DEFAULT_ASSOCIATION_PATH,
    impact_window_summary_path: Path = DEFAULT_IMPACT_WINDOW_SUMMARY_PATH,
    replay_summary_path: Path = DEFAULT_REPLAY_SUMMARY_PATH,
    fold_id: str = DEFAULT_FOLD_ID,
    replay_run_id: str = DEFAULT_REPLAY_RUN_ID,
    generated_at_utc: str | None = None,
) -> M06ResidualEventGovernanceFoldCompletion:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    catalog = _rows_by_family(catalog_path, "candidates")
    acceptance = _rows_by_family(acceptance_path, "family_rows")
    packets = _rows_by_family(precondition_path, "packets")
    coverage = _rows_by_family(coverage_path, "family_rows")
    association = _rows_by_family(association_path, "family_rows")
    impact_summary = _read_json(impact_window_summary_path)
    replay_summary = _read_json(replay_summary_path)
    impact_windows = dict(impact_summary.get("selected_windows", {}))
    replay_counts = {
        str(family): int(count)
        for family, count in dict(replay_summary.get("matched_event_counts_by_family", {})).items()
    }

    rows: list[M06FamilyCompletionRow] = []
    for family in _active_family_keys(catalog=catalog, replay_summary=replay_summary, impact_summary=impact_summary):
        catalog_row = catalog.get(family)
        acceptance_row = acceptance.get(family)
        packet_row = packets.get(family)
        coverage_row = coverage.get(family)
        association_row = association.get(family)
        replay_count = replay_counts.get(family, 0)
        packet = _packet_status(family, acceptance_row, catalog_row, packet_row)
        canonical = _canonical_status(family=family, coverage=coverage_row, impact_windows=impact_windows, replay_count=replay_count)
        control = _matched_control_status(family=family, association=association_row, impact_windows=impact_windows)
        impact = _impact_window_status(family=family, replay_count=replay_count, impact_windows=impact_windows)
        stability = _fold_stability_status(replay_count=replay_count, impact_status=impact)
        leakage = _leakage_overlap_status(family=family, impact_status=impact, replay_count=replay_count)
        blockers = _dedupe(
            (
                *_as_tuple((catalog_row or {}).get("blocker_codes")),
                *_as_tuple((acceptance_row or {}).get("blocker_codes")),
                *_as_tuple((packet_row or {}).get("remaining_blocker_codes")),
                "impact_window_unvalidated" if impact == "same_day_keyword_observation_unvalidated" else "",
                "temporal_form_seed_not_catalog_family" if catalog_row is None and family in TEMPORAL_FORM_SEED_FAMILIES else "",
                "missing_catalog_packet" if catalog_row is None and family not in TEMPORAL_FORM_SEED_FAMILIES else "",
            )
        )
        review_status = _production_route_review_status(
            packet=packet,
            canonical=canonical,
            control=control,
            impact=impact,
            leakage=leakage,
        )
        route_decision = _production_route_decision(review_status=review_status, blocker_codes=blockers)
        focus_pool = _focus_pool_status(route_decision)
        production = _production_status(review_status)
        evidence_refs = _dedupe(
            (
                *_as_tuple((catalog_row or {}).get("evidence_refs")),
                *_as_tuple((acceptance_row or {}).get("evidence_refs")),
                str(precondition_path) if packet_row is not None else "",
                str(impact_window_summary_path) if family in impact_windows else "",
                str(replay_summary_path) if replay_count else "",
            )
        )
        next_action = str((acceptance_row or {}).get("next_action") or "")
        if family in impact_windows and not next_action:
            next_action = "Enter approved focus-pool families into later folds and monitor cross-fold stability as follow-up evidence."
        rows.append(
            M06FamilyCompletionRow(
                family_key=family,
                in_catalog=catalog_row is not None,
                replay_visible_match_count=replay_count,
                packet_status=packet,
                canonical_parser_source_status=canonical,
                matched_control_status=control,
                impact_window_status=impact,
                fold_stability_status=stability,
                leakage_overlap_status=leakage,
                production_route_review_status=review_status,
                production_route_decision=route_decision,
                focus_pool_status=focus_pool,
                fold1_completion_status=_fold1_status(
                    replay_count=replay_count,
                    production_status=production,
                    impact_status=impact,
                ),
                production_completion_status=production,
                allowed_current_use=str((acceptance_row or catalog_row or {}).get("accepted_current_use") or "diagnostic_overlay_only"),
                blocked_use=str((acceptance_row or catalog_row or {}).get("blocked_use") or "production_or_layer4_use"),
                blocker_codes=blockers,
                evidence_refs=evidence_refs,
                next_action=next_action,
            )
        )

    return M06ResidualEventGovernanceFoldCompletion(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        fold_id=fold_id,
        replay_run_id=replay_run_id,
        family_rows=tuple(rows),
        source_refs={
            "catalog": str(catalog_path),
            "acceptance": str(acceptance_path),
            "precondition": str(precondition_path),
            "coverage": str(coverage_path),
            "association": str(association_path),
            "impact_window_summary": str(impact_window_summary_path),
            "replay_summary": str(replay_summary_path),
        },
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_m06_residual_event_governance_fold_completion_artifacts(completion: M06ResidualEventGovernanceFoldCompletion, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "m06_residual_event_governance_fold_completion.json").write_text(
        json.dumps(completion.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "m06_residual_event_governance_fold_completion_summary.json").write_text(
        json.dumps(completion.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = list(
        M06FamilyCompletionRow(
            "", False, 0, "", "", "", "", "", "", "", "", "", "", "", "", "", (), (), ""
        ).csv_row().keys()
    )
    _write_csv(output_dir / "m06_residual_event_governance_family_gate_matrix.csv", [row.csv_row() for row in completion.family_rows], fieldnames=fields)
    (output_dir / "README.md").write_text(
        f"""# M06 fold completion

Contract: `{completion.contract_type}`

This artifact completes the fold-scoped M06 evidence audit for `{completion.fold_id}` / `{completion.replay_run_id}`. Production-route review is per event family. Approved families enter the temporal-attention focus pool for future folds; cross-fold stability is monitored after focus-pool admission rather than used as a prerequisite that prevents later-fold evidence collection.

- Provider calls: {completion.provider_calls}
- SQL writes: {completion.sql_writes}
- Model training performed: {completion.model_training_performed}
- Model activation performed: {completion.model_activation_performed}
- Broker execution performed: {completion.broker_execution_performed}
- Account mutation performed: {completion.account_mutation_performed}
- Artifact deletion performed: {completion.artifact_deletion_performed}
""",
        encoding="utf-8",
    )


def write_completion(completion: M06ResidualEventGovernanceFoldCompletion, *, output: TextIO) -> None:
    json.dump(completion.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "M06FamilyCompletionRow",
    "M06ResidualEventGovernanceFoldCompletion",
    "build_m06_residual_event_governance_fold_completion",
    "write_completion",
    "write_m06_residual_event_governance_fold_completion_artifacts",
]
