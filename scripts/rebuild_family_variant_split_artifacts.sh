#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/.openclaw/workspace/projects/crypto-trading"
RUNNER="$ROOT/src/runners/build_family_variant_dashboard_artifacts.py"
OUT_DIR="$ROOT/data/intermediate/dashboard_payloads/family_variant_dashboard"

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
  local variants_dir="$dir/variants"
  [ -f "$dir/summary.json" ] || return 1
  [ -f "$dir/composite.json" ] || return 1
  [ -d "$variants_dir" ] || return 1
  local have expected
  have=$(find "$variants_dir" -maxdepth 1 -type f -name '*.json' | wc -l)
  expected=$(expected_variant_count "$family")
  [ "$have" -ge "$expected" ] || return 1
  return 0
}

for family in "${families[@]}"; do
  echo "=== ensure split artifacts: $family ==="
  until is_complete "$family"; do
    python3 "$RUNNER" --family "$family" --resume
    sleep 1
  done
  echo "=== complete: $family ==="
done
