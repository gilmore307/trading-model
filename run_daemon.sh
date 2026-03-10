#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace/projects/okx-trading
mkdir -p logs/service
source .venv/bin/activate
LOCK_DIR="/tmp/okx-trading.lock"
PIDFILE="logs/service/daemon.pid"
if [ -f "$PIDFILE" ]; then
  old_pid=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "${old_pid:-}" ] && [ "$old_pid" != "$$" ] && kill -0 "$old_pid" 2>/dev/null; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daemon_exit reason=existing_pidfile pid=$old_pid" | tee -a logs/service/daemon.log
    exit 1
  fi
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
while true; do
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[$ts] cycle_skip reason=lock_held" | tee -a logs/service/daemon.log
    sleep 60
    continue
  fi
  
  mode=$(python scripts_mode.py | python -c 'import sys,json; print(json.load(sys.stdin)["mode"])')
  echo "[$ts] cycle_start mode=$mode" | tee -a logs/service/daemon.log
  if [ "$mode" = "test" ]; then
    if python -m src.runner.test_mode --arm-demo-submit --write-state --duration-minutes 1 2>&1 | tee -a logs/service/daemon.log; then
      python scripts_set_mode.py develop --reason "test_complete_auto_transition" --actor daemon 2>&1 | tee -a logs/service/daemon.log || true
      echo "[$ts] cycle_ok mode=test" | tee -a logs/service/daemon.log
    else
      python scripts_set_mode.py develop --reason "test_failed_auto_transition" --actor daemon 2>&1 | tee -a logs/service/daemon.log || true
      echo "[$ts] cycle_error mode=test" | tee -a logs/service/daemon.log
    fi
  else
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
      python scripts_set_mode.py calibrate --reason "review_complete_auto_transition" --actor daemon 2>&1 | tee -a logs/service/daemon.log || true
      echo "[$ts] cycle_ok mode=review" | tee -a logs/service/daemon.log
    else
      echo "[$ts] cycle_error mode=review" | tee -a logs/service/daemon.log
    fi
  elif [ "$mode" = "calibrate" ]; then
    if python -m src.review.calibrate_orchestrator 2>&1 | tee -a logs/service/daemon.log; then
      echo "[$ts] cycle_ok mode=calibrate" | tee -a logs/service/daemon.log
    else
      echo "[$ts] cycle_error mode=calibrate" | tee -a logs/service/daemon.log
    fi
  elif [ "$mode" = "reset" ]; then
    if python -m src.review.fresh_reset 2>&1 | tee -a logs/service/daemon.log; then
      echo "[$ts] cycle_ok mode=reset" | tee -a logs/service/daemon.log
    else
      echo "[$ts] cycle_error mode=reset" | tee -a logs/service/daemon.log
    fi
  else
    echo "[$ts] cycle_ok mode=develop" | tee -a logs/service/daemon.log
  fi
  fi
  python scripts_status.py >> logs/service/daemon.log 2>&1 || true
  python scripts_snapshot.py >> logs/service/daemon.log 2>&1 || true
  sync || true
  echo "[$ts] cycle_end mode=$mode" | tee -a logs/service/daemon.log
  rmdir "$LOCK_DIR" 2>/dev/null || true
  :
  sleep 60
done
