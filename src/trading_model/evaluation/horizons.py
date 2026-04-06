from __future__ import annotations

import pandas as pd


HORIZONS = [1, 3, 12, 24]


def add_group_forward_returns(
    frame: pd.DataFrame,
    *,
    group_cols: list[str],
    value_col: str,
    prefix: str,
) -> pd.DataFrame:
    out = frame.copy()
    out = out.sort_values(group_cols + ["ts"]).reset_index(drop=True)
    grouped = out.groupby(group_cols, sort=False)[value_col]
    for horizon in HORIZONS:
        out[f"{prefix}_forward_return_{horizon}bar"] = grouped.transform(lambda s, h=horizon: s.shift(-h) / s - 1.0)
    return out
