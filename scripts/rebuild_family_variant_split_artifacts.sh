#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/.openclaw/workspace/projects/crypto-trading"
RUNNER="$ROOT/src/runners/build_family_variant_dashboard_artifacts.py"
OUT_DIR="$ROOT/data/intermediate/dashboard_payloads/family_variant_dashboard"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

families=("$@")
if [ ${#families[@]} -eq 0 ]; then
  families=(moving_average donchian_breakout bollinger_reversion)
fi

expected_variant_count() {
  local family="$1"
  python3 - "$family" <<'PY'
import sys
from pathlib import Path
root=Path('/root/.openclaw/workspace/projects/crypto-trading')
sys.path.insert(0, str(root))
from src.research.family_registry import family_config
family=sys.argv[1]
cfg=family_config(family)
print(len(cfg['baseline_variants']))
PY
}

is_complete() {
  local family="$1"
  local dir="$OUT_DIR/$family"
  [ -f "$dir/summary.json" ] || return 1
  [ -f "$dir/composite.json" ] || return 1
  return 0
}

for family in "${families[@]}"; do
  echo "=== ensure split artifacts: $family ==="
  until is_complete "$family"; do
    ts=$(date +%Y%m%d-%H%M%S)
    log="$LOG_DIR/rebuild-${family}-${ts}.log"
    echo "[$(date '+%F %T')] running family=$family log=$log"
    if python3 "$RUNNER" --family "$family" --two-pass --retain-top-per-cluster 1 --reserve-top-per-cluster 10 >"$log" 2>&1; then
      echo "[$(date '+%F %T')] runner finished family=$family"
    else
      code=$?
      echo "[$(date '+%F %T')] runner failed family=$family code=$code; retrying after 5s"
      sleep 5
    fi
  done
  echo "=== complete: $family ==="
done

echo "All requested families complete."
