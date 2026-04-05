from __future__ import annotations

import numpy as np
import pandas as pd

from trading_model.contracts.types import EvaluationConfig


def _mad(series: pd.Series) -> float:
    med = series.median()
    return float((series - med).abs().median())


def build_winner_mapping(state_evaluation_table: pd.DataFrame, config: EvaluationConfig) -> pd.DataFrame:
    frame = state_evaluation_table.copy()
    frame["month"] = pd.to_datetime(frame["timestamp"]).dt.to_period("M").astype(str)

    default_variant = (
        frame.groupby("variant_id")[config.winner_metric]
        .mean()
        .sort_values(ascending=False)
        .index[0]
    )
    default_rows = frame[frame["variant_id"] == default_variant][["symbol", "ts", config.winner_metric]].rename(
        columns={config.winner_metric: "default_metric"}
    )
    frame = frame.merge(default_rows, on=["symbol", "ts"], how="left")
    frame["d_i"] = frame[config.winner_metric] - frame["default_metric"]

    monthly = (
        frame.groupby(["state_id", "variant_id", "month"], as_index=False)
        .agg(
            dbar=("d_i", "mean"),
            obs_n=("d_i", "size"),
            episode_n=("d_i", lambda s: int((s != 0).sum())),
        )
    )

    stats = (
        monthly.groupby(["state_id", "variant_id"], as_index=False)
        .agg(
            mu=("dbar", "mean"),
            sigma=("dbar", "std"),
            p=("dbar", lambda s: float((s > 0).mean())),
            obs_n=("obs_n", "sum"),
            active_months_n=("month", "nunique"),
            episode_n=("episode_n", "sum"),
        )
        .fillna({"sigma": 0.0})
    )

    stats["w"] = np.minimum(1.0, stats["obs_n"] / config.n_ref) * np.minimum(1.0, stats["active_months_n"] / config.m_ref)
    stats["eligible"] = (
        (stats["obs_n"] >= config.min_obs_n)
        & (stats["active_months_n"] >= config.min_active_months_n)
        & (stats["episode_n"] >= config.min_episode_n)
    )

    scored_groups: list[pd.DataFrame] = []
    for state_id, group in stats.groupby("state_id", sort=True):
        eligible = group.copy()
        mu_med = eligible["mu"].median()
        mu_mad = _mad(eligible["mu"]) + 1e-9
        sigma_med = eligible["sigma"].median()
        sigma_mad = _mad(eligible["sigma"]) + 1e-9
        eligible["z_mu"] = (eligible["mu"] - mu_med) / mu_mad
        eligible["z_sigma"] = (eligible["sigma"] - sigma_med) / sigma_mad
        eligible["winner_score"] = eligible["w"] * (
            eligible["z_mu"] - 0.5 * eligible["z_sigma"] + 0.5 * (2 * eligible["p"] - 1)
        )
        eligible = eligible.sort_values(["winner_score", "mu", "p"], ascending=[False, False, False]).reset_index(drop=True)
        top1 = eligible.iloc[0] if not eligible.empty else None
        top2 = eligible.iloc[1] if len(eligible) > 1 else None
        margin = float(top1["winner_score"] - top2["winner_score"]) if top1 is not None and top2 is not None else np.nan
        accepted = bool(
            top1 is not None
            and top1["winner_score"] > 0
            and (np.isnan(margin) or margin >= config.min_score_margin)
            and top1["p"] >= config.min_positive_month_ratio
        )
        chosen_variant = top1["variant_id"] if accepted else "no_strong_preference"
        scored_groups.append(
            pd.DataFrame(
                [
                    {
                        "state_id": state_id,
                        "winner_type": "variant" if accepted else "no_strong_preference",
                        "winner_id": chosen_variant,
                        "runner_up_id": None if top2 is None else top2["variant_id"],
                        "winner_score": None if top1 is None else float(top1["winner_score"]),
                        "score_margin": None if np.isnan(margin) else margin,
                        "selection_confidence": None if top1 is None else float(top1["p"]),
                        "fallback_policy": "keep_current_then_global_default",
                        "mapping_version": "v1",
                        "primary_winner_metric": config.winner_metric,
                        "default_variant_id": default_variant,
                    }
                ]
            )
        )
    return pd.concat(scored_groups, ignore_index=True)
