from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from models.model_10_event_risk_governor.event_family_impact_window_backtest import (
    build_real_input_event_family_impact_window_backtest,
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

    def test_real_input_backtest_uses_event_and_bar_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            event_csv = tmp / "events.csv"
            bar_csv = tmp / "bars.csv"
            event_csv.write_text(
                "\n".join(
                    [
                        "family_key,event_temporal_form,event_date,event_ref,source_ref",
                        "cpi_inflation_release,scheduled_data_release_event,2021-01-20,cpi-real-1,calendar://cpi/2021-01-20",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            lines = ["symbol,date,open,high,low,close"]
            start = date(2020, 12, 20)
            for offset in range(60):
                day = start + timedelta(days=offset)
                impact = 0.05 if day == date(2021, 1, 20) else 0.002
                lines.append(f"SPY,{day.isoformat()},100,{100 * (1 + impact)},{100 * (1 - impact)},100")
            bar_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

            backtest = build_real_input_event_family_impact_window_backtest(
                event_paths=(event_csv,),
                bar_paths=(bar_csv,),
                generated_at_utc="2026-06-10T10:20:00+00:00",
            )
            payload = backtest.to_dict()

            self.assertEqual(payload["input_scope"], "real_input_backtest")
            self.assertEqual(payload["source_event_paths"], [str(event_csv)])
            self.assertEqual(payload["source_bar_paths"], [str(bar_csv)])
            self.assertEqual(payload["summary"]["sample_scope_note"], "Reviewed local event and price input contract run; not accepted promotion evidence until review.")
            self.assertEqual(payload["family_rows"][0]["parameterization_status"], "real_input_backtest_selected")
            self.assertEqual(payload["family_rows"][0]["event_family_impact_parameterization"]["impact_scope_parameter"], "point_in_time_price_path")
            self.assertEqual(payload["provider_calls"], 0)

    def test_cli_requires_event_and_bar_inputs_together(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            event_csv = tmp / "events.csv"
            event_csv.write_text("family_key,event_temporal_form,event_date\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_10_event_risk_governor/build_event_family_impact_window_backtest.py",
                    "--event-csv",
                    str(event_csv),
                    "--output-dir",
                    str(tmp / "out"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--event-csv and --bar-csv must be provided together", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
