from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from model_governance.training import lightgbm_score_model
from model_governance.training import LightGBMScoreModelSpec, predict_lightgbm_score, train_lightgbm_score_model


class LightGBMScoreArtifactTests(unittest.TestCase):
    def test_shared_lightgbm_score_artifact_trains_and_predicts(self) -> None:
        spec = LightGBMScoreModelSpec(
            schema_version="test_lightgbm_score_model_artifact",
            model_id="test_model",
            model_version="test",
            model_type="lightgbm_gbdt_test_score",
            score_semantics="0.5_neutral",
            seed=7,
            iterations=50,
            learning_rate=0.1,
        )
        try:
            artifact = train_lightgbm_score_model(
                spec=spec,
                feature_rows=([1.0, 0.0], [0.0, 1.0], [0.5, 0.5]),
                targets=(0.9, 0.1, 0.5),
                feature_names=("positive_feature", "negative_feature"),
                artifact_fields={"horizon": "test"},
            )
        except RuntimeError as error:
            raise unittest.SkipTest(str(error)) from error

        self.assertEqual(artifact["schema_version"], "test_lightgbm_score_model_artifact")
        self.assertEqual(artifact["model_type"], "lightgbm_gbdt_test_score")
        self.assertEqual(artifact["training_summary"]["sample_count"], 3)
        positive_score = predict_lightgbm_score([1.0, 0.0], artifact)
        negative_score = predict_lightgbm_score([0.0, 1.0], artifact)

        self.assertGreater(positive_score, negative_score)

    def test_shared_lightgbm_artifact_rejects_width_mismatch(self) -> None:
        spec = LightGBMScoreModelSpec(
            schema_version="test_lightgbm_score_model_artifact",
            model_id="test_model",
            model_version="test",
            model_type="lightgbm_gbdt_test_score",
            score_semantics="0.5_neutral",
            seed=7,
            iterations=10,
        )
        try:
            artifact = train_lightgbm_score_model(
                spec=spec,
                feature_rows=([1.0, 0.0], [0.0, 1.0]),
                targets=(0.9, 0.1),
                feature_names=("a", "b"),
            )
        except RuntimeError as error:
            raise unittest.SkipTest(str(error)) from error

        with self.assertRaisesRegex(ValueError, "feature count 1 does not match artifact width 2"):
            predict_lightgbm_score([1.0], artifact)

    def test_shared_lightgbm_artifact_reuses_booster_for_repeated_predictions(self) -> None:
        class FakeBooster:
            construction_count = 0

            def __init__(self, *, model_str: str) -> None:
                FakeBooster.construction_count += 1
                self.model_str = model_str

            def predict(self, _features: object) -> list[float]:
                return [0.42]

        artifact = {
            "schema_version": "test_lightgbm_score_model_artifact",
            "model_id": "test_model",
            "model_version": "test",
            "model_type": "lightgbm_gbdt_test_score",
            "score_semantics": "0.5_neutral",
            "feature_names": ["a", "b"],
            "booster_model": "fake model",
        }

        lightgbm_score_model._BOOSTER_CACHE.clear()
        with patch.dict(sys.modules, {"lightgbm": SimpleNamespace(Booster=FakeBooster)}):
            self.assertEqual(predict_lightgbm_score([1.0, 0.0], artifact), 0.42)
            self.assertEqual(predict_lightgbm_score([0.0, 1.0], artifact), 0.42)

        self.assertEqual(FakeBooster.construction_count, 1)


if __name__ == "__main__":
    unittest.main()
