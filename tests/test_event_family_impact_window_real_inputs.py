from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from models.model_03_event_state.event_governance.event_family_impact_window_real_inputs import (
    cpi_events_from_trading_economics,
    _temporal_form_for_family,
    triple_witching_events,
)


class EventFamilyImpactWindowRealInputsTests(unittest.TestCase):
    def test_triple_witching_events_use_quarterly_third_fridays(self) -> None:
        rows = triple_witching_events(date(2021, 1, 1), date(2022, 1, 1))
        self.assertEqual([row["event_date"] for row in rows], ["2021-03-19", "2021-06-18", "2021-09-17", "2021-12-17"])
        self.assertTrue(all(row["family_key"] == "triple_witching_calendar" for row in rows))
        self.assertTrue(all(row["event_temporal_form"] == "scheduled_calendar_event" for row in rows))

    def test_cpi_events_deduplicate_te_rows_by_release_date(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            source_root = Path(raw_tmp)
            saved = source_root / "trading_economics_calendar_web" / "2021-03" / "runs" / "run" / "saved"
            saved.mkdir(parents=True)
            path = saved / "trading_economics_calendar_event.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["event_time", "country", "event", "source_event_type"],
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "event_time": "2021-03-10T08:30:00-05:00",
                        "country": "United States",
                        "event": "Inflation Rate YoY",
                        "source_event_type": "inflation rate",
                    }
                )
                writer.writerow(
                    {
                        "event_time": "2021-03-10T08:30:00-05:00",
                        "country": "United States",
                        "event": "Core Inflation Rate YoY",
                        "source_event_type": "core inflation rate",
                    }
                )
                writer.writerow(
                    {
                        "event_time": "2021-03-12T08:30:00-05:00",
                        "country": "United States",
                        "event": "PPI",
                        "source_event_type": "ppi",
                    }
                )

            rows = cpi_events_from_trading_economics(source_root, date(2021, 3, 1), date(2021, 4, 1))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["family_key"], "cpi_inflation_release")
        self.assertEqual(rows[0]["event_temporal_form"], "scheduled_data_release_event")
        self.assertEqual(rows[0]["event_date"], "2021-03-10")
        self.assertIn(str(path), rows[0]["source_ref"])

    def test_temporal_forms_cover_scheduled_and_unscheduled_families(self) -> None:
        self.assertEqual(_temporal_form_for_family("fomc_rates_policy"), "scheduled_data_release_event")
        self.assertEqual(_temporal_form_for_family("earnings_guidance_scheduled_shell"), "scheduled_calendar_event")
        self.assertEqual(_temporal_form_for_family("equity_offering_dilution"), "instantaneous_unscheduled_event")


if __name__ == "__main__":
    unittest.main()
