"""Close out the current fine-grained event-family scouting queue.

This module does not promote, train, activate, or mutate anything. It consumes the
existing local event-family catalog and available scouting artifacts, then assigns
every family a bounded disposition so the batch can move forward without
pretending blocked families have evidence.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

CONTRACT_TYPE = "event_family_remaining_closeout_v1"
SUMMARY_CONTRACT_TYPE = "event_family_remaining_closeout_summary_v1"
DEFAULT_CATALOG_PATH = Path("storage/event_family_batch_catalog_20260516/event_family_batch_catalog.json")
DEFAULT_OUTPUT_DIR = Path("storage/event_family_remaining_closeout_20260516")

RISK_ONLY_FAMILIES = {"earnings_guidance_scheduled_shell", "cpi_inflation_release"}
TEMPORARY_EVIDENCE_FAMILIES = {"cpi_inflation_release"}
DEFERRED_LOW_SIGNAL_FAMILIES = {"option_derivatives_abnormality"}
HIGH_PRIORITY_PACKET_CANDIDATES = {
    "equity_offering_dilution",
    "legal_regulatory_investigation",
    "credit_liquidity_stress",
    "fomc_rates_policy",
    "sector_regulation_policy",
    "mna_transaction",
    "accounting_restatement_or_fraud",
    "bankruptcy_or_restructuring",
}
RESIDUAL_DEFINITION_FAMILIES = {"price_action_pattern", "residual_market_structure_disturbance"}
LIQUIDITY_EVIDENCE_FAMILIES = {"microstructure_liquidity_disruption"}
EXPECTATION_BASELINE_FAMILIES = {
    "earnings_guidance_result_metrics",
    "earnings_guidance_raise_cut_or_withdrawal",
    "nfp_employment_release",
}

EVIDENCE_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "earnings_guidance_scheduled_shell": (
        "storage/earnings_guidance_event_alone_q4_2025_20260515/report.json",
        "docs/101_earnings_guidance_event_family_packet.md",
    ),
    "earnings_guidance_result_metrics": (
        "storage/earnings_guidance_readiness_scout_q4_2025_20260515/report.json",
        "storage/earnings_guidance_result_artifact_scout_q4_2025_20260515/report.json",
    ),
    "earnings_guidance_raise_cut_or_withdrawal": (
        "storage/earnings_guidance_current_prior_comparison_readiness_q4_2025_20260516/report.json",
        "storage/earnings_guidance_prior_guidance_exhibit_extraction_q4_2025_20260515/report.json",
    ),
    "cpi_inflation_release": (
        "storage/cpi_release_correlation_study_20260516/strict_summary.json",
        "storage/cpi_abnormal_release_correlation_study_20260516/abnormal_cpi_release_summary.json",
        "storage/cpi_surprise_correlation_study_20260516/cpi_surprise_summary.json",
        "storage/te_cpi_surprise_correlation_study_20260516/te_cpi_surprise_summary.json",
    ),
    "option_derivatives_abnormality": (
        "storage/option_activity_matched_control_study_20260515/",
        "storage/option_activity_strict_filter_study_20260515/",
        "storage/option_event_risk_amplifier_study_20260515/",
    ),
}


@dataclass(frozen=True)
class FamilyCloseoutRow:
    family_key: str
    routing_bucket: str
    mechanism_group: str
    priority: str
    prior_family_status: str
    prior_association_status: str
    closeout_status: str
    accepted_current_use: str
    blocked_use: str
    alpha_promotion_status: str
    risk_feature_status: str
    next_action_class: str
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    next_action: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        row = self.to_row()
        return {key: ";".join(value) if isinstance(value, tuple) else str(value) for key, value in row.items()}


@dataclass(frozen=True)
class RemainingCloseoutBatch:
    contract_type: str
    generated_at_utc: str
    family_rows: tuple[FamilyCloseoutRow, ...]
    provider_calls: int = 0
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
            "closeout_status_counts": _counts(row.closeout_status for row in self.family_rows),
            "alpha_promotion_status_counts": _counts(row.alpha_promotion_status for row in self.family_rows),
            "risk_feature_status_counts": _counts(row.risk_feature_status for row in self.family_rows),
            "next_action_class_counts": _counts(row.next_action_class for row in self.family_rows),
            "risk_candidate_family_keys": [
                row.family_key for row in self.family_rows if row.risk_feature_status.startswith("risk_candidate")
            ],
            "deferred_low_signal_family_keys": [row.family_key for row in self.family_rows if row.closeout_status == "deferred_low_signal"],
            "next_packet_queue": [row.family_key for row in self.family_rows if row.next_action_class == "build_family_packet"],
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "family_rows": [row.to_row() for row in self.family_rows],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_catalog(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    return [dict(item) for item in payload.get("candidates", [])]


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part for part in value.split(";") if part)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return tuple(out)


def _disposition(spec: Mapping[str, Any]) -> tuple[str, str, str, str, tuple[str, ...], str, str]:
    family = str(spec.get("family_key") or "")
    blockers = _as_tuple(spec.get("blocker_codes"))

    if family in DEFERRED_LOW_SIGNAL_FAMILIES:
        return (
            "deferred_low_signal",
            "alpha_blocked_controls_failed",
            "risk_blocked_current_definition_failed",
            "defer_until_definition_changes",
            blockers,
            "Do not spend more batch cycles on current option-abnormality definition; revisit only with a revised abnormality standard and new matched controls.",
            "Existing matched-control studies failed current promotion standard.",
        )
    if family == "cpi_inflation_release":
        return (
            "risk_only_candidate_temporary_evidence",
            "alpha_blocked_directional_signal_weak",
            "risk_candidate_macro_surprise_control",
            "use_as_control_feature_after_canonical_te_route",
            _dedupe((*blockers, "directional_alpha_not_proven", "canonical_te_expectation_history_needed")),
            "Keep CPI surprise as macro event-risk/control feature; build fuller TE expectation-history route before production canonicalization.",
            "Actual-vs-forecast surprise has event-risk/path relevance, but not standalone directional alpha.",
        )
    if family == "earnings_guidance_scheduled_shell":
        return (
            "risk_only_scouting_underpowered",
            "alpha_blocked_result_not_known_pre_event",
            "risk_candidate_scheduled_catalyst",
            "expand_controlled_shell_study",
            blockers,
            "Expand scheduled earnings shell study across more seasons/symbols with market/sector/target-state controls.",
            "Scheduled shell may matter for direction-neutral event risk, not signed alpha.",
        )
    if family in EXPECTATION_BASELINE_FAMILIES:
        return (
            "blocked_missing_pit_expectation_or_comparable_baseline",
            "alpha_blocked_missing_pit_baseline",
            "risk_blocked_missing_interpretation_baseline",
            "build_expectation_baseline",
            blockers,
            str(spec.get("next_action") or "Build point-in-time expectation/comparable baseline before association work."),
            "Cannot interpret surprise, raise/cut, or signed effect without point-in-time expected/comparable baseline.",
        )
    if family in RESIDUAL_DEFINITION_FAMILIES:
        return (
            "blocked_missing_residual_definition",
            "alpha_blocked_residual_not_defined",
            "risk_blocked_residual_not_defined",
            "define_residual_over_base_state",
            blockers,
            str(spec.get("next_action") or "Define residual over base market/sector/target state before labeling events."),
            "Price/action residual families must prove information beyond base state, not relearn normal price behavior.",
        )
    if family in LIQUIDITY_EVIDENCE_FAMILIES:
        return (
            "blocked_missing_liquidity_evidence",
            "alpha_not_applicable_execution_risk_family",
            "risk_blocked_missing_liquidity_labels",
            "build_liquidity_evidence_route",
            blockers,
            str(spec.get("next_action") or "Build liquidity/depth labels and execution-risk controls."),
            "Liquidity disruption needs depth/spread/execution-risk evidence, not only headline or bar returns.",
        )
    if family in HIGH_PRIORITY_PACKET_CANDIDATES:
        return (
            "packet_required_high_priority",
            "alpha_blocked_missing_family_packet",
            "risk_blocked_missing_family_packet",
            "build_family_packet",
            blockers,
            str(spec.get("next_action") or "Create event-family scouting packet and matched-control design."),
            "High-priority mechanism, but no accepted packet/interpreter/control set yet.",
        )
    if "missing_family_packet" in blockers or str(spec.get("association_status") or "").startswith("blocked_missing_family_packet"):
        return (
            "packet_required_normal_priority",
            "alpha_blocked_missing_family_packet",
            "risk_blocked_missing_family_packet",
            "build_family_packet",
            blockers,
            str(spec.get("next_action") or "Create event-family scouting packet before association work."),
            "Candidate remains a routing/mechanism idea until packet and controls exist.",
        )
    return (
        "review_required",
        "alpha_blocked_review_required",
        "risk_blocked_review_required",
        "manual_review",
        blockers,
        str(spec.get("next_action") or "Manual review required before continuing."),
        "No automatic closeout rule matched this family.",
    )


def build_event_family_remaining_closeout(
    *,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    generated_at_utc: str | None = None,
) -> RemainingCloseoutBatch:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    rows: list[FamilyCloseoutRow] = []
    for spec in _read_catalog(catalog_path):
        family = str(spec.get("family_key") or "")
        closeout, alpha_status, risk_status, next_class, blockers, next_action, disposition_note = _disposition(spec)
        evidence_refs = _dedupe((*_as_tuple(spec.get("evidence_refs")), *EVIDENCE_BY_FAMILY.get(family, ())))
        accepted_current_use = str(spec.get("accepted_current_use") or "")
        if family in TEMPORARY_EVIDENCE_FAMILIES:
            accepted_current_use = "temporary_macro_risk_surprise_evidence_pending_canonical_te_history"
        rows.append(
            FamilyCloseoutRow(
                family_key=family,
                routing_bucket=str(spec.get("routing_bucket") or ""),
                mechanism_group=str(spec.get("mechanism_group") or ""),
                priority=str(spec.get("priority") or ""),
                prior_family_status=str(spec.get("family_status") or ""),
                prior_association_status=str(spec.get("association_status") or ""),
                closeout_status=closeout,
                accepted_current_use=accepted_current_use,
                blocked_use=str(spec.get("blocked_use") or ""),
                alpha_promotion_status=alpha_status,
                risk_feature_status=risk_status,
                next_action_class=next_class,
                blocker_codes=blockers,
                evidence_refs=evidence_refs,
                next_action=f"{disposition_note} Next: {next_action}",
            )
        )
    return RemainingCloseoutBatch(contract_type=CONTRACT_TYPE, generated_at_utc=generated, family_rows=tuple(rows))


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_closeout_artifacts(batch: RemainingCloseoutBatch, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_family_remaining_closeout.json").write_text(
        json.dumps(batch.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_family_remaining_closeout_summary.json").write_text(
        json.dumps(batch.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    row_fields = list(FamilyCloseoutRow("", "", "", "", "", "", "", "", "", "", "", "", (), (), "").csv_row().keys())
    _write_csv(output_dir / "event_family_remaining_closeout.csv", [row.csv_row() for row in batch.family_rows], fieldnames=row_fields)
    packet_rows = [row.csv_row() for row in batch.family_rows if row.next_action_class == "build_family_packet"]
    _write_csv(output_dir / "event_family_next_packet_queue.csv", packet_rows, fieldnames=row_fields)
    (output_dir / "README.md").write_text(
        f"""# Event-family remaining closeout

Contract: `{batch.contract_type}`

This artifact closes the current fine-grained event-family batch by assigning all {len(batch.family_rows)} families a bounded disposition. It is not model training, promotion, or activation.

- Provider calls: {batch.provider_calls}
- Model activation performed: {batch.model_activation_performed}
- Broker execution performed: {batch.broker_execution_performed}
- Account mutation performed: {batch.account_mutation_performed}
- Artifact deletion performed: {batch.artifact_deletion_performed}

The closeout separates risk/control candidates from blocked packet work and deferred low-signal families. No family is promoted to standalone directional alpha.
""",
        encoding="utf-8",
    )


def write_batch(batch: RemainingCloseoutBatch, *, output: TextIO) -> None:
    json.dump(batch.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "FamilyCloseoutRow",
    "RemainingCloseoutBatch",
    "build_event_family_remaining_closeout",
    "write_batch",
    "write_closeout_artifacts",
]
