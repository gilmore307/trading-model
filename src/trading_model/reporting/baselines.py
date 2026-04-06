from __future__ import annotations

import pandas as pd


BASELINE_VOL_Q = 4
BASELINE_RET_Q = 4


def build_trivial_baselines(state_table: pd.DataFrame) -> pd.DataFrame:
    frame = state_table.copy()
    frame = frame.sort_values(["symbol", "ts"]).reset_index(drop=True)

    frame["vol_bucket"] = pd.qcut(frame["rv_m"], q=min(BASELINE_VOL_Q, frame["rv_m"].nunique()), duplicates="drop")
    frame["ret_bucket"] = pd.qcut(frame["ret_m"], q=min(BASELINE_RET_Q, frame["ret_m"].nunique()), duplicates="drop")
    frame["trivial_baseline_id"] = (
        frame["ret_bucket"].astype(str) + "|" + frame["vol_bucket"].astype(str)
    )
    return frame[["symbol", "ts", "trivial_baseline_id", "vol_bucket", "ret_bucket"]]
