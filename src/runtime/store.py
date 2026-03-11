from __future__ import annotations

from datetime import UTC, datetime

from src.runtime.mode import RuntimeMode
from src.runtime.state import RuntimeState


class RuntimeStore:
    def __init__(self):
        self._state = RuntimeState()

    def get(self) -> RuntimeState:
        return self._state

    def set_mode(self, mode: RuntimeMode, reason: str | None = None) -> RuntimeState:
        self._state.mode = mode
        self._state.reason = reason
        self._state.updated_at = datetime.now(UTC)
        return self._state
