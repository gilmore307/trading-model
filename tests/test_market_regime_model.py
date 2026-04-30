from __future__ import annotations

import importlib
import importlib.util
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
generator = importlib.import_module("model_outputs.model_01_market_regime.generator")
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_model_01_market_regime.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("generate_model_01_market_regime", SCRIPT_PATH)
sql_runner = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC and SCRIPT_SPEC.loader
SCRIPT_SPEC.loader.exec_module(sql_runner)


def _row(index: int) -> dict[str, object]:
    base = datetime(2026, 1, 2, 10, 0, tzinfo=ET)
    value = float(index)
    return {
        "snapshot_time": (base + timedelta(minutes=30 * index)).isoformat(),
        "spy_return_5d": value,
        "spy_return_20d": value,
        "spy_distance_to_ma20": value,
        "spy_distance_to_ma50": value,
        "spy_ma20_slope_5d": value,
        "spy_ma_alignment_score": value,
        "vixy_realized_vol_20d": value,
        "vixy_realized_vol_20d_percentile_252d": value,
        "market_state_avg_abs_return_corr_20d": value,
        "hyg_lqd_30m": -value,
        "hyg_lqd_distance_to_ma20": -value,
        "hyg_lqd_realized_vol_20d_ratio": value,
        "tlt_shy_30m": -value,
        "ief_shy_30m": -value,
        "uup_spy_30m": value,
        "uup_return_5d": value,
        "dbc_return_5d": value,
        "gld_spy_30m": value,
        "sector_observation_distance_to_ma20_dispersion": value,
        "sector_observation_return_20d_dispersion": value,
        "sector_observation_positive_return_1d_pct": value,
        "sector_observation_above_ma20_pct": value,
        "qqq_spy_30m": value,
        "iwm_spy_30m": value,
        "rsp_spy_30m": value,
        "xly_xlp_30m": value,
        "tlt_spy_30m": -value,
        "vixy_spy_30m": -value,
    }


class MarketRegimeModelTests(unittest.TestCase):
    def test_generates_continuous_state_vector_without_state_labels(self) -> None:
        rows = generator.generate_rows([_row(1), _row(2), _row(3), _row(4)], lookback=10, min_history=2)

        self.assertEqual(len(rows), 4)
        mature = rows[-1]
        self.assertEqual(mature["available_time"], _row(4)["snapshot_time"])
        self.assertGreater(mature["trend_factor"], 0)
        self.assertGreater(mature["volatility_stress_factor"], 0)
        self.assertGreater(mature["credit_stress_factor"], 0)
        self.assertGreater(mature["rate_pressure_factor"], 0)
        self.assertGreater(mature["risk_appetite_factor"], 0)
        self.assertGreater(mature["data_quality_score"], 0)
        self.assertLessEqual(mature["data_quality_score"], 1)
        self.assertIsNotNone(mature["transition_pressure"])
        for forbidden in {"state_id", "state_probability_0", "state_confidence"}:
            self.assertNotIn(forbidden, mature)

    def test_uses_available_time_when_present(self) -> None:
        row = _row(1)
        row["available_time"] = "2026-01-02T12:00:00-05:00"
        rows = generator.generate_rows([row], min_history=1)

        self.assertEqual(rows[0]["available_time"], "2026-01-02T12:00:00-05:00")

    def test_rolling_standardization_does_not_use_current_or_future_rows(self) -> None:
        rows = generator.generate_rows([_row(1), _row(2), _row(3)], lookback=10, min_history=2)

        # The first two rows cannot score themselves into the rolling fit; the third row
        # is compared only to prior rows and becomes a positive trend observation.
        self.assertIsNone(rows[0]["trend_factor"])
        self.assertIsNone(rows[1]["trend_factor"])
        self.assertGreater(rows[2]["trend_factor"], 0.9)

    def test_factor_config_controls_membership_direction_and_reducer(self) -> None:
        specs = {spec.name: spec for spec in generator.load_factor_specs()}

        self.assertIn("trend_factor", specs)
        self.assertIn("spy_return_20d", {signal.column for signal in specs["trend_factor"].signals})
        credit_directions = {
            signal.column: signal.direction
            for signal in specs["credit_stress_factor"].signals
            if signal.column in {"hyg_lqd_30m", "hyg_lqd_realized_vol_20d_ratio"}
        }
        self.assertEqual(credit_directions["hyg_lqd_30m"], -1)
        self.assertEqual(credit_directions["hyg_lqd_realized_vol_20d_ratio"], 1)
        self.assertEqual(specs["sector_rotation_factor"].reducer([2.0, -2.0]), generator.REDUCERS["bounded_abs_mean"]([2.0, -2.0]))

    def test_sql_writer_uses_model_table_and_columns(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self.calls: list[tuple[str, list[object] | None]] = []

            def execute(self, sql: str, params: list[object] | None = None) -> None:
                self.calls.append((sql, params))

        cursor = FakeCursor()
        sql_runner.write_model_rows_sql(
            cursor,
            [{"available_time": "2026-01-02T10:00:00-05:00", "trend_factor": 0.5}],
            target_schema="trading_model",
            target_table="model_01_market_regime",
        )

        joined_sql = "\n".join(sql for sql, _params in cursor.calls)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_01_market_regime"', joined_sql)
        self.assertIn('ADD COLUMN IF NOT EXISTS "trend_factor" DOUBLE PRECISION', joined_sql)
        self.assertIn('ON CONFLICT ("available_time") DO UPDATE SET', joined_sql)


if __name__ == "__main__":
    unittest.main()
