from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class AttachStatus(str, Enum):
    EXACT = "exact"
    PREVIOUS_BAR = "previous_bar"
    OUT_OF_TOLERANCE = "out_of_tolerance"
    MISSING = "missing"


class FeatureConfig(BaseModel):
    short_window: int = 3
    medium_window: int = 12
    baseline_volume_window: int = 20
    eps: float = 1e-9
    winsor_lower: float = 0.01
    winsor_upper: float = 0.99


class DiscoveryConfig(BaseModel):
    method: Literal["gmm", "kmeans"] = "gmm"
    candidate_k: list[int] = Field(default_factory=lambda: [4, 6, 8, 10, 12])
    selected_k: int | None = None
    random_state: int = 42
    max_iter: int = 300


class EvaluationConfig(BaseModel):
    winner_metric: str = "forward_return_12bar"
    oracle_metric: str = "oracle_forward_return_12bar"
    n_ref: int = 300
    m_ref: int = 6
    min_obs_n: int = 100
    min_active_months_n: int = 3
    min_episode_n: int = 5
    min_score_margin: float = 0.25
    min_positive_month_ratio: float = 0.55


class PipelineConfig(BaseModel):
    symbol: str
    research_object_type: str = "stocks"
    trading_data_root: Path = Path("/root/.openclaw/workspace/projects/trading-data/data")
    trading_strategy_root: Path = Path("/root/.openclaw/workspace/projects/trading-strategy/data")
    output_root: Path = Path("outputs")
    data_months: list[str]
    strategy_months: list[str]
    attach_tolerance_ms: int = 60_000
    variant_limit: int | None = 12
    feature: FeatureConfig = Field(default_factory=FeatureConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)


class ModelSelectionRecord(BaseModel):
    method: str
    k: int
    inertia_or_bic: float
    silhouette: float | None = None
    calinski_harabasz: float | None = None
    davies_bouldin: float | None = None
    min_cluster_pct: float | None = None
    max_cluster_pct: float | None = None
    score: float


class DiscoveryResult(BaseModel):
    state_table_partition_root: Path
    model_selection_path: Path
    stability_report_path: Path
    selected_method: str
    selected_k: int
    state_model_version: str


class EvaluationResult(BaseModel):
    state_evaluation_table_partition_root: Path
    mapping_path: Path
    oracle_gap_report_path: Path
    mapping_version: str
