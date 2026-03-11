from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.runtime.mode import RuntimeMode


@dataclass(slots=True)
class RuntimeState:
    mode: RuntimeMode = RuntimeMode.DEVELOP
    updated_at: datetime = datetime.now(UTC)
    reason: str | None = None
