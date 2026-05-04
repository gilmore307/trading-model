from __future__ import annotations

import unittest
from pathlib import Path

from models.model_03_strategy_selection.families import (
    ACTIVE_STANDALONE_FAMILIES,
    FAMILIES_BY_NAME,
    FAMILY_EVALUATION_ORDER,
    PRUNING_UNIT,
    stable_spec_hash,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FAMILIES_PATH = REPO_ROOT / "src" / "models" / "model_03_strategy_selection" / "families"


class StrategySelectionFamilyTests(unittest.TestCase):
    def test_active_standalone_families_have_ordered_importable_files(self) -> None:
        self.assertTrue((FAMILIES_PATH / "family_spec_common.py").is_file())
        expected_files = [
            "family_01_moving_average_crossover",
            "family_02_donchian_channel_breakout",
            "family_03_macd_trend",
            "family_04_bollinger_band_reversion",
            "family_05_rsi_reversion",
            "family_06_bias_reversion",
            "family_07_vwap_reversion",
            "family_08_range_breakout",
            "family_09_opening_range_breakout",
            "family_10_volatility_breakout",
        ]
        files = [
            path.stem
            for path in sorted(FAMILIES_PATH.glob("family_[0-9][0-9]_*.py"))
        ]

        self.assertEqual(files, expected_files)

    def test_family_evaluation_order_is_explicit(self) -> None:
        self.assertEqual(PRUNING_UNIT, "3_strategy_family")
        self.assertEqual(
            FAMILY_EVALUATION_ORDER,
            tuple(spec.family for spec in ACTIVE_STANDALONE_FAMILIES),
        )
        self.assertEqual(
            [spec.evaluation_order for spec in ACTIVE_STANDALONE_FAMILIES],
            list(range(1, len(ACTIVE_STANDALONE_FAMILIES) + 1)),
        )

    def test_reviewed_variant_counts_match_catalog(self) -> None:
        expected_counts = {
            "moving_average_crossover": 96,
            "donchian_channel_breakout": 144,
            "macd_trend": 288,
            "bollinger_band_reversion": 384,
            "rsi_reversion": 192,
            "bias_reversion": 384,
            "vwap_reversion": 108,
            "range_breakout": 288,
            "opening_range_breakout": 48,
            "volatility_breakout": 96,
        }

        self.assertEqual(set(FAMILIES_BY_NAME), set(expected_counts))
        for family, expected_count in expected_counts.items():
            self.assertEqual(FAMILIES_BY_NAME[family].variant_count, expected_count, family)

    def test_active_families_use_fixed_one_minute_bars(self) -> None:
        for spec in ACTIVE_STANDALONE_FAMILIES:
            axis_names = {axis.name for axis in spec.axes}
            self.assertEqual(spec.fixed_parameters["signal_bar_interval"], "1Min", spec.family)
            self.assertNotIn("timeframe", axis_names, spec.family)
            self.assertNotIn("signal_timeframe", axis_names, spec.family)

    def test_moving_average_profiles_cover_required_trade_rhythms(self) -> None:
        spec = FAMILIES_BY_NAME["moving_average_crossover"]
        axis_names = {axis.name for axis in spec.axes}

        self.assertNotIn("timeframe", axis_names)
        self.assertIn("ma_window_profile", axis_names)
        window_profiles = dict(
            (value[0], value[1:])
            for axis in spec.axes
            if axis.name == "ma_window_profile"
            for value in axis.values
        )
        self.assertEqual(window_profiles["micro_3_10"], (3, 10))
        self.assertEqual(window_profiles["intraday_90_360"], (90, 360))
        self.assertEqual(window_profiles["equity_day_390_1950"], (390, 1950))
        self.assertEqual(window_profiles["continuous_day_1440_7200"], (1440, 7200))
        self.assertNotIn("intraday_15_60", window_profiles)
        self.assertNotIn("intraday_60_240", window_profiles)
        self.assertNotIn("intraday_120_480", window_profiles)
        self.assertNotIn("equity_swing_780_3900", window_profiles)
        self.assertNotIn("continuous_swing_4320_20160", window_profiles)
        first_variant = next(iter(spec.iter_variant_specs()))
        self.assertEqual(first_variant["fixed_parameters"]["signal_bar_interval"], "1Min")
        self.assertIn("ma_window_profile", first_variant["variable_parameters"])
        self.assertNotIn("trend_filter_enabled", axis_names)
        self.assertNotIn("trend_filter_enabled", first_variant["variable_parameters"])
        self.assertNotIn("timeframe", first_variant["variable_parameters"])

    def test_variant_generation_is_deterministic_and_layer3_bounded(self) -> None:
        forbidden_payload_tokens = {
            "ticker",
            "company",
            "contract_id",
            "option_dte",
            "strike",
            "delta",
            "premium",
            "position_size",
            "portfolio_weight",
            "execution_policy",
        }

        for spec in ACTIVE_STANDALONE_FAMILIES:
            first_run = list(spec.iter_variant_specs())
            second_run = list(spec.iter_variant_specs())
            self.assertEqual(first_run, second_run, spec.family)
            self.assertEqual(len(first_run), spec.variant_count, spec.family)
            self.assertEqual(len({row["3_strategy_variant"] for row in first_run}), spec.variant_count, spec.family)

            for row in first_run[:5]:
                self.assertEqual(row["3_family_evaluation_order"], spec.evaluation_order)
                self.assertFalse(any(key.endswith("_group") for key in row))
                self.assertEqual(row["3_strategy_family"], spec.family)
                self.assertEqual(row["fixed_parameters"]["signal_bar_interval"], "1Min")
                self.assertNotIn("timeframe", row["variable_parameters"])
                self.assertNotIn("signal_timeframe", row["variable_parameters"])
                self.assertTrue(row["3_strategy_variant"].startswith(f"{spec.family}."))
                self.assertEqual(
                    row["strategy_spec_hash"],
                    stable_spec_hash(
                        {
                            "3_strategy_family": spec.family,
                            "fixed_parameters": row["fixed_parameters"],
                            "variable_parameters": row["variable_parameters"],
                        }
                    ),
                )
                serialized = repr(row).lower()
                for token in forbidden_payload_tokens:
                    self.assertNotIn(token, serialized, f"{spec.family} leaks {token}")


if __name__ == "__main__":
    unittest.main()
