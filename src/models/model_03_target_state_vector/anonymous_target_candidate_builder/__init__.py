"""Importable anonymous target candidate builder boundary."""
from .builder import (
    ANONYMITY_PASS_STATES,
    BUILDER_VERSION,
    ELIGIBILITY_STATES,
    MODEL_FACING_VECTOR,
    OUTPUT_COLUMNS,
    CandidateBuildResult,
    build_candidate_rows,
    build_candidates,
    model_facing_payload,
    validate_model_facing_vector,
)

__all__ = [
    "ANONYMITY_PASS_STATES",
    "BUILDER_VERSION",
    "ELIGIBILITY_STATES",
    "MODEL_FACING_VECTOR",
    "OUTPUT_COLUMNS",
    "CandidateBuildResult",
    "build_candidate_rows",
    "build_candidates",
    "model_facing_payload",
    "validate_model_facing_vector",
]
