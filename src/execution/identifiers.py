from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def generate_execution_id(*, account: str, symbol: str, action: str) -> str:
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    compact_symbol = ''.join(ch for ch in symbol.upper() if ch.isalnum())[:12]
    compact_account = ''.join(ch for ch in account.lower() if ch.isalnum())[:8]
    compact_action = ''.join(ch for ch in action.lower() if ch.isalnum())[:4]
    nonce = uuid4().hex[:8]
    return f"exec_{stamp}_{compact_account}_{compact_symbol}_{compact_action}_{nonce}"


def build_okx_cl_ord_id(*, execution_id: str, account: str, symbol: str, action: str) -> str:
    compact_account = ''.join(ch for ch in account.lower() if ch.isalnum())[:6]
    compact_symbol = ''.join(ch for ch in symbol.upper() if ch.isalnum())[:8]
    compact_action = ''.join(ch for ch in action.lower() if ch.isalnum())[:2]
    tail = execution_id.replace('exec_', '').replace('_', '')[-14:]
    cl_ord_id = f"oc{compact_account}{compact_symbol}{compact_action}{tail}"
    return cl_ord_id[:32]
