from __future__ import annotations

import pandas as pd


def build_aggregate_cross_symbol_verdict(summary: dict) -> dict:
    results = pd.DataFrame(summary.get("results", []))
    availability = pd.DataFrame(summary.get("availability", []))

    ok_results = results[results.get("status", pd.Series(dtype=object)) == "ok"].copy() if not results.empty else pd.DataFrame()
    beat_count = int(ok_results["state_model_beats_trivial_baseline"].astype(bool).sum()) if not ok_results.empty else 0
    total_ok = int(len(ok_results))
    blocked_all_count = int((ok_results.get("accepted_winner_state_count", 0).fillna(0) == 0).sum()) if not ok_results.empty else 0

    priority_symbols = []
    if not ok_results.empty:
        ranked = ok_results.sort_values(["shared_month_count", "execution_confidence_mean", "trivial_baseline_metric_12bar"], ascending=[False, False, False])
        priority_cols = [col for col in ["symbol", "shared_month_count", "state_model_metric_12bar", "trivial_baseline_metric_12bar", "execution_confidence_mean", "execution_confidence_max"] if col in ranked.columns]
        priority_symbols = ranked[priority_cols].to_dict(orient="records")

    no_shared = []
    if not availability.empty:
        no_shared = availability[availability["shared_month_count"] == 0][["symbol"]].to_dict(orient="records")

    return {
        "headline": {
            "symbols_scanned": int(len(availability)) if not availability.empty else 0,
            "symbols_with_shared_months": total_ok,
            "symbols_beating_trivial_baseline": beat_count,
            "symbols_fully_blocked_on_winner_mapping": blocked_all_count,
        },
        "research_conclusion": {
            "overall_result": "no_cross_symbol_outperformance" if beat_count == 0 else "mixed_or_positive",
            "main_constraint": "coverage_months_insufficient" if total_ok > 0 and blocked_all_count == total_ok else "mixed_constraints",
            "recommended_next_action": "expand_shared_month_coverage_before_tuning_mapping" if total_ok > 0 and beat_count == 0 else "inspect_symbol_level_winners",
        },
        "priority_symbols_for_data_expansion": priority_symbols,
        "symbols_without_any_shared_months": no_shared,
    }
