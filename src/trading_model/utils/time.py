from __future__ import annotations

import pandas as pd


def month_label_utc(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, utc=True)
    return ts.dt.strftime("%Y-%m")


def month_count_utc(series: pd.Series) -> int:
    ts = pd.to_datetime(series, utc=True)
    return int(ts.dt.strftime("%Y-%m").nunique())
