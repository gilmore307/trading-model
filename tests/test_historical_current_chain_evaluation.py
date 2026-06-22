from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from model_governance.current_chain import build_current_chain_rows
from model_governance.historical_current_chain_evaluation import (
    BASELINE_FEATURE_NAMES,
    HistoricalInputRow,
    TARGET_STATE_FEATURE_TABLE,
    TARGET_STATE_SOURCE_TABLE,
    _event_observation_payload,
    historical_source_row_to_payload,
    load_historical_rows_from_database,
    run_historical_current_chain_evaluation,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class HistoricalCurrentChainEvaluationTests(unittest.TestCase):
    def test_historical_source_row_maps_to_current_payload_without_identity_in_features(self) -> None:
        payload = historical_source_row_to_payload(_source_row("2017-01-03T10:00:00-05:00", "tcand_a", "AAPL", 100.0, 101.0))

        self.assertEqual(payload["routing_symbol"], "AAPL")
        self.assertEqual(payload["target_candidate_id"], "tcand_a")
        self.assertNotIn("symbol", payload["anonymous_target_feature_vector"])
        self.assertEqual(payload["accepted_event_contracts"], [])
        self.assertEqual(payload["option_contract_candidates"], [])

        rows = build_current_chain_rows(payload, use_fixture_defaults=False)
        target_payload = rows["model_02_target_state"][0]["target_context_state"]["anonymous_target_feature_vector"]
        self.assertNotIn("symbol", target_payload)
        self.assertNotIn("company_name", target_payload)

    def test_historical_evaluation_builds_folds_and_deferred_evidence_tables(self) -> None:
        rows = [
            HistoricalInputRow(
                source_row=_source_row("2017-01-03T10:00:00-05:00", "tcand_a", "AAPL", 100.0, 101.0),
                payload=historical_source_row_to_payload(_source_row("2017-01-03T10:00:00-05:00", "tcand_a", "AAPL", 100.0, 101.0)),
                label_payload={
                    "label_name": "future_target_return_1W",
                    "horizon": "1W",
                    "available_time": "2017-01-03T10:00:00-05:00",
                    "label_time": "2017-01-10T10:00:00-05:00",
                    "label_matured": True,
                    "future_return_1W": 0.01,
                    "utility_score_1W": 0.55,
                },
            ),
            HistoricalInputRow(
                source_row=_source_row("2017-02-01T10:00:00-05:00", "tcand_b", "MSFT", 50.0, 49.0),
                payload=historical_source_row_to_payload(_source_row("2017-02-01T10:00:00-05:00", "tcand_b", "MSFT", 50.0, 49.0)),
                label_payload={
                    "label_name": "future_target_return_1W",
                    "horizon": "1W",
                    "available_time": "2017-02-01T10:00:00-05:00",
                    "label_time": "2017-02-08T10:00:00-05:00",
                    "label_matured": True,
                    "future_return_1W": -0.02,
                    "utility_score_1W": 0.40,
                },
            ),
        ]

        artifact = run_historical_current_chain_evaluation(rows, run_id="test_run", train_baseline=False)
        receipt = artifact["receipt"]

        self.assertEqual(receipt["contract_type"], "current_model_historical_evaluation_receipt")
        self.assertEqual(receipt["source_selection_policy"], "point_in_time_liquidity_ranked_daily_stratified_context_enriched_sample")
        self.assertEqual(receipt["fold_count"], 2)
        self.assertEqual(receipt["label_join_coverage_rate"], 1.0)
        self.assertEqual(receipt["unique_target_candidate_count"], 2)
        self.assertEqual(receipt["unique_routing_symbol_count"], 2)
        self.assertEqual(receipt["preferred_decision_horizon_counts"], {"1W": 2})
        self.assertEqual(receipt["rows_with_option_contract_candidates"], 0)
        self.assertEqual(receipt["rows_with_event_observations"], 0)
        self.assertFalse(receipt["activation_allowed"])
        self.assertFalse(receipt["production_promotion_allowed"])
        self.assertIn("degenerate_underlying_action_distribution", receipt["warning_reasons"])
        self.assertIn("m04_materiality_adjusted_action_1w", BASELINE_FEATURE_NAMES)
        self.assertNotIn("m04_trade_intensity_1w", BASELINE_FEATURE_NAMES)
        self.assertEqual(artifact["tables"]["model_dataset_request"][0]["required_source_key"], f"trading_data.{TARGET_STATE_FEATURE_TABLE}")
        self.assertEqual(artifact["tables"]["model_dataset_snapshot"][0]["feature_table"], f"trading_data.{TARGET_STATE_FEATURE_TABLE}")
        self.assertEqual(len(artifact["tables"]["model_eval_label"]), 2)
        self.assertEqual(artifact["tables"]["model_eval_run"][0]["run_status"], "blocked")

    def test_historical_evaluation_blocks_single_target_candidate_evidence(self) -> None:
        rows = [
            HistoricalInputRow(
                source_row=_source_row("2017-01-03T10:00:00-05:00", "tcand_a", "AAPL", 100.0, 101.0),
                payload=historical_source_row_to_payload(_source_row("2017-01-03T10:00:00-05:00", "tcand_a", "AAPL", 100.0, 101.0)),
                label_payload={
                    "label_name": "future_target_return_1W",
                    "horizon": "1W",
                    "available_time": "2017-01-03T10:00:00-05:00",
                    "label_time": "2017-01-10T10:00:00-05:00",
                    "label_matured": True,
                    "future_return_1W": 0.01,
                    "utility_score_1W": 0.55,
                },
            ),
            HistoricalInputRow(
                source_row=_source_row("2017-02-01T10:00:00-05:00", "tcand_a", "AAPL", 50.0, 49.0),
                payload=historical_source_row_to_payload(_source_row("2017-02-01T10:00:00-05:00", "tcand_a", "AAPL", 50.0, 49.0)),
                label_payload={
                    "label_name": "future_target_return_1W",
                    "horizon": "1W",
                    "available_time": "2017-02-01T10:00:00-05:00",
                    "label_time": "2017-02-08T10:00:00-05:00",
                    "label_matured": True,
                    "future_return_1W": -0.02,
                    "utility_score_1W": 0.40,
                },
            ),
        ]

        artifact = run_historical_current_chain_evaluation(rows, run_id="single_target_run", train_baseline=False)
        receipt = artifact["receipt"]

        self.assertEqual(receipt["evaluation_status"], "blocked")
        self.assertIn("insufficient_target_candidate_diversity", receipt["blocking_reasons"])
        self.assertIn("insufficient_routing_symbol_diversity", receipt["blocking_reasons"])
        self.assertIn("low_target_candidate_diversity", receipt["warning_reasons"])
        self.assertIn("low_routing_symbol_diversity", receipt["warning_reasons"])

    def test_historical_evaluation_cli_supports_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/models/run_current_model_historical_evaluation.py", "--help"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--per-month-limit", result.stdout)
        self.assertIn("--skip-baseline-training", result.stdout)

    def test_database_loader_uses_point_in_time_ranked_daily_stratified_sampling(self) -> None:
        cursor = _CapturingCursor()

        rows = load_historical_rows_from_database(
            cursor,
            start_time="2017-01-01T00:00:00-05:00",
            end_time="2017-02-01T00:00:00-05:00",
            limit=10,
            per_month_limit=5,
        )

        self.assertEqual(rows, [])
        query = cursor.query
        self.assertIn("point_in_time_candidate_rank", query)
        self.assertIn("daily_sample_rank", query)
        self.assertIn(TARGET_STATE_FEATURE_TABLE, query)
        self.assertIn(TARGET_STATE_SOURCE_TABLE, query)
        self.assertIn("COALESCE(da.dollar_volume, 0) DESC", query)
        self.assertIn("COALESCE(da.spread_bps, 1000000) ASC", query)
        self.assertIn("ORDER BY monthly_sample.available_time, monthly_sample.point_in_time_candidate_rank", query)
        self.assertNotIn("model_02_target_state_feature_generation", query)
        self.assertNotIn("model_02_target_state_data_acquisition", query)
        self.assertNotIn("ORDER BY fg.available_time, fg.target_candidate_id", query)

    def test_historical_source_row_preserves_point_in_time_option_and_event_context(self) -> None:
        row = _source_row("2017-01-03T10:00:00-05:00", "tcand_a", "AAPL", 100.0, 101.0)
        row["target_state_features"]["multi_frame_state"]["1W"]["return"] = None  # type: ignore[index]
        row["option_contract_candidates"] = [{"contract_ref": "AAPL_CALL", "right": "call"}]
        row["event_observations"] = [{"event_id": "evt_aapl", "dedup_status": "new_information"}]

        payload = historical_source_row_to_payload(row)

        self.assertEqual(payload["policy_gate_state"]["preferred_decision_horizon"], "1D")
        self.assertTrue(payload["option_expression_policy"]["option_expression_allowed"])
        self.assertEqual(payload["option_expression_policy"]["option_surface_status"], "optionable_chain_available")
        self.assertEqual(payload["option_expression_policy"]["max_quote_age_seconds"], 604800)
        self.assertEqual(payload["option_contract_candidates"], [{"contract_ref": "AAPL_CALL", "right": "call"}])
        self.assertEqual(payload["event_observations"], [{"event_id": "evt_aapl", "dedup_status": "new_information"}])

    def test_event_overview_rows_are_standardized_before_model_consumption(self) -> None:
        payload = _event_observation_payload(
            {
                "event_id": "evt_option_activity",
                "canonical_event_id": "evt_option_activity",
                "dedup_status": "canonical",
                "event_time": "2021-01-04T12:38:03-05:00",
                "available_time": "2021-01-04T12:38:03-05:00",
                "event_category_type": "symbol_news",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "title": "10 Information Technology Stocks With Unusual Options Alerts In Today's Session",
                "summary": "This unusual options alert can help traders track potentially big trading opportunities.",
                "source_name": "Benzinga",
                "source_priority": "verified_news",
                "reference_type": "web_url",
                "reference": "https://example.test/news",
                "feature_payload_json": {"event_category_type": "symbol_news", "scope_type": "symbol"},
            }
        )

        interpretation = payload["event_interpretation"]
        self.assertEqual(payload["dedup_status"], "new_information")
        self.assertEqual(interpretation["schema_version"], "event_interpretation_v1")
        self.assertEqual(interpretation["normalized_event_type"], "option_derivatives_abnormality")
        self.assertEqual(interpretation["affected_scope"]["primary_scope"], "microstructure")
        self.assertGreaterEqual(interpretation["option_impact_score"], 0.70)
        self.assertIn("option_price", interpretation["impact_channels"])


