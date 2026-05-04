"""StrategySelectionModel family-spec primitives.

Layer 3 strategy families are implemented as deterministic, point-in-time
variant specifications. The specs are intentionally pure Python data contracts:
they do not read databases, choose option contracts, size positions, or emit
orders. Evaluation code can import these specs one family at a time and test the
expanded variants against anonymous target-candidate feature rows.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

ACTIVE_CATALOG = "active_catalog"
LAYER3_BACKLOG = "layer3_backlog"
PRUNING_UNIT = "3_strategy_family"


@dataclass(frozen=True)
class VariantAxis:
    """One reviewed variant axis for a strategy family."""

    name: str
    values: tuple[Any, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("variant axis name is required")
        if not self.values:
            raise ValueError(f"variant axis {self.name!r} must define at least one value")


@dataclass(frozen=True)
class StrategyFamilySpec:
    """Reviewed standalone Layer 3 strategy-family implementation contract."""

    family: str
    evaluation_order: int
    status: str
    summary: str
    suitable_periods: tuple[str, ...]
    alpaca_data_support: tuple[str, ...]
    fixed_parameters: Mapping[str, Any]
    axes: tuple[VariantAxis, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.evaluation_order < 1:
            raise ValueError("strategy family evaluation_order must be positive; 0 is reserved for common primitives")

    @property
    def variant_count(self) -> int:
        count = 1
        for axis in self.axes:
            count *= len(axis.values)
        return count

    def iter_variant_specs(self) -> Iterable[dict[str, Any]]:
        """Expand reviewed axes into canonical variant payloads."""

        axis_names = [axis.name for axis in self.axes]
        axis_values = [axis.values for axis in self.axes]
        for values in itertools.product(*axis_values):
            variable_parameters = dict(zip(axis_names, values, strict=True))
            fixed_parameters = dict(self.fixed_parameters)
            hash_payload = {
                "3_strategy_family": self.family,
                "fixed_parameters": fixed_parameters,
                "variable_parameters": variable_parameters,
            }
            spec_hash = stable_spec_hash(hash_payload)
            yield {
                "3_family_evaluation_order": self.evaluation_order,
                "3_strategy_family": self.family,
                "implementation_status": self.status,
                "fixed_parameters": fixed_parameters,
                "variable_parameters": variable_parameters,
                "3_strategy_variant": f"{self.family}.{spec_hash[:16]}",
                "strategy_spec_hash": spec_hash,
            }


def stable_spec_hash(payload: Mapping[str, Any]) -> str:
    """Return a deterministic hash for a canonical strategy spec payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def family_payload(spec: StrategyFamilySpec) -> dict[str, Any]:
    """Serialize a family-level spec for documentation/tests."""

    return {
        "3_family_evaluation_order": spec.evaluation_order,
        "3_strategy_family": spec.family,
        "implementation_status": spec.status,
        "summary": spec.summary,
        "suitable_periods": list(spec.suitable_periods),
        "alpaca_data_support": list(spec.alpaca_data_support),
        "fixed_parameters": dict(spec.fixed_parameters),
        "axes": {axis.name: list(axis.values) for axis in spec.axes},
        "variant_count": spec.variant_count,
        "notes": list(spec.notes),
    }
