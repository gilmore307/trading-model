from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
ACTIVE_STRATEGY_POINTER_PATH = OUT_DIR / 'active-strategy.json'


@dataclass(slots=True)
class ActiveStrategySnapshot:
    version: str
    updated_at: str
    source: str
    metadata: dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_active_strategy_snapshot() -> ActiveStrategySnapshot:
    if ACTIVE_STRATEGY_POINTER_PATH.exists():
        try:
            payload = json.loads(ACTIVE_STRATEGY_POINTER_PATH.read_text(encoding='utf-8'))
        except Exception:
            payload = {}
        version = str(payload.get('version') or 'legacy-default')
        updated_at = str(payload.get('updated_at') or _utc_now_iso())
        source = str(payload.get('source') or str(ACTIVE_STRATEGY_POINTER_PATH))
        metadata = payload.get('metadata') if isinstance(payload.get('metadata'), dict) else {}
        metadata.setdefault('family', str(payload.get('family') or metadata.get('family') or 'default'))
        metadata.setdefault('config_path', str(payload.get('config_path') or metadata.get('config_path') or ''))
        metadata.setdefault('promoted_at', str(payload.get('promoted_at') or metadata.get('promoted_at') or updated_at))
        metadata.setdefault('promotion_note', str(payload.get('promotion_note') or metadata.get('promotion_note') or ''))
        return ActiveStrategySnapshot(version=version, updated_at=updated_at, source=source, metadata=metadata)

    snapshot = ActiveStrategySnapshot(
        version='legacy-default',
        updated_at=_utc_now_iso(),
        source='implicit_runtime_default',
        metadata={
            'note': 'active strategy pointer not initialized; using legacy runtime default',
            'family': 'default',
            'config_path': '',
            'promoted_at': _utc_now_iso(),
            'promotion_note': 'bootstrap default pointer',
        },
    )
    ACTIVE_STRATEGY_POINTER_PATH.write_text(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2), encoding='utf-8')
    return snapshot


def store_active_strategy_snapshot(snapshot: ActiveStrategySnapshot) -> None:
    ACTIVE_STRATEGY_POINTER_PATH.write_text(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2), encoding='utf-8')
