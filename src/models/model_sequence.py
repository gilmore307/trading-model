"""Concise ordered model sequence for the current trading-model stack."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

MODEL_SEQUENCE_CONTRACT = "trading_model_sequence"


@dataclass(frozen=True)
class ModelSequenceEntry:
    """One display/order row for the current model stack."""

    model_step: str
    model_name: str
    model_id: str
    model_surface: str
    conceptual_output: str

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["contract_type"] = MODEL_SEQUENCE_CONTRACT
        return row


def model_sequence() -> tuple[ModelSequenceEntry, ...]:
    """Return the accepted six-model stack sequence."""

    return (
        ModelSequenceEntry(
            model_step="M01",
            model_name="Background Context",
            model_id="background_context_model",
            model_surface="model_01_background_context",
            conceptual_output="background_context_state",
        ),
        ModelSequenceEntry(
            model_step="M02",
            model_name="Target State",
            model_id="target_state_model",
            model_surface="model_02_target_state",
            conceptual_output="target_context_state",
        ),
        ModelSequenceEntry(
            model_step="M03",
            model_name="Event State",
            model_id="event_state_model",
            model_surface="model_03_event_state",
            conceptual_output="event_state_vector",
        ),
        ModelSequenceEntry(
            model_step="M04",
            model_name="Unified Decision",
            model_id="unified_decision_model",
            model_surface="model_04_unified_decision",
            conceptual_output="unified_decision_vector",
        ),
        ModelSequenceEntry(
            model_step="M05",
            model_name="Option Expression",
            model_id="option_expression_model",
            model_surface="model_05_option_expression",
            conceptual_output="option_expression_plan",
        ),
        ModelSequenceEntry(
            model_step="M06",
            model_name="Residual Event Governance",
            model_id="residual_event_governance_model",
            model_surface="model_06_residual_event_governance",
            conceptual_output="event_risk_intervention",
        ),
    )


def model_sequence_rows() -> list[dict[str, Any]]:
    """Return serializable six-model sequence rows."""

    return [entry.to_dict() for entry in model_sequence()]


__all__ = ["MODEL_SEQUENCE_CONTRACT", "ModelSequenceEntry", "model_sequence", "model_sequence_rows"]
