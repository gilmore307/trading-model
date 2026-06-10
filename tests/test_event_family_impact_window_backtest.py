from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_10_event_risk_governor.event_family_impact_window_backtest import (
    build_sample_event_family_impact_window_backtest,
    write_event_family_impact_window_backtest_artifacts,
)


class EventFamilyImpactWindowBacktestTests(unittest.TestCase):
    def test_sample_backtest_learns_distinct_event_windows(self) -> None:
        backtest = build_sample_event_family_impact_window_backtest(generated_at_utc="2026-06-10T07:40:00+00:00")
        by_family = {row.family_key: row for row in backtest.family_rows}

        self.assertEqual(by_family["cpi_inflation_release"].event_temporal_form, "scheduled_data_release_event")
        self.assertEqual(by_family["cpi_inflation_release"].selected_window_label, "minus_7_to_plus_3")
        self.assertEqual(by_family["cpi_inflation_release"].event_family_impact_parameterization["selected_effect_window"]["start_offset_days"], -7)
        self.assertEqual(by_family["cpi_inflation_release"].event_family_impact_parameterization["selected_effect_window"]["end_offset_days"], 3)

        self.assertEqual(by_family["triple_witching_calendar"].event_temporal_form, "scheduled_calendar_event")
        self.assertEqual(by_family["triple_witching_calendar"].selected_window_label, "minus_2_to_plus_2")

        self.assertEqual(by_family["breaking_news_shock"].event_temporal_form, "instantaneous_unscheduled_event")
        self.assertEqual(by_family["breaking_news_shock"].selected_window_label, "event_day_only")

    def test_backtest_is_non_mutating_contract_evidence(self) -> None:
        backtest = build_sample_event_family_impact_window_backtest(generated_at_utc="2026-06-10T07:40:00+00:00")
        payload = backtest.to_dict()

        self.assertEqual(payload["contract_type"], "event_family_impact_window_backtest")
        self.assertEqual(payload["summary"]["family_count"], 3)
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_writes_backtest_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "impact-window"
            backtest = build_sample_event_family_impact_window_backtest(generated_at_utc="2026-06-10T07:40:00+00:00")
            write_event_family_impact_window_backtest_artifacts(backtest, output_dir)

            payload_path = output_dir / "event_family_impact_window_backtest.json"
            summary_path = output_dir / "event_family_impact_window_backtest_summary.json"
            csv_path = output_dir / "event_family_impact_window_backtest.csv"
            score_path = output_dir / "event_family_impact_window_candidate_scores.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertTrue(score_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["selected_windows"]["cpi_inflation_release"]["selected_window_label"], "minus_7_to_plus_3")
            self.assertIn("event_day_only", score_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
