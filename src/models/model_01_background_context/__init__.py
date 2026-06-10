"""M01 BackgroundContextModel package."""

from .contract import CONCEPTUAL_OUTPUT, MODEL_ID, MODEL_STEP, MODEL_SURFACE, MODEL_VERSION, PRIMARY_OUTPUT
from .generator import generate_rows

__all__ = [
    "CONCEPTUAL_OUTPUT",
    "MODEL_ID",
    "MODEL_STEP",
    "MODEL_SURFACE",
    "MODEL_VERSION",
    "PRIMARY_OUTPUT",
    "generate_rows",
]
