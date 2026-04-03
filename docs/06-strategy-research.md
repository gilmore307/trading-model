# 06 Strategy Research

This document defines the strategy-research role of `trading-model`.

## Purpose

`trading-model` should study the strategy-result surface and identify what is worth promoting downstream.

Main research questions:
- which strategy families are worth keeping?
- which variants are robust across historical windows?
- where does switching add value beyond a strong single variant?
- what selector/model layer can convert that opportunity into a forward-usable output?

## Working unit

The repo should not treat a strategy as only a short label such as `MA` or `RSI`.
The meaningful research unit is usually one of:
- strategy family
- variant
- parameter region
- state-conditioned behavior

## Family-first workflow

The preferred workflow is:
1. define or ingest a candidate family surface
2. evaluate family variants on historical data
3. compare intra-family robustness and redundancy
4. keep strong representatives and remove dominated regions
5. compare family champions across families
6. study where state-conditioned switching may improve results

## Baseline and composite comparison

Research should preserve at least these anchors:
- strong single-variant baselines
- Oracle-style upper-bound comparisons
- executable selector/model outputs

This is required because the repo must distinguish between:
- theoretical switching opportunity
- actually capturable switching opportunity

## Selector/model interpretation

The end goal is not only to find the best fixed variant.
The more important goal is to learn:
- which strategy behavior fits which market condition
- how much value market-state-aware selection can capture
- which families and outputs deserve downstream promotion

## Relationship to market-state work

Strategy research and market-state work should be developed together.

Why:
- family research reveals where switching opportunity exists
- market-state work tries to explain when different behavior should be preferred
- selector/model work connects the two

## What this repo should publish

Good outputs from this layer include:
- family comparison summaries
- variant ranking artifacts
- Oracle-gap comparisons
- selector/model evaluation outputs
- promotion-ready candidate recommendations

## Historical notes

Older candidate-pool, implementation-plan, and detailed framework notes were moved into `docs/archive/legacy/`.
Those remain useful historical design context, but this file is now the main active entry point.
