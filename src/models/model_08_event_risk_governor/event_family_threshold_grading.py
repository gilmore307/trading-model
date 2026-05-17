"""Threshold/grading preparation for EventRiskGovernor event families.

This is a queue-shaping artifact: it removes measured no-association families from
next threshold/grading work while preserving audit rows. It performs no provider
calls, training, activation, broker/account mutation, destructive SQL, artifact
or source deletion.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

CONTRACT_TYPE = "event_family_threshold_grading_v1"
SUMMARY_CONTRACT_TYPE = "event_family_threshold_grading_summary_v1"
DEFAULT_ASSOCIATION_DIR = Path("storage/event_family_all_association_20260516")
DEFAULT_OUTPUT_DIR = Path("storage/event_family_threshold_grading_20260516")

ACCEPTED_RISK_CONTROL = "accepted_risk_control"
THRESHOLD_REVIEW = "threshold_review_candidate"
RETIRED_NO_ASSOCIATION = "retired_no_clear_local_association"
RETIRED_DEFINITION = "retired_current_definition_no_accepted_association"
HOLD_THIN = "hold_thin_unstable_screening"
BLOCKED = "blocked_required_data_or_precondition"


@dataclass(frozen=True)
class ThresholdGradingRow:
    family_key: str
    queue_status: str
    threshold_grade_seed: str
    active_threshold_universe: bool
    delete_from_threshold_queue: bool
    association_class: str
    screening_stability_status: str
    event_count: int
    max_label_count: int
    risk_material_metric_count: int
    positive_direction_horizon_count: int
    negative_direction_horizon_count: int
    deletion_scope: str
    threshold_next_action: str
    evidence_note: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in self.to_row().items():
            out[key] = str(value).lower() if isinstance(value, bool) else str(value)
        return out


@dataclass(frozen=True)
class EventFamilyThresholdGrading:
    contract_type: str
    generated_at_utc: str
    source_association_dir: str
    family_rows: tuple[ThresholdGradingRow, ...]
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
            "queue_status_counts": _counts(row.queue_status for row in self.family_rows),
            "active_threshold_universe": [row.family_key for row in self.family_rows if row.active_threshold_universe],
            "deleted_from_threshold_queue": [row.family_key for row in self.family_rows if row.delete_from_threshold_queue],
            "retirement_note": "Delete means remove from the next active threshold/grading queue while preserving audit artifacts and evidence rows.",
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
            "source_association_dir": self.source_association_dir,
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


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _int(row: Mapping[str, str], key: str) -> int:
    try:
        return int(row.get(key) or 0)
    except ValueError:
        return 0


def _classify(row: Mapping[str, str]) -> tuple[str, str, bool, bool, str, str, str]:
    family = row["family_key"]
    stability = row["screening_stability_status"]
    assoc = row["association_class"]
    if stability == "accepted_risk_control_prior_study":
        return (
            ACCEPTED_RISK_CONTROL,
            "A_risk_control",
            True,
            False,
            "none",
            "Set risk/path thresholds from accepted prior study; do not create standalone directional-alpha grade.",
            "Accepted risk/control association from reviewed prior study.",
        )
    if stability == "expanded_screening_threshold_review_candidate":
        grade = "B_screening_candidate" if _int(row, "risk_material_metric_count") >= 2 else "C_screening_candidate"
        return (
            THRESHOLD_REVIEW,
            grade,
            True,
            False,
            "none",
            "Enter threshold/grading calibration with family-specific canonical parser, dedup, and matched controls required before acceptance.",
            "Expanded local screening is strong enough to keep in the next threshold-review queue, but not accepted for model use.",
        )
    if stability == "measured_no_clear_local_stability" or assoc == "no_clear_local_association":
        return (
            RETIRED_NO_ASSOCIATION,
            "Reject_no_clear_association",
            False,
            True,
            "threshold_queue_only",
            "Remove from active threshold/grading queue; preserve audit row and revisit only if a materially better source/parser changes the evidence basis.",
            "Measured local expanded screening did not show clear risk/path/directional association.",
        )
    if stability == "definition_revision_required" or assoc == "current_definition_no_accepted_association":
        return (
            RETIRED_DEFINITION,
            "Reject_current_definition",
            False,
            True,
            "current_definition_only",
            "Delete the current definition from threshold work; define a new abnormality standard before retesting.",
            f"{family} current definition has no accepted association and should not enter threshold grading.",
        )
    if stability == "thin_unstable_screening":
        return (
            HOLD_THIN,
            "Hold_thin_unstable",
            False,
            False,
            "none",
            "Do not threshold yet; require more source coverage and stability before re-entry.",
            "Local signal is too thin or unstable for threshold grading.",
        )
    return (
        BLOCKED,
        "Blocked",
        False,
        False,
        "none",
        "Do not threshold until required data/precondition route is completed.",
        "Missing local labels, PIT baseline, residual detector, or liquidity-depth evidence.",
    )


def build_event_family_threshold_grading(
    *,
    association_dir: Path = DEFAULT_ASSOCIATION_DIR,
    generated_at_utc: str | None = None,
) -> EventFamilyThresholdGrading:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    stability_rows = _read_csv(association_dir / "event_family_expanded_stability.csv")
    rows: list[ThresholdGradingRow] = []
    for source in stability_rows:
        status, grade, active, delete, deletion_scope, next_action, note = _classify(source)
        rows.append(
            ThresholdGradingRow(
                family_key=source["family_key"],
                queue_status=status,
                threshold_grade_seed=grade,
                active_threshold_universe=active,
                delete_from_threshold_queue=delete,
                association_class=source["association_class"],
                screening_stability_status=source["screening_stability_status"],
                event_count=_int(source, "event_count"),
                max_label_count=_int(source, "max_label_count"),
                risk_material_metric_count=_int(source, "risk_material_metric_count"),
                positive_direction_horizon_count=_int(source, "positive_direction_horizon_count"),
                negative_direction_horizon_count=_int(source, "negative_direction_horizon_count"),
                deletion_scope=deletion_scope,
                threshold_next_action=next_action,
                evidence_note=note,
            )
        )
    return EventFamilyThresholdGrading(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        source_association_dir=str(association_dir),
        family_rows=tuple(rows),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_event_family_threshold_grading_artifacts(grading: EventFamilyThresholdGrading, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_family_threshold_grading.json").write_text(
        json.dumps(grading.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_family_threshold_grading_summary.json").write_text(
        json.dumps(grading.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = list(
        ThresholdGradingRow("", "", "", False, False, "", "", 0, 0, 0, 0, 0, "", "", "").csv_row().keys()
    )
    _write_csv(output_dir / "event_family_threshold_grading.csv", [row.csv_row() for row in grading.family_rows], fieldnames=fields)
    (output_dir / "README.md").write_text(
        f"""# Event-family threshold grading queue

Contract: `{grading.contract_type}`

This artifact shapes the next threshold/grading queue. Families with measured no-clear local association are deleted from the active threshold queue, not physically deleted from evidence storage. No provider calls, model training, activation, broker/account mutation, artifact deletion, or destructive SQL are performed.
""",
        encoding="utf-8",
    )


def write_grading(grading: EventFamilyThresholdGrading, *, output: TextIO) -> None:
    json.dump(grading.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "EventFamilyThresholdGrading",
    "ThresholdGradingRow",
    "build_event_family_threshold_grading",
    "write_event_family_threshold_grading_artifacts",
    "write_grading",
]
