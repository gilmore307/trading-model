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
    row: dict[str, object] = {"snapshot_time": (base + timedelta(minutes=30 * index)).isoformat()}
    column_direction: dict[str, float] = {}
    for spec in generator.FACTOR_SPECS:
        for signal in spec.signals:
            column_direction.setdefault(signal.column, signal.direction)
    for column, direction in column_direction.items():
        row[column] = value * direction
    return row


class MarketRegimeModelTests(unittest.TestCase):
    def test_generates_continuous_state_vector_without_state_labels(self) -> None:
        input_rows = [_row(index) for index in range(1, 66)]
        rows = generator.generate_rows(input_rows, lookback=120)

        self.assertEqual(len(rows), 65)
        mature = rows[-1]
        self.assertEqual(mature["available_time"], _row(65)["snapshot_time"])
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
        rows = generator.generate_rows([row])

        self.assertEqual(rows[0]["available_time"], "2026-01-02T12:00:00-05:00")

    def test_rolling_standardization_does_not_use_current_or_future_rows(self) -> None:
        rows = generator.generate_rows([_row(index) for index in range(1, 22)], lookback=120)

        # The first twenty rows cannot score themselves into the rolling fit; the
        # twenty-first row is compared only to prior rows and becomes positive.
        self.assertIsNone(rows[0]["trend_factor"])
        self.assertIsNone(rows[19]["trend_factor"])
        self.assertGreater(rows[20]["trend_factor"], 0)

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
        self.assertEqual(specs["trend_factor"].aggregation, "bucketed_mean")
        self.assertGreaterEqual(next(signal.min_history for signal in specs["correlation_stress_factor"].signals), 30)

    def test_zscore_uses_std_floor_and_clip(self) -> None:
        signal = generator.Signal("example", min_history=2, std_floor=1e-8, z_clip=5.0)
        scaler = generator.RollingZScore(lookback=10, min_history=2, std_floor=1e-8, z_clip=5.0)
        scaler.update({"example": 1.0}, ["example"])
        scaler.update({"example": 1.0}, ["example"])
        self.assertEqual(scaler.zscore(signal, 2.0), 0.0)

        scaler = generator.RollingZScore(lookback=10, min_history=2, std_floor=1e-8, z_clip=5.0)
        scaler.update({"example": 0.0}, ["example"])
        scaler.update({"example": 1.0}, ["example"])
        self.assertEqual(scaler.zscore(signal, 100.0), 5.0)

    def test_sql_reader_expands_feature_payload_json(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self.executed: list[tuple[str, list[object]]] = []

            def execute(self, sql: str, params: list[object]) -> None:
                self.executed.append((sql, params))

            def fetchall(self) -> list[dict[str, object]]:
                return [
                    {
                        "snapshot_time": "2026-01-02T16:00:00-05:00",
                        "feature_payload_json": '{"spy_return_1d": 0.01}',
                    }
                ]

        cursor = FakeCursor()
        rows = sql_runner.fetch_derived_rows(cursor, source_schema="trading_data", source_table="feature_01_market_regime")

        self.assertEqual(rows[0]["snapshot_time"], "2026-01-02T16:00:00-05:00")
        self.assertEqual(rows[0]["spy_return_1d"], 0.01)
        self.assertNotIn("feature_payload_json", rows[0])

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
