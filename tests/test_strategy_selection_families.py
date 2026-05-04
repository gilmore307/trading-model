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
            "moving_average_crossover": 288,
            "donchian_channel_breakout": 288,
            "macd_trend": 288,
            "bollinger_band_reversion": 384,
            "rsi_reversion": 288,
            "bias_reversion": 384,
            "vwap_reversion": 216,
            "range_breakout": 432,
            "opening_range_breakout": 48,
            "volatility_breakout": 240,
        }

        self.assertEqual(set(FAMILIES_BY_NAME), set(expected_counts))
        for family, expected_count in expected_counts.items():
            self.assertEqual(FAMILIES_BY_NAME[family].variant_count, expected_count, family)

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
