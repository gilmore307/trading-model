# return_distribution_surface

Shared contracts and builders for tradable-time return distribution surfaces.

This package owns the current research path for replacing scalar model scores
with a calendar-aware conditional return distribution surface. The native
training unit is a point-in-time anchor paired with an equal-step tradable-time
target grid. Market events such as opens, closes, overnight gaps, and multi-day
targets are target-row context features and evaluation slices, not separate
label heads.

The current builder has two modes:

- `baseline`: one smooth quantile surface over `tau_trading_minutes`.
- `context`: the same surface with target-row context terms for session gaps,
  open windows, close windows, and overnight/multi-session structure. The
  context fit is shape constrained: it fits the lower quantile plus positive
  adjacent quantile spacings so predicted quantiles are ordered by construction.

`context` is the default because it tests the intended contract: one
tradable-time distribution function conditioned by market-calendar context,
instead of separate models for close/open/overnight labels.

The accepted research route is the shape-constrained `context` surface. The
current evidence gate is a read-only 2024-01 through 2025-01 SPY/QQQ validation over
272 sessions per symbol and about 1.23 million label rows per symbol. That gate
kept CDF monotonicity failures at zero and showed that open, close, intraday,
and session-gap calibration slices need context features inside the same
surface function.

The package is not yet a production model layer. It provides reusable
label-grid, surface-fitting, and validation code so M01 through M05 can adopt
the same surface contract without recreating incompatible local routes. The
batch entrypoint
`scripts/models/build_tradable_time_return_distribution_surface_bundle.py`
is the current closure route: it builds symbol/window surface artifacts, writes
`surface_bundle_manifest.json`, and can run the local M04/M05 surface handoff
smoke for each ready summary.

The remaining promotion path is to train and evaluate M01 through M05 against
walk-forward optionable-target surface bundles, not to return to scalar scores.
