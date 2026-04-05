from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import RobustScaler

from trading_model.contracts.types import FeatureConfig


def winsorize_and_scale(frame: pd.DataFrame, feature_columns: list[str], config: FeatureConfig) -> pd.DataFrame:
    processed = frame.copy()
    clip_bounds: dict[str, tuple[float, float]] = {}
    for col in feature_columns:
        lower = processed[col].quantile(config.winsor_lower)
        upper = processed[col].quantile(config.winsor_upper)
        processed[col] = processed[col].clip(lower=lower, upper=upper)
        clip_bounds[col] = (lower, upper)

    scaler = RobustScaler()
    scaled = scaler.fit_transform(processed[feature_columns])
    processed[[f"z_{col}" for col in feature_columns]] = scaled
    processed.attrs["clip_bounds"] = clip_bounds
    processed.attrs["scaler_center"] = dict(zip(feature_columns, scaler.center_))
    processed.attrs["scaler_scale"] = dict(zip(feature_columns, scaler.scale_))
    return processed
