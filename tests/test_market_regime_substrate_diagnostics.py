from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from models.model_01_market_regime.substrate_diagnostics import diagnose_substrate


def _feature_rows() -> list[dict[str, object]]:
    return [
        {"snapshot_time": "2026-01-02T10:00:00-05:00", "spy_return_30m": 0.01, "qqq_spy_30m": 0.02},
        {"snapshot_time": "2026-01-02T10:30:00-05:00", "spy_return_30m": None, "qqq_spy_30m": None},
        {"snapshot_time": "2026-01-02T11:00:00-05:00", "spy_return_30m": 0.03, "qqq_spy_30m": None},
    ]


def _model_rows() -> list[dict[str, object]]:
    return [
        {
            "available_time": "2026-01-02T10:00:00-05:00",
            "1_market_direction_score": 0.1,
            "1_market_trend_quality_score": None,
            "1_coverage_score": 0.2,
            "1_data_quality_score": 0.2,
        }
    ]


class MarketRegimeSubstrateDiagnosticsTests(unittest.TestCase):
    def test_diagnostic_separates_source_feature_and_model_blockers(self) -> None:
        summary = diagnose_substrate(
            source_symbol_rows=[
                {
                    "symbol": "SPY",
                    "timeframe": "30Min",
                    "row_count": 10,
                    "decision_row_count": 10,
                    "decision_day_count": 2,
                    "start_time": "2026-01-02T10:00:00-05:00",
                    "end_time": "2026-01-02T16:00:00-05:00",
                },
                {
                    "symbol": "QQQ",
                    "timeframe": "30Min",
                    "row_count": 400,
                    "decision_row_count": 400,
                    "decision_day_count": 300,
                    "start_time": "2025-01-02T10:00:00-05:00",
                    "end_time": "2026-01-02T16:00:00-05:00",
                },
            ],
            feature_rows=_feature_rows(),
            model_rows=_model_rows(),
            min_source_decision_days=252,
            min_feature_signal_coverage=0.01,
        )

        self.assertEqual(summary["contract_type"], "model_01_market_regime_substrate_diagnostic_v1")
        self.assertEqual(summary["source_bar_summary"]["symbol_count"], 2)
        self.assertEqual(summary["blocker_counts"]["source_sparse_symbol_timeframe_count"], 1)
        self.assertGreater(summary["blocker_counts"]["feature_low_signal_row_count"], 0)
        self.assertEqual(summary["alignment_summary"]["feature_model_intersection_count"], 1)
        self.assertEqual(summary["alignment_summary"]["feature_without_model_count"], 2)
        self.assertEqual(summary["blocker_counts"]["model_feature_missing_alignment_count"], 2)
        self.assertEqual(summary["write_policy"], "read_only_no_database_write")

    def test_cli_module_imports_without_database_dependency(self) -> None:
        module = importlib.import_module("models.model_01_market_regime.substrate_diagnostics")
        self.assertTrue(hasattr(module, "diagnose_substrate"))

    def test_core_diagnostic_has_no_database_connection_surface(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        text = (repo_root / "src" / "models" / "model_01_market_regime" / "substrate_diagnostics.py").read_text(encoding="utf-8")
        for token in ["psycopg", "OPENCLAW_DATABASE_URL", "database-url", "connect(", "subprocess"]:
            self.assertNotIn(token, text)

    def test_cli_fixture_stdout_is_machine_readable_json(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = {**os.environ, "PYTHONPATH": "src"}
        result = subprocess.run(
            [
                sys.executable,
                "scripts/models/model_01_market_regime/diagnose_model_01_market_regime_substrate.py",
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["contract_type"], "model_01_market_regime_substrate_diagnostic_v1")
        self.assertIn("DRY RUN ONLY", result.stderr)


if __name__ == "__main__":
    unittest.main()
