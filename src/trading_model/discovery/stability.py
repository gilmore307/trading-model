from __future__ import annotations

import pandas as pd


def build_stability_report(state_table: pd.DataFrame, model_selection: pd.DataFrame, state_model_version: str) -> dict:
    state_counts = state_table["state_id"].value_counts(normalize=True).sort_index()
    dwell = (
        state_table.assign(run_break=state_table["state_id"].ne(state_table["state_id"].shift()).cumsum())
        .groupby(["state_id", "run_break"], as_index=False)
        .size()
        .groupby("state_id")["size"]
        .agg(["mean", "median", "max", "count"])
        .reset_index()
        .to_dict(orient="records")
    )

    transition = pd.crosstab(
        state_table["state_id"].shift(),
        state_table["state_id"],
        normalize="index",
    ).fillna(0.0)

    return {
        "state_model_version": state_model_version,
        "row_count": int(len(state_table)),
        "selected_k": int(state_table["state_id"].nunique()),
        "cluster_size_pct": {str(k): float(v) for k, v in state_counts.items()},
        "avg_state_confidence": float(state_table["state_confidence"].dropna().mean()) if state_table["state_confidence"].notna().any() else None,
        "avg_state_margin": float(state_table["state_margin"].dropna().mean()) if "state_margin" in state_table.columns and state_table["state_margin"].notna().any() else None,
        "low_margin_share_lt_0_05": float((state_table["state_margin"] < 0.05).mean()) if "state_margin" in state_table.columns and state_table["state_margin"].notna().any() else None,
        "dwell_summary": dwell,
        "transition_matrix": {
            str(idx): {str(col): float(val) for col, val in row.items()}
            for idx, row in transition.to_dict(orient="index").items()
        },
        "model_selection": model_selection.to_dict(orient="records"),
    }
