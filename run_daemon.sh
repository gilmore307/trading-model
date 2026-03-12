#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace/projects/crypto-trading
exec ./.venv/bin/python -m src.runners.trade_daemon --interval-seconds 60
