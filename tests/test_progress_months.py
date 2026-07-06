from __future__ import annotations

import unittest

from model_governance.progress_months import month_keys_between, month_progress


class ProgressMonthsTest(unittest.TestCase):
    def test_month_keys_between_uses_exclusive_end_month(self) -> None:
        self.assertEqual(
            month_keys_between("2016-01-01T00:00:00-05:00", "2017-01-01T00:00:00-05:00"),
            [
                "2016-01",
                "2016-02",
                "2016-03",
                "2016-04",
                "2016-05",
                "2016-06",
                "2016-07",
                "2016-08",
                "2016-09",
                "2016-10",
                "2016-11",
                "2016-12",
            ],
        )

    def test_month_progress_counts_prior_months_as_completed(self) -> None:
        payload = month_progress(
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2017-01-01T00:00:00-05:00",
            current_time="2016-03-15T10:30:00-05:00",
        )
        self.assertEqual(payload["current_month"], "2016-03")
        self.assertEqual(payload["completed_months"], 2)
        self.assertEqual(payload["expected_months"], 12)
        self.assertEqual(payload["unit_label"], "dataset months")

    def test_completed_month_progress_marks_full_window(self) -> None:
        payload = month_progress(
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2017-01-01T00:00:00-05:00",
            completed=True,
        )
        self.assertEqual(payload["current_month"], "2016-12")
        self.assertEqual(payload["completed_months"], 12)
        self.assertEqual(payload["expected_months"], 12)


if __name__ == "__main__":
    unittest.main()
