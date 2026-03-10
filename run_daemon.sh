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
  mode=$(python scripts_mode.py | python -c 'import sys,json; print(json.load(sys.stdin)["mode"])')
  echo "[$ts] cycle_start mode=$mode" | tee -a logs/service/daemon.log
  python -m src.runner.live_trader --market-only 2>&1 | tee -a logs/service/daemon.log || true
  python -m src.review.reconcile_state 2>&1 | tee -a logs/service/daemon.log || true
  if [ "$mode" = "trade" ]; then
    if python -m src.runner.live_trader --arm-demo-submit 2>&1 | tee -a logs/service/daemon.log; then
      echo "[$ts] cycle_ok mode=trade" | tee -a logs/service/daemon.log
    else
      echo "[$ts] cycle_error mode=trade" | tee -a logs/service/daemon.log
    fi
  elif [ "$mode" = "review" ]; then
    python -m src.review.flatten_all 2>&1 | tee -a logs/service/daemon.log || true
    python -m src.review.workflow 2>&1 | tee -a logs/service/daemon.log || true
    if python -m src.review.review_runner 2>&1 | tee -a logs/service/daemon.log; then
      python scripts_set_mode.py reset --reason "review_complete_auto_transition" --actor daemon 2>&1 | tee -a logs/service/daemon.log || true
      echo "[$ts] cycle_ok mode=review" | tee -a logs/service/daemon.log
    else
      echo "[$ts] cycle_error mode=review" | tee -a logs/service/daemon.log
    fi
  elif [ "$mode" = "reset" ]; then
    if python -m src.review.reset_orchestrator 2>&1 | tee -a logs/service/daemon.log; then
      echo "[$ts] cycle_ok mode=reset" | tee -a logs/service/daemon.log
    else
      echo "[$ts] cycle_error mode=reset" | tee -a logs/service/daemon.log
    fi
  else
    echo "[$ts] cycle_ok mode=develop" | tee -a logs/service/daemon.log
  fi
  python scripts_status.py > logs/service/health.json 2>> logs/service/daemon.log || true
  python scripts_snapshot.py > logs/service/snapshot.json 2>> logs/service/daemon.log || true
  sync || true
  echo "[$ts] cycle_end mode=$mode" | tee -a logs/service/daemon.log
  rmdir "$LOCK_DIR" 2>/dev/null || true
  trap - EXIT
  sleep 60
done
