# 20 trading-strategy Input Boundary

_Last updated: 2026-04-03_

This document defines how `trading-model` should consume `trading-strategy` outputs.

## Core role split

`trading-strategy` is now the strategy execution layer.
It receives requested instrument / family / variant payloads, runs historical strategy-layer simulation, and writes standardized outputs.

`trading-model` should consume those outputs instead of treating strategy replay definition/execution as its long-term primary home.

## What `trading-model` should read from `trading-strategy`

At minimum, `trading-model` should be prepared to consume:
- variant trade outputs
- variant return series
- variant equity series
- family Oracle Composite outputs
- global Oracle Composite outputs
- monthly summary/meta files
- run-level manifest files

## Canonical storage shape from `trading-strategy`

The retained outputs follow the path rule:
- `data/<instrument>/<family>/<variant>/<YYMM>/`

Examples of consumed artifacts:
- `trades.jsonl`
- `returns.jsonl`
- `equity.jsonl`
- `summary.json`
- `meta.json`

Run-level coordination lives under:
- `data/<instrument>/_runs/run_manifest_*.json`

## Why this matters for `trading-model`

This allows `trading-model` to focus on:
- state modeling
- selector modeling
- comparison against Oracle ceilings
- promotion logic

rather than also owning the full strategy execution layer.

## Boundary rule

`trading-model` should ask questions like:
- given the strategy-layer outputs, what market-state-aware selector should we learn?
- how close can the learned/model-based composite get to Oracle?
- which families / variants deserve promotion?

It should not rely on remaining permanently responsible for defining every concrete strategy replay path in-tree.
