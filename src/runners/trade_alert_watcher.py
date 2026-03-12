from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

RUNTIME_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
DAEMON_LOG = RUNTIME_DIR / 'trade-daemon.jsonl'
LATEST_ARTIFACT = RUNTIME_DIR / 'latest-execution-cycle.json'
STATE_PATH = RUNTIME_DIR / 'trade-alert-watcher-state.json'


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        env[key.strip()] = value.strip()
    return env


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def send_discord_message(token: str, channel_id: str, content: str) -> None:
    url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
    resp = requests.post(
        url,
        headers={
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json',
        },
        json={'content': content},
        timeout=20,
    )
    resp.raise_for_status()


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
    return (
        'crypto-trading 运行告警\n\n'
        f"- action: {summary.get('plan_action')}\n"
        f"- account: {summary.get('plan_account')}\n"
        f"- symbol: {summary.get('symbol')}\n"
        f"- regime: {summary.get('regime')}\n"
        f"- block_reason: {summary.get('block_reason')}\n"
        f"- policy_reason: {summary.get('policy_reason')}\n"
        f"- diagnostics: {summary.get('diagnostics')}"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Watch trade daemon outputs and send Discord alerts.')
    parser.add_argument('--poll-seconds', type=float, default=5.0)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    env = load_env(Path('/root/.openclaw/workspace/projects/crypto-trading/.env'))
    discord_target = env.get('OPENCLAW_DISCORD_CHANNEL', '')
    channel_id = discord_target.removeprefix('channel:') if discord_target.startswith('channel:') else discord_target
    token = os.getenv('DISCORD_BOT_TOKEN') or env.get('DISCORD_BOT_TOKEN') or os.getenv('CHANNELS_DISCORD_TOKEN')
    if not token or not channel_id:
        raise RuntimeError('Discord token/channel not configured for watcher.')

    state = read_json(STATE_PATH)
    last_daemon_size = int(state.get('last_daemon_size') or 0)
    last_trade_fingerprint = state.get('last_trade_fingerprint')
    last_warn_fingerprint = state.get('last_warn_fingerprint')

    while True:
        if DAEMON_LOG.exists():
            content = DAEMON_LOG.read_text(encoding='utf-8')
            if len(content) > last_daemon_size:
                delta = content[last_daemon_size:]
                last_daemon_size = len(content)
                for line in delta.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get('event') == 'cycle_error':
                        send_discord_message(token, channel_id, format_error_message(event))

        artifact = read_json(LATEST_ARTIFACT)
        summary = artifact.get('summary') if isinstance(artifact, dict) else {}
        if isinstance(summary, dict):
            action = summary.get('plan_action')
            receipt_accepted = summary.get('receipt_accepted')
            recorded_at = artifact.get('recorded_at')
            trade_fp = f"{recorded_at}|{action}|{summary.get('plan_account')}|{summary.get('symbol')}|{summary.get('receipt_mode')}|{receipt_accepted}"
            if action in {'enter', 'exit'} and receipt_accepted and trade_fp != last_trade_fingerprint:
                send_discord_message(token, channel_id, format_trade_message(summary, artifact))
                last_trade_fingerprint = trade_fp

            warn_fp = f"{recorded_at}|{summary.get('block_reason')}|{summary.get('policy_reason')}"
            if (summary.get('block_reason') or summary.get('policy_reason')) and warn_fp != last_warn_fingerprint:
                send_discord_message(token, channel_id, format_reconcile_message(summary))
                last_warn_fingerprint = warn_fp

        write_json(STATE_PATH, {
            'last_daemon_size': last_daemon_size,
            'last_trade_fingerprint': last_trade_fingerprint,
            'last_warn_fingerprint': last_warn_fingerprint,
            'updated_at': datetime.now(UTC).isoformat(),
        })
        time.sleep(max(1.0, args.poll_seconds))


if __name__ == '__main__':
    main()
