from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from src.config.settings import Settings

STATE_PATH = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime/direct-notify-state.json')


class DiscordNotifier:
    def __init__(self, settings: Settings):
        self._channel_id = self._normalize_channel(settings.discord_channel)
        self._bot_token = settings.discord_bot_token
        self._webhook_url = settings.discord_webhook_url
        self._notify_warnings = settings.notify_runtime_warnings
        self._state = self._load_state()

    @property
    def enabled(self) -> bool:
        return bool(self._webhook_url or (self._bot_token and self._channel_id))

    @property
    def notify_warnings(self) -> bool:
        return self._notify_warnings

    @staticmethod
    def _normalize_channel(value: str | None) -> str | None:
        if not value:
            return None
        return value.removeprefix('channel:') if value.startswith('channel:') else value

    def _load_state(self) -> dict[str, Any]:
        if not STATE_PATH.exists():
            return {}
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def _save_state(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding='utf-8')

    def send(self, content: str) -> None:
        if not self.enabled:
            return
        if self._webhook_url:
            resp = requests.post(self._webhook_url, json={'content': content}, timeout=20)
            resp.raise_for_status()
            return
        if self._bot_token and self._channel_id:
            url = f'https://discord.com/api/v10/channels/{self._channel_id}/messages'
            resp = requests.post(
                url,
                headers={
                    'Authorization': f'Bot {self._bot_token}',
                    'Content-Type': 'application/json',
                },
                json={'content': content},
                timeout=20,
            )
            resp.raise_for_status()

    def notify_trade(self, summary: dict[str, Any], artifact: dict[str, Any]) -> bool:
        receipt_accepted = summary.get('receipt_accepted')
        action = summary.get('plan_action')
        if action not in {'enter', 'exit'} or not receipt_accepted:
            return False
        receipt = artifact.get('receipt') or {}
        fingerprint = '|'.join([
            'trade',
            str(action),
            str(summary.get('plan_account')),
            str(summary.get('symbol')),
            str(receipt.get('order_id')),
            str(summary.get('receipt_mode')),
        ])
        if fingerprint == self._state.get('last_trade_fingerprint'):
            return False
        self.send(format_trade_message(summary, artifact))
        self._state['last_trade_fingerprint'] = fingerprint
        self._save_state()
        return True

    def notify_error(self, event: dict[str, Any]) -> bool:
        fingerprint = '|'.join(['error', str(event.get('error'))])
        if fingerprint == self._state.get('last_error_fingerprint'):
            return False
        self.send(format_error_message(event))
        self._state['last_error_fingerprint'] = fingerprint
        self._save_state()
        return True

    def notify_warning(self, summary: dict[str, Any]) -> bool:
        if not should_notify_warning(summary, self._notify_warnings):
            return False
        fingerprint = '|'.join([
            'warning',
            str(summary.get('symbol')),
            str(summary.get('plan_account')),
            str(summary.get('plan_action')),
            str(summary.get('block_reason')),
            str(summary.get('policy_reason')),
        ])
        if fingerprint == self._state.get('last_warning_fingerprint'):
            return False
        self.send(format_reconcile_message(summary))
        self._state['last_warning_fingerprint'] = fingerprint
        self._save_state()
        return True


def should_notify_warning(summary: dict[str, Any], notify_runtime_warnings: bool) -> bool:
    block_reason = summary.get('block_reason')
    policy_reason = summary.get('policy_reason')
    diagnostics = set(summary.get('diagnostics') or [])

    if block_reason == 'severe_alignment_issue' or policy_reason == 'severe_alignment_issue':
        return True
    if 'freeze_route' in diagnostics or 'route_frozen' in diagnostics:
        return True
    if notify_runtime_warnings and (block_reason or policy_reason):
        return True
    return False


def format_trade_message(summary: dict[str, Any], artifact: dict[str, Any]) -> str:
    receipt = artifact.get('receipt') or {}
    plan = artifact.get('plan') or {}
    return (
        'crypto-trading 交易执行\n\n'
        f"- action: {summary.get('plan_action')}\n"
        f"- account: {summary.get('plan_account')}\n"
        f"- symbol: {summary.get('symbol')}\n"
        f"- regime: {summary.get('regime')}\n"
        f"- side: {receipt.get('side') or plan.get('side')}\n"
        f"- size: {receipt.get('size') or plan.get('size')}\n"
        f"- receipt_mode: {summary.get('receipt_mode')}\n"
        f"- order_id: {(receipt or {}).get('order_id')}\n"
        f"- reason: {summary.get('plan_reason')}"
    )


def format_error_message(event: dict[str, Any]) -> str:
    return (
        'crypto-trading 运行异常\n\n'
        f"- event: {event.get('event')}\n"
        f"- observed_at: {event.get('observed_at')}\n"
        f"- error: {event.get('error')}"
    )


def format_reconcile_message(summary: dict[str, Any]) -> str:
    symbol = summary.get('symbol') or '未知标的'
    regime = summary.get('regime') or '未知状态'
    action = summary.get('plan_action') or 'hold'
    account = summary.get('plan_account') or '无'
    block_reason = summary.get('block_reason')
    policy_reason = summary.get('policy_reason')

    if block_reason == 'regime_non_tradable':
        headline = f'市场太乱，暂不交易：{symbol}'
        detail = (
            f'系统刚判断 {symbol} 当前属于 {regime} 行情，短时间内不适合开仓，'
            '所以这轮选择继续观察，不下单。'
        )
    elif block_reason:
        headline = f'本轮未执行交易：{symbol}'
        detail = (
            f'系统判断这轮先不动手。当前市场状态：{regime}；'
            f'主要原因：{block_reason}。'
        )
    elif policy_reason:
        headline = f'交易策略主动跳过：{symbol}'
        detail = (
            f'市场判断已完成，但策略层这轮选择不执行。当前市场状态：{regime}；'
            f'原因：{policy_reason}。'
        )
    else:
        headline = f'系统保持观望：{symbol}'
        detail = f'当前市场状态：{regime}，本轮动作：{action}。'

    return (
        f'{headline}\n\n'
        f'{detail}\n\n'
        f'当前动作：{action}\n'
        f'当前账户：{account}'
    )
