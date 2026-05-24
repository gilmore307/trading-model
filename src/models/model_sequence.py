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
    """Return the accepted M01-M10 model stack sequence."""

    return (
        ModelSequenceEntry(
            model_step="M01",
            model_name="Market Regime",
            model_id="market_regime_model",
            model_surface="model_01_market_regime",
            conceptual_output="market_context_state",
        ),
        ModelSequenceEntry(
            model_step="M02",
            model_name="Sector Context",
            model_id="sector_context_model",
            model_surface="model_02_sector_context",
            conceptual_output="sector_context_state",
        ),
        ModelSequenceEntry(
            model_step="M03",
            model_name="Target State",
            model_id="target_state_vector_model",
            model_surface="model_03_target_state_vector",
            conceptual_output="target_context_state",
        ),
        ModelSequenceEntry(
            model_step="M04",
            model_name="Event Failure Risk",
            model_id="event_failure_risk_model",
            model_surface="model_04_event_failure_risk",
            conceptual_output="event_failure_risk_vector",
        ),
        ModelSequenceEntry(
            model_step="M05",
            model_name="Alpha Confidence",
            model_id="alpha_confidence_model",
            model_surface="model_05_alpha_confidence",
            conceptual_output="alpha_confidence_vector",
        ),
        ModelSequenceEntry(
            model_step="M06",
            model_name="Dynamic Risk Policy",
            model_id="dynamic_risk_policy_model",
            model_surface="model_06_dynamic_risk_policy",
            conceptual_output="dynamic_risk_policy_state",
        ),
        ModelSequenceEntry(
            model_step="M07",
            model_name="Position Projection",
            model_id="position_projection_model",
            model_surface="model_07_position_projection",
            conceptual_output="position_projection_vector",
        ),
        ModelSequenceEntry(
            model_step="M08",
            model_name="Underlying Action",
            model_id="underlying_action_model",
            model_surface="model_08_underlying_action",
            conceptual_output="underlying_action_plan",
        ),
        ModelSequenceEntry(
            model_step="M09",
            model_name="Option Expression",
            model_id="option_expression_model",
            model_surface="model_09_option_expression",
            conceptual_output="option_expression_plan",
        ),
        ModelSequenceEntry(
            model_step="M10",
            model_name="Event Risk Governor",
            model_id="event_risk_governor",
            model_surface="model_10_event_risk_governor",
            conceptual_output="event_context_vector",
        ),
    )


def model_sequence_rows() -> list[dict[str, Any]]:
    """Return serializable M01-M10 model sequence rows."""

    return [entry.to_dict() for entry in model_sequence()]


__all__ = ["MODEL_SEQUENCE_CONTRACT", "ModelSequenceEntry", "model_sequence", "model_sequence_rows"]
