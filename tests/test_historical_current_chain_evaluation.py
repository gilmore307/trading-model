from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from model_governance.current_chain import build_current_chain_rows
from model_governance.historical_current_chain_evaluation import (
    HistoricalInputRow,
    historical_source_row_to_payload,
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
        self.assertEqual(receipt["fold_count"], 2)
        self.assertEqual(receipt["label_join_coverage_rate"], 1.0)
        self.assertFalse(receipt["activation_allowed"])
        self.assertFalse(receipt["production_promotion_allowed"])
        self.assertIn("degenerate_underlying_action_distribution", receipt["warning_reasons"])
        self.assertEqual(len(artifact["tables"]["model_eval_label"]), 2)
        self.assertEqual(artifact["tables"]["model_eval_run"][0]["run_status"], "blocked")

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


if __name__ == "__main__":
    unittest.main()
