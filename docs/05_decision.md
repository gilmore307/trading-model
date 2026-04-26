# Decision


## D001 - Market-state discovery is market-only

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

State discovery inputs must be market/data-source features only; strategy performance is excluded until after state tables exist.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.


## D002 - Model research is offline

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

This repository produces research artifacts and verdicts, not live trading decisions or order placement.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.


## D003 - Generated model artifacts stay out of Git

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

State tables, trained outputs, model artifacts, and research runs are runtime artifacts unless accepted as tiny fixtures.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.
