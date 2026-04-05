from __future__ import annotations

import numpy as np
import pandas as pd

from trading_model.contracts.types import FeatureConfig


FEATURE_COLUMNS = [
    "ret_s",
    "ret_m",
    "rv_s",
    "rv_m",
    "range_s",
    "range_m",
    "activity_s",
    "activity_m",
    "slope_s",
    "slope_m",
    "directionality_s",
    "directionality_m",
]


def _rolling_slope(log_price: pd.Series, window: int) -> pd.Series:
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def fit(values: np.ndarray) -> float:
        y = np.asarray(values, dtype=float)
        y_mean = y.mean()
        return float(((x - x_mean) * (y - y_mean)).sum() / denom)

    return log_price.rolling(window).apply(fit, raw=True)


def build_base_features(bars: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    frame = bars.copy()
    eps = config.eps
    w_s = config.short_window
    w_m = config.medium_window
    b = config.baseline_volume_window

    frame["r_1"] = np.log(frame["close"] / frame["close"].shift(1))
    frame["log_close"] = np.log(frame["close"])

    frame["ret_s"] = np.log(frame["close"] / frame["close"].shift(w_s))
    frame["ret_m"] = np.log(frame["close"] / frame["close"].shift(w_m))

    frame["rv_s"] = np.sqrt(frame["r_1"].pow(2).rolling(w_s).sum())
    frame["rv_m"] = np.sqrt(frame["r_1"].pow(2).rolling(w_m).sum())

    frame["range_s"] = (
        frame["high"].rolling(w_s).max() - frame["low"].rolling(w_s).min()
    ) / (frame["close"] + eps)
    frame["range_m"] = (
        frame["high"].rolling(w_m).max() - frame["low"].rolling(w_m).min()
    ) / (frame["close"] + eps)

    vol_baseline = frame["volume"].shift(1).rolling(b).median()
    frame["activity_s"] = frame["volume"].rolling(w_s).mean() / (vol_baseline + eps)
    frame["activity_m"] = frame["volume"].rolling(w_m).mean() / (vol_baseline + eps)

    frame["slope_s"] = _rolling_slope(frame["log_close"], w_s)
    frame["slope_m"] = _rolling_slope(frame["log_close"], w_m)

    frame["directionality_s"] = frame["ret_s"].abs() / (frame["r_1"].abs().rolling(w_s).sum() + eps)
    frame["directionality_m"] = frame["ret_m"].abs() / (frame["r_1"].abs().rolling(w_m).sum() + eps)

    frame = frame.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
    return frame
