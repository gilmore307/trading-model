from __future__ import annotations

import pandas as pd


def build_oracle_gap_report(state_evaluation_table: pd.DataFrame, mapping: pd.DataFrame) -> dict:
    frame = state_evaluation_table.copy()
    metric = "forward_return_12bar"
    oracle_metric = "oracle_forward_return_12bar"

    overall_realized = float(frame[metric].mean())
    overall_oracle = float(frame[oracle_metric].mean()) if frame[oracle_metric].notna().any() else None
    overall_gap_abs = None if overall_oracle is None else float(overall_oracle - overall_realized)

    by_month = (
        frame.assign(month=pd.to_datetime(frame["timestamp"]).dt.to_period("M").astype(str))
        .groupby("month", as_index=False)
        .agg(
            realized_metric_state_routed=(metric, "mean"),
            oracle_metric=(oracle_metric, "mean"),
        )
    )
    by_month["gap_abs_state_routed"] = by_month["oracle_metric"] - by_month["realized_metric_state_routed"]

    by_state = (
        frame.groupby("state_id", as_index=False)
        .agg(
            state_support_n=("ts", "size"),
            oracle_metric_mean=(oracle_metric, "mean"),
            realized_metric_mean=(metric, "mean"),
        )
    )
    by_state["gap_abs"] = by_state["oracle_metric_mean"] - by_state["realized_metric_mean"]
    by_state = by_state.merge(mapping[["state_id", "winner_id"]], on="state_id", how="left")
    by_state = by_state.rename(columns={"winner_id": "preferred_target"})

    return {
        "overall": {
            "overall_realized_metric": overall_realized,
            "overall_oracle_metric": overall_oracle,
            "overall_gap_abs": overall_gap_abs,
        },
        "by_month": by_month.to_dict(orient="records"),
        "by_state": by_state.to_dict(orient="records"),
    }
