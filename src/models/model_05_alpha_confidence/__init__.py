"""Physical package for Layer 5 AlphaConfidenceModel."""
from .contract import MODEL_ID, MODEL_LAYER, MODEL_SURFACE, MODEL_VERSION, VECTOR_OUTPUT
from .event_conditioned_contrast import build_labeled_focus_pool_rows, run_event_conditioned_alpha_contrast
from .generator import generate_rows
from .training import score_after_cost_alpha, train_after_cost_alpha_model

__all__ = [
    "MODEL_ID",
    "MODEL_LAYER",
    "MODEL_SURFACE",
    "MODEL_VERSION",
    "VECTOR_OUTPUT",
    "build_labeled_focus_pool_rows",
    "generate_rows",
    "run_event_conditioned_alpha_contrast",
    "score_after_cost_alpha",
    "train_after_cost_alpha_model",
]
