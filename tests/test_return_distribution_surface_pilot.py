from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from models.return_distribution_surface import (
    bucket_regular_session_closes,
    build_tradable_time_label_rows,
    fit_tradable_time_distribution_surface,
)


ET = ZoneInfo("America/New_York")


class ReturnDistributionSurfacePilotTests(unittest.TestCase):
    def test_label_grid_skips_closed_session_time_and_tracks_calendar_gap(self) -> None:
        rows = []
        price = 100.0
        for day in (5, 6):
            ts = datetime(2025, 1, day, 9, 30, tzinfo=ET)
            for _ in range(39):
                price += 0.1
                rows.append({"symbol": "SPY", "timestamp": ts, "bar_close": price})
                ts += timedelta(minutes=10)

        closes = bucket_regular_session_closes(rows, bucket_minutes=10, symbol="SPY")
        labels = build_tradable_time_label_rows(closes, anchor_minutes=10, max_trading_minutes=120)
        overnight = min(
            (
                row
                for row in labels
                if row.anchor_session_date.day == 5 and row.target_session_date.day == 6
            ),
            key=lambda row: row.tau_trading_minutes,
        )

        self.assertEqual(overnight.tau_trading_minutes, 10)
        self.assertGreater(overnight.tau_calendar_minutes, 600)
        self.assertTrue(overnight.crosses_session_gap)
        self.assertEqual(overnight.session_gap_count, 1)
        self.assertTrue(overnight.target_near_open)

    def test_surface_fit_returns_monotone_cdf_and_slice_diagnostics(self) -> None:
        rows = []
        for day in range(2, 12):
            price = 100.0 + day
            ts = datetime(2025, 1, day, 9, 30, tzinfo=ET)
            for bucket in range(39):
                price += 0.03 + 0.002 * bucket
                rows.append({"symbol": "SPY", "timestamp": ts, "bar_close": price})
                ts += timedelta(minutes=10)

        closes = bucket_regular_session_closes(rows, bucket_minutes=10, symbol="SPY")
        labels = build_tradable_time_label_rows(closes, anchor_minutes=10, max_trading_minutes=180)
        result = fit_tradable_time_distribution_surface(labels)

        self.assertGreater(len(result.horizon_axis_minutes), 4)
        self.assertTrue(all(row["cdf_monotone"] for row in result.cdf_rows))
        self.assertIn("all", result.slice_validation)
        self.assertIn("crosses_session_gap", result.slice_validation)


if __name__ == "__main__":
    unittest.main()
