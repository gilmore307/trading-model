"""Legacy physical package for conceptual Layer 4 AlphaConfidenceModel scaffold."""
from .contract import MODEL_ID, MODEL_LAYER, MODEL_SURFACE, MODEL_VERSION, VECTOR_OUTPUT
from .generator import generate_rows

__all__ = ["MODEL_ID", "MODEL_LAYER", "MODEL_SURFACE", "MODEL_VERSION", "VECTOR_OUTPUT", "generate_rows"]
