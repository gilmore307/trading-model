"""Compatibility exports for promotion agent-review helpers.

New code should import from ``model_governance.promotion.agent_review``.
"""

from model_governance.promotion.agent_review import (
    build_decision_row_from_review,
    build_market_regime_promotion_prompt,
    extract_json_object,
    validate_promotion_review,
)

__all__ = [
    "build_decision_row_from_review",
    "build_market_regime_promotion_prompt",
    "extract_json_object",
    "validate_promotion_review",
]
