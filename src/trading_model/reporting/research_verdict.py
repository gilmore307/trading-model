from __future__ import annotations

import pandas as pd

from trading_model.utils.time import month_count_utc


def build_research_verdict(
    state_evaluation_table: pd.DataFrame,
    mapping: pd.DataFrame,
    trivial_policy: pd.DataFrame,
) -> dict:
    state_metric = float(state_evaluation_table["forward_return_12bar"].mean())
    trivial_metric = float(state_evaluation_table["trivial_baseline_forward_return_12bar"].mean())
    oracle_metric = float(state_evaluation_table["oracle_forward_return_12bar"].mean())

    state_gap = oracle_metric - state_metric
    trivial_gap = oracle_metric - trivial_metric
    beats_trivial = state_metric > trivial_metric

    mapping_summary = {
        "state_count": int(mapping["state_id"].nunique()),
        "accepted_winner_state_count": int((mapping["winner_type"] == "variant").sum()),
        "blocked_state_count": int((mapping["winner_type"] != "variant").sum()),
        "eligible_variant_n_min": int(mapping["eligible_variant_n"].fillna(0).min()) if "eligible_variant_n" in mapping.columns else None,
        "eligible_variant_n_max": int(mapping["eligible_variant_n"].fillna(0).max()) if "eligible_variant_n" in mapping.columns else None,
    }

    coverage_blockers = []
    grouped = state_evaluation_table.groupby(["state_id", "variant_id"], as_index=False).agg(
        obs_n=("ts", "size"),
        active_months_n=("timestamp", month_count_utc),
        episode_n=("position", lambda s: int((s.fillna(0).ne(0) & ~s.fillna(0).ne(0).shift(fill_value=False)).sum())),
    )
    if not grouped.empty:
        state_blockers = grouped.groupby("state_id", as_index=False).agg(
            best_obs_n=("obs_n", "max"),
            best_active_months_n=("active_months_n", "max"),
            best_episode_n=("episode_n", "max"),
        )
        for row in state_blockers.to_dict(orient="records"):
            blocker_reasons = []
            if row["best_obs_n"] < 100:
                blocker_reasons.append("obs")
            if row["best_active_months_n"] < 3:
                blocker_reasons.append("months")
            if row["best_episode_n"] < 5:
                blocker_reasons.append("episodes")
            coverage_blockers.append({
                "state_id": row["state_id"],
                "best_obs_n": int(row["best_obs_n"]),
                "best_active_months_n": int(row["best_active_months_n"]),
                "best_episode_n": int(row["best_episode_n"]),
                "blockers": blocker_reasons,
            })

    execution_confidence_summary = {
        "contract": "v1_0to1",
        "semantics": "ranking_strength_for_state_routed_selection",
        "mean": float(mapping["execution_confidence"].mean()) if "execution_confidence" in mapping.columns and mapping["execution_confidence"].notna().any() else None,
        "max": float(mapping["execution_confidence"].max()) if "execution_confidence" in mapping.columns and mapping["execution_confidence"].notna().any() else None,
        "accepted_variant_mean": float(mapping.loc[mapping["winner_type"] == "variant", "execution_confidence"].mean()) if "execution_confidence" in mapping.columns and (mapping["winner_type"] == "variant").any() else None,
        "bucket_counts": mapping["execution_confidence_bucket"].value_counts(dropna=False).to_dict() if "execution_confidence_bucket" in mapping.columns else {},
    }

    symbol = state_evaluation_table["symbol"].iloc[0] if not state_evaluation_table.empty else None
    covered_months = sorted(state_evaluation_table["timestamp"].dropna().astype(str).str.slice(0, 7).unique().tolist()) if "timestamp" in state_evaluation_table.columns else []

    return {
        "symbol": symbol,
        "covered_months": covered_months,
        "headline": {
            "state_model_beats_trivial_baseline": beats_trivial,
            "state_model_metric_12bar": state_metric,
            "trivial_baseline_metric_12bar": trivial_metric,
            "oracle_metric_12bar": oracle_metric,
            "state_gap_to_oracle_12bar": state_gap,
            "trivial_gap_to_oracle_12bar": trivial_gap,
        },
        "mapping_summary": mapping_summary,
        "execution_confidence_summary": execution_confidence_summary,
        "coverage_blockers_by_state": coverage_blockers,
        "trivial_policy_bucket_count": int(len(trivial_policy)),
    }
