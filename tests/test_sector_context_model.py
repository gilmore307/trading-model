from __future__ import annotations

import importlib
import importlib.util
import json
import unittest
from pathlib import Path


generator = importlib.import_module("models.model_02_sector_context.generator")
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "models" / "model_02_sector_context" / "generate_model_02_sector_context.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("generate_model_02_sector_context", SCRIPT_PATH)
sql_runner = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC and SCRIPT_SPEC.loader
SCRIPT_SPEC.loader.exec_module(sql_runner)


class SectorContextModelTests(unittest.TestCase):
    def _feature_rows(self):
        return [
            {
                "snapshot_time": "2026-01-02T16:00:00-05:00",
                "candidate_symbol": "SECTOR_OBSERVATION_UNIVERSE",
                "candidate_type": "sector_rotation_summary",
                "comparison_symbol": "MARKET",
                "rotation_pair_id": "sector_observation_breadth",
                "rotation_pair_type": "sector_rotation_summary",
                "sector_observation_positive_return_1d_pct": 0.8,
                "sector_observation_positive_return_5d_pct": 0.7,
                "sector_observation_above_ma20_pct": 0.75,
                "sector_observation_distance_to_ma20_dispersion": 0.03,
                "sector_observation_return_20d_dispersion": 0.04,
            },
            {
                "snapshot_time": "2026-01-02T16:00:00-05:00",
                "candidate_symbol": "XLK",
                "candidate_type": "sector_industry_etf",
                "comparison_symbol": "SPY",
                "rotation_pair_id": "xlk_spy",
                "rotation_pair_type": "sector_rotation",
                "relative_strength_return": 0.02,
                "relative_strength_return_30m": 0.02,
                "relative_strength_distance_to_ma20": 0.05,
                "relative_strength_slope_20d": 0.01,
                "relative_strength_ma_alignment_score": 1.0,
                "relative_strength_realized_vol_20d_ratio": 1.1,
                "relative_strength_return_corr_20d": 0.7,
                "relative_strength_return_corr_60d": 0.5,
                "relative_strength_return_corr_20d_60d_change": 0.2,
            },
            {
                "snapshot_time": "2026-01-02T16:00:00-05:00",
                "candidate_symbol": "XLP",
                "candidate_type": "sector_industry_etf",
                "comparison_symbol": "SPY",
                "rotation_pair_id": "xlp_spy",
                "rotation_pair_type": "sector_rotation",
                "relative_strength_return": -0.02,
                "relative_strength_distance_to_ma20": -0.03,
                "relative_strength_ma_alignment_score": -1.0,
                "relative_strength_realized_vol_20d_ratio": 1.8,
                "relative_strength_return_corr_20d": 0.4,
            },
        ]

    def _market_rows(self):
        return [
            {
                "available_time": "2026-01-02T16:00:00-05:00",
                "1_market_direction_score": 0.4,
                "1_market_trend_quality_score": 0.3,
                "1_market_liquidity_support_score": 0.2,
                "1_market_stability_score": 0.25,
                "1_market_risk_stress_score": -0.1,
                "1_market_transition_risk_score": 0.1,
            }
        ]

    def test_generates_primary_rows_with_narrow_contract(self) -> None:
        rows = generator.generate_rows(self._feature_rows(), self._market_rows())

        self.assertEqual({row["sector_or_industry_symbol"] for row in rows}, {"XLK", "XLP"})
        xlk = next(row for row in rows if row["sector_or_industry_symbol"] == "XLK")
        self.assertEqual(list(xlk), generator.OUTPUT_COLUMNS)
        self.assertEqual(xlk["model_id"], "sector_context_model")
        self.assertEqual(xlk["market_context_state_ref"], "model_01_market_regime:2026-01-02T16:00:00-05:00")
        self.assertIn(xlk["2_sector_handoff_state"], generator.HANDOFF_STATES)
        self.assertIn(xlk["2_eligibility_state"], generator.ELIGIBILITY_STATES)
        self.assertNotIn("candidate_symbol", xlk)
        self.assertNotIn("stock_etf_exposure", json.dumps(xlk))
        self.assertIsNotNone(xlk["2_sector_handoff_rank"])

    def test_support_artifacts_keep_review_and_gating_detail_outside_primary(self) -> None:
        explainability = generator.build_explainability_rows(self._feature_rows(), self._market_rows())
        diagnostics = generator.build_diagnostics_rows(self._feature_rows(), self._market_rows())

        self.assertEqual({row["sector_or_industry_symbol"] for row in explainability}, {"XLK", "XLP"})
        xlk_explain = next(row for row in explainability if row["sector_or_industry_symbol"] == "XLK")
        self.assertIn("2_relative_strength_score", xlk_explain)
        self.assertIn("2_context_support_score", xlk_explain)
        self.assertTrue(xlk_explain["explanation_payload_json"]["excludes_etf_holdings_and_stock_exposure"])

        xlk_diag = next(row for row in diagnostics if row["sector_or_industry_symbol"] == "XLK")
        self.assertIn("2_data_quality_score", xlk_diag)
        self.assertEqual(xlk_diag["diagnostic_payload_json"]["no_future_leak_policy"], "point_in_time_inputs_only_no_future_returns_or_realized_pnl")

    def test_sql_writers_create_three_physical_artifacts(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self.calls: list[tuple[str, list[object] | None]] = []

            def execute(self, sql: str, params: list[object] | None = None) -> None:
                self.calls.append((sql, params))

        cursor = FakeCursor()
        primary = generator.generate_rows(self._feature_rows(), self._market_rows())
        explainability = generator.build_explainability_rows(self._feature_rows(), self._market_rows())
        diagnostics = generator.build_diagnostics_rows(self._feature_rows(), self._market_rows())

        sql_runner.write_model_rows_sql(cursor, primary, target_schema="trading_model", target_table="model_02_sector_context")
        sql_runner.write_explainability_rows_sql(cursor, explainability, target_schema="trading_model", target_table="model_02_sector_context_explainability")
        sql_runner.write_diagnostics_rows_sql(cursor, diagnostics, target_schema="trading_model", target_table="model_02_sector_context_diagnostics")

        joined_sql = "\n".join(sql for sql, _params in cursor.calls)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_02_sector_context"', joined_sql)
        self.assertIn('PRIMARY KEY ("available_time", "sector_or_industry_symbol")', joined_sql)
        self.assertIn('"2_sector_handoff_state" TEXT', joined_sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_02_sector_context_explainability"', joined_sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_02_sector_context_diagnostics"', joined_sql)
        self.assertIn('"diagnostic_payload_json" JSONB NOT NULL', joined_sql)


if __name__ == "__main__":
    unittest.main()
