from __future__ import annotations

import numpy as np
import pandas as pd


def _clip01(series: pd.Series) -> pd.Series:
    return series.astype(float).clip(lower=0.0, upper=1.0)


def add_execution_confidence_fields(mapping: pd.DataFrame) -> pd.DataFrame:
    frame = mapping.copy()

    base_confidence = _clip01(frame.get("selection_confidence", pd.Series(np.nan, index=frame.index)).fillna(0.0))
    margin = frame.get("score_margin", pd.Series(np.nan, index=frame.index)).fillna(0.0).clip(lower=0.0)
    margin_strength = 1.0 - np.exp(-margin)

    eligible_variant_n = frame.get("eligible_variant_n", pd.Series(np.nan, index=frame.index)).fillna(0.0)
    coverage_strength = (eligible_variant_n / (eligible_variant_n + 2.0)).clip(lower=0.0, upper=1.0)

    is_variant = frame.get("winner_type", pd.Series("", index=frame.index)).eq("variant")
    execution_confidence = (0.55 * base_confidence) + (0.30 * margin_strength) + (0.15 * coverage_strength)
    execution_confidence = execution_confidence.where(is_variant, 0.0).clip(lower=0.0, upper=1.0)

    frame["execution_confidence"] = execution_confidence
    frame["opportunity_strength"] = execution_confidence
    frame["execution_confidence_bucket"] = pd.cut(
        frame["execution_confidence"],
        bins=[-0.001, 0.25, 0.50, 0.75, 1.0],
        labels=["very_low", "low", "medium", "high"],
    ).astype("string")
    frame["execution_confidence_contract"] = "v1_0to1"
    frame["execution_confidence_semantics"] = "ranking_strength_for_state_routed_selection"
    return frame
