"""Physical package for Layer 5 AlphaConfidenceModel scaffold."""
from .contract import MODEL_ID, MODEL_LAYER, MODEL_SURFACE, MODEL_VERSION, VECTOR_OUTPUT
from .generator import generate_rows
from .training import score_after_cost_alpha, train_after_cost_alpha_model

__all__ = [
    "MODEL_ID",
    "MODEL_LAYER",
    "MODEL_SURFACE",
    "MODEL_VERSION",
    "VECTOR_OUTPUT",
    "generate_rows",
    "score_after_cost_alpha",
    "train_after_cost_alpha_model",
]
