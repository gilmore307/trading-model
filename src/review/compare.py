from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config.accounts import V2_ACCOUNTS
from src.execution.pipeline import ExecutionCycleResult

# This module intentionally focuses on state/ownership comparison first.
# Performance comparison should layer on top once per-account PnL/equity inputs are available.


FLAT_COMPARE_ALIAS = 'flat_compare'


@dataclass(slots=True)
class CompareSnapshot:
    symbol: str
    regime: str
    confidence: float | None
    selected_strategy: str | None
    composite_owner: str | None
    accounts: list[dict[str, Any]]
    highlights: list[str]


def _account_row(alias: str, label: str, live_positions: list[dict[str, Any]], selected_strategy: str | None, composite_owner: str | None) -> dict[str, Any]:
    pos = next((p for p in live_positions if p.get('account') == alias), None)
    status = 'flat'
    side = None
    size = 0.0
    owner_match = False
    selected_match = False
    if pos is not None:
        status = pos.get('status') or 'unknown'
        side = pos.get('side')
        size = float(pos.get('size') or 0.0)
    owner_match = composite_owner == alias
    selected_match = selected_strategy == alias
    return {
        'account': alias,
        'label': label,
        'has_position': pos is not None and side is not None and size > 0,
        'status': status,
        'side': side,
        'size': size,
        'selected_by_router': selected_match,
        'owns_composite_position': owner_match,
    }


def build_compare_snapshot(result: ExecutionCycleResult) -> dict[str, Any]:
    selected_strategy = result.router_composite.get('selected_strategy')
    composite_owner = result.router_composite.get('position_owner')
    accounts = [
        _account_row(account.alias, account.label, result.live_positions, selected_strategy, composite_owner)
        for account in V2_ACCOUNTS
    ]
    accounts.append(
        {
            'account': FLAT_COMPARE_ALIAS,
            'label': 'Flat Compare',
            'has_position': False,
            'status': 'flat',
            'side': None,
            'size': 0.0,
            'selected_by_router': False,
            'owns_composite_position': composite_owner == FLAT_COMPARE_ALIAS,
        }
    )

    highlights: list[str] = []
    if selected_strategy is not None:
        highlights.append(f'router_selected:{selected_strategy}')
    if composite_owner is not None:
        highlights.append(f'composite_owner:{composite_owner}')
    if selected_strategy and composite_owner and selected_strategy != composite_owner:
        highlights.append('router_selection_differs_from_position_owner')
    if result.router_composite.get('switch_action'):
        highlights.append(f"composite_switch:{result.router_composite.get('switch_action')}")

    snapshot = CompareSnapshot(
        symbol=result.regime_output.symbol,
        regime=result.regime_output.final_decision.get('primary'),
        confidence=result.regime_output.final_decision.get('confidence'),
        selected_strategy=selected_strategy,
        composite_owner=composite_owner,
        accounts=accounts,
        highlights=highlights,
    )
    return {
        'symbol': snapshot.symbol,
        'regime': snapshot.regime,
        'confidence': snapshot.confidence,
        'selected_strategy': snapshot.selected_strategy,
        'composite_owner': snapshot.composite_owner,
        'accounts': snapshot.accounts,
        'highlights': snapshot.highlights,
    }
