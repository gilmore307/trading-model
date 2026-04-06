from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

from trading_model.contracts.types import DiscoveryConfig, ModelSelectionRecord


class DiscoveryModelBundle:
    def __init__(self, model: object, labels: np.ndarray, probabilities: np.ndarray | None):
        self.model = model
        self.labels = labels
        self.probabilities = probabilities


def fit_candidate_models(feature_matrix: np.ndarray, config: DiscoveryConfig) -> tuple[DiscoveryModelBundle, list[ModelSelectionRecord]]:
    bundles: list[tuple[DiscoveryModelBundle, ModelSelectionRecord]] = []

    for k in config.candidate_k:
        if config.method == "gmm":
            model = GaussianMixture(
                n_components=k,
                covariance_type="full",
                random_state=config.random_state,
                max_iter=config.max_iter,
            )
            labels = model.fit_predict(feature_matrix)
            probabilities = model.predict_proba(feature_matrix)
            inertia_or_bic = float(model.bic(feature_matrix))
        else:
            model = KMeans(
                n_clusters=k,
                random_state=config.random_state,
                n_init="auto",
                max_iter=config.max_iter,
            )
            labels = model.fit_predict(feature_matrix)
            probabilities = None
            inertia_or_bic = float(model.inertia_)

        unique, counts = np.unique(labels, return_counts=True)
        cluster_pct = counts / counts.sum()

        silhouette = float(silhouette_score(feature_matrix, labels)) if len(unique) > 1 else None
        ch = float(calinski_harabasz_score(feature_matrix, labels)) if len(unique) > 1 else None
        db = float(davies_bouldin_score(feature_matrix, labels)) if len(unique) > 1 else None

        score = 0.0
        if silhouette is not None:
            score += silhouette * 3.0
        if ch is not None:
            score += np.log1p(ch)
        if db is not None:
            score -= db
        score -= max(0.0, 0.05 - float(cluster_pct.min())) * 10.0

        bundles.append(
            (
                DiscoveryModelBundle(model=model, labels=labels, probabilities=probabilities),
                ModelSelectionRecord(
                    method=config.method,
                    k=k,
                    inertia_or_bic=inertia_or_bic,
                    silhouette=silhouette,
                    calinski_harabasz=ch,
                    davies_bouldin=db,
                    min_cluster_pct=float(cluster_pct.min()),
                    max_cluster_pct=float(cluster_pct.max()),
                    score=float(score),
                ),
            )
        )

    bundles.sort(key=lambda item: (-item[1].score, item[1].k))
    selected_bundle, _ = bundles[0]
    records = [record for _, record in bundles]
    return selected_bundle, records


def attach_states(frame: pd.DataFrame, bundle: DiscoveryModelBundle, z_feature_columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    result["state_id"] = bundle.labels.astype(int)
    if bundle.probabilities is not None:
        sorted_probabilities = np.sort(bundle.probabilities, axis=1)
        top1 = sorted_probabilities[:, -1]
        top2 = sorted_probabilities[:, -2] if sorted_probabilities.shape[1] > 1 else np.zeros(len(sorted_probabilities))
        result["state_confidence"] = top1
        result["state_margin"] = top1 - top2
    else:
        result["state_confidence"] = np.nan
        result["state_margin"] = np.nan
    result["feature_vector_dim"] = len(z_feature_columns)
    return result
