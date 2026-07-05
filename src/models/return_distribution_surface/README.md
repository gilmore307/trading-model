# return_distribution_surface

Shared pilot contracts and builders for tradable-time return distribution
surfaces.

This package owns the current research path for replacing scalar model scores
with a calendar-aware conditional return distribution surface. The native
training unit is a point-in-time anchor paired with an equal-step tradable-time
target grid. Market events such as opens, closes, overnight gaps, and multi-day
targets are target-row context features and evaluation slices, not separate
label heads.

The current pilot has two modes:

- `baseline`: one smooth quantile surface over `tau_trading_minutes`.
- `context`: the same surface with target-row context terms for session gaps,
  open windows, close windows, and overnight/multi-session structure. The
  context fit is shape constrained: it fits the lower quantile plus positive
  adjacent quantile spacings so predicted quantiles are ordered by construction.

`context` is the default because it tests the intended contract: one
tradable-time distribution function conditioned by market-calendar context,
instead of separate models for close/open/overnight labels.

The package is not a production model layer. It provides reusable label-grid,
surface-fitting, and validation code so M01 through M05 can adopt the same
surface contract without recreating incompatible local pilots.