def _source_row(available_time: str, target_candidate_id: str, symbol: str, close: float, future_close: float) -> dict[str, object]:
    return {
        "available_time": available_time,
        "tradeable_time": available_time,
        "target_candidate_id": target_candidate_id,
        "symbol": symbol,
        "bar_close": close,
        "future_close": future_close,
        "label_time": available_time,
        "dollar_volume": 10_000_000.0,
        "avg_bid": close - 0.01,
        "avg_ask": close + 0.01,
        "spread_bps": 2.0,
        "market_state_features": {
            "market_context_payload": {
                "1_market_direction_score": 0.1,
                "1_market_trend_quality_score": 0.5,
                "1_market_risk_stress_score": 0.2,
                "1_market_liquidity_support_score": 0.7,
                "1_data_quality_score": 0.8,
                "1_coverage_score": 0.8,
            }
        },
        "sector_state_features": {
            "sector_context_payload": {
                "sector_or_industry_symbol": "XLK",
                "2_sector_relative_direction_score": 0.1,
                "2_sector_breadth_confirmation_score": 0.6,
                "2_sector_internal_dispersion_score": 0.2,
            }
        },
        "target_state_features": {
            "target_price_state": {"bar_close": close},
            "target_data_quality_state": {"has_volume": True},
            "multi_frame_state": {
                "1W": {"return": (future_close - close) / close, "trend_quality": 0.5, "realized_vol": 0.2},
                "1D": {"return": 0.0, "trend_quality": 0.5, "realized_vol": 0.2},
                "1h": {"return": 0.0, "trend_quality": 0.5, "realized_vol": 0.2},
                "10min": {"return": 0.0, "trend_quality": 0.5, "realized_vol": 0.2},
            },
        },
        "cross_state_features": {},
        "feature_quality_diagnostics": {"history_bars": 120, "has_target_close": True, "has_target_volume": True},
    }


class _CapturingCursor:
    def __init__(self) -> None:
        self.query = ""
        self.params = ()

    def execute(self, query: str, params: tuple[object, ...]) -> None:
        self.query = query
        self.params = params

    def fetchall(self) -> list[dict[str, object]]:
        return []


if __name__ == "__main__":
    unittest.main()
