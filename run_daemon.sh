#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace/projects/okx-trading
mkdir -p logs/service
source .venv/bin/activate
LOCK_DIR="/tmp/okx-trading.lock"
while true; do
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[$ts] cycle_skip reason=lock_held" | tee -a logs/service/daemon.log
    sleep 60
    continue
  fi
  trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
  echo "[$ts] cycle_start" | tee -a logs/service/daemon.log
  if python -m src.runner.live_trader --arm-demo-submit 2>&1 | tee -a logs/service/daemon.log; then
    echo "[$ts] cycle_ok" | tee -a logs/service/daemon.log
  else
    echo "[$ts] cycle_error" | tee -a logs/service/daemon.log
  fi
  python scripts_status.py > logs/service/health.json 2>> logs/service/daemon.log || true
  sync || true
  echo "[$ts] cycle_end" | tee -a logs/service/daemon.log
  rmdir "$LOCK_DIR" 2>/dev/null || true
  trap - EXIT
  sleep 60
done
