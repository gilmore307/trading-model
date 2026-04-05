from __future__ import annotations

import pandas as pd


HORIZONS = [1, 3, 12, 24]


def add_forward_returns(state_table: pd.DataFrame) -> pd.DataFrame:
    frame = state_table.copy()
    close = frame["close"]
    for horizon in HORIZONS:
        frame[f"forward_return_{horizon}bar"] = close.shift(-horizon) / close - 1.0
    return frame
