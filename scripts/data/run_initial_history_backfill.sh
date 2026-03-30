#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
mkdir -p logs/data-fetch

PY="./.venv/bin/python"
CANDLE="scripts/data/fetch_okx_history_candles.py"
DERIV="scripts/data/fetch_okx_derivatives_context.py"

run_candle() {
  local inst_id="$1"
  local out_path="$2"
  local log_path="$3"
  echo "[$(date -Is)] start candle ${inst_id}" | tee -a "$log_path"
  "$PY" "$CANDLE" \
    --inst-id "$inst_id" \
    --bar 1m \
    --start 2022-01-01T00:00:00Z \
    --output "$out_path" \
    --resume \
    --sleep-seconds 0.35 \
    --progress-every 200 \
    --checkpoint-every 25 \
    >> "$log_path" 2>&1
  echo "[$(date -Is)] done candle ${inst_id}" | tee -a "$log_path"
  sleep 8
}

run_deriv() {
  local inst_id="$1"
  local log_path="$2"
  echo "[$(date -Is)] start derivatives ${inst_id}" | tee -a "$log_path"
  "$PY" "$DERIV" \
    --inst-id "$inst_id" \
    --kind all \
    --timeframe 5m \
    --limit 500 \
    --rounds 1 \
    --resume \
    >> "$log_path" 2>&1
  echo "[$(date -Is)] done derivatives ${inst_id}" | tee -a "$log_path"
  sleep 5
}

run_candle "BTC-USDT-SWAP" "data/raw/okx/candles/BTC-USDT-SWAP/1m/BTC-USDT-SWAP_1m_20220101_now.jsonl" "logs/data-fetch/btc_usdt_swap_1m_20220101_now.log"
run_deriv "BTC-USDT-SWAP" "logs/data-fetch/btc_usdt_swap_derivatives.log"

run_candle "BTC-USDT" "data/raw/okx/candles/BTC-USDT/1m/BTC-USDT_1m_20220101_now.jsonl" "logs/data-fetch/btc_usdt_1m_20220101_now.log"

run_candle "ETH-USDT-SWAP" "data/raw/okx/candles/ETH-USDT-SWAP/1m/ETH-USDT-SWAP_1m_20220101_now.jsonl" "logs/data-fetch/eth_usdt_swap_1m_20220101_now.log"
run_deriv "ETH-USDT-SWAP" "logs/data-fetch/eth_usdt_swap_derivatives.log"

run_candle "ETH-USDT" "data/raw/okx/candles/ETH-USDT/1m/ETH-USDT_1m_20220101_now.jsonl" "logs/data-fetch/eth_usdt_1m_20220101_now.log"

run_candle "SOL-USDT-SWAP" "data/raw/okx/candles/SOL-USDT-SWAP/1m/SOL-USDT-SWAP_1m_20220101_now.jsonl" "logs/data-fetch/sol_usdt_swap_1m_20220101_now.log"
run_deriv "SOL-USDT-SWAP" "logs/data-fetch/sol_usdt_swap_derivatives.log"

run_candle "SOL-USDT" "data/raw/okx/candles/SOL-USDT/1m/SOL-USDT_1m_20220101_now.jsonl" "logs/data-fetch/sol_usdt_1m_20220101_now.log"

echo "[$(date -Is)] initial history backfill finished" | tee -a logs/data-fetch/backfill-master.log
