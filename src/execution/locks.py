from __future__ import annotations

import threading
from collections import defaultdict
from contextlib import contextmanager


class AccountSymbolLockRegistry:
    def __init__(self):
        self._locks: dict[tuple[str, str], threading.Lock] = defaultdict(threading.Lock)

    @contextmanager
    def hold(self, account: str, symbol: str):
        lock = self._locks[(account, symbol)]
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
