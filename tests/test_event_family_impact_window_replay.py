from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_03_event_state.event_governance.event_family_impact_window_replay import build_impact_window_replay_artifacts


class EventFamilyImpactWindowReplayTests(unittest.TestCase):
    def test_replay_overlay_respects_scheduled_visibility_and_unscheduled_no_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            replay_rows = root / "decision_rows.jsonl"
            replay_rows.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "decision_id": "before_cpi",
                                "target_ref": "AAPL",
                                "replay_time_pointer": "2021-03-08T16:00:00-05:00",
                                "decision_status": "accepted",
                                "prediction_score": 0.5,
                                "outcome_label": 0,
                                "realized_return": 0.0,
                                "cost": 0.0,
                                "baseline_return": 0.0,
                            }
                        ),
                        json.dumps(
                            {
                                "decision_id": "before_breaking_news",
                                "target_ref": "AAPL",
                                "replay_time_pointer": "2021-03-14T16:00:00-04:00",
                                "decision_status": "accepted",
                                "prediction_score": 0.5,
                                "outcome_label": 0,
                                "realized_return": 0.0,
                                "cost": 0.0,
                                "baseline_return": 0.0,
                            }
                        ),
                        json.dumps(
                            {
                                "decision_id": "after_breaking_news",
                                "target_ref": "AAPL",
                                "replay_time_pointer": "2021-03-15T16:00:00-04:00",
                                "decision_status": "accepted",
                                "prediction_score": 0.5,
                                "outcome_label": 0,
                                "realized_return": 0.0,
                                "cost": 0.0,
                                "baseline_return": 0.0,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            event_csv = root / "events.csv"
            with event_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["family_key", "event_temporal_form", "event_date", "event_ref", "source_ref"],
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "family_key": "cpi_inflation_release",
                        "event_temporal_form": "scheduled_data_release_event",
                        "event_date": "2021-03-10",
                        "event_ref": "cpi_20210310",
                        "source_ref": "test",
                    }
                )
                writer.writerow(
                    {
                        "family_key": "breaking_news_shock",
                        "event_temporal_form": "instantaneous_unscheduled_event",
                        "event_date": "2021-03-15",
                        "event_ref": "shock_20210315",
                        "source_ref": "test",
                    }
                )
            summary = root / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "selected_windows": {
                            "cpi_inflation_release": {"selected_window_label": "minus_3_to_event"},
                            "breaking_news_shock": {"selected_window_label": "minus_2_to_plus_2"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "out"

            result = build_impact_window_replay_artifacts(
                replay_decision_rows=replay_rows,
                event_csv=event_csv,
                impact_window_summary=summary,
                output_dir=output_dir,
                fold_id="fold_test",
                replay_run_id="replay_test",
                include_sql_candidate_events=False,
            )

            overlay_rows = [json.loads(line) for line in Path(result.overlay_rows_path).read_text(encoding="utf-8").splitlines()]
            by_decision = {row["decision_id"]: row for row in overlay_rows}

        self.assertEqual(by_decision["before_cpi"]["visible_event_families"], ["cpi_inflation_release"])
        self.assertEqual(by_decision["before_cpi"]["visible_event_window_policies"], ["calibrated_impact_window"])
        self.assertEqual(by_decision["before_breaking_news"]["visible_event_families"], [])
        self.assertEqual(by_decision["after_breaking_news"]["visible_event_families"], ["breaking_news_shock"])


if __name__ == "__main__":
    unittest.main()
