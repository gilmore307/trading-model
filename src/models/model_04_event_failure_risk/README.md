# model_04_event_failure_risk

Current package for Layer 4 `EventFailureRiskModel`.

The package emits point-in-time `event_failure_risk_vector` rows only from agent-reviewed event/strategy-failure gates. It covers scheduled calendar and market-structure event risk such as overnight/weekend/holiday windows, early closes, triple-witching, major option expiry, index reconstitution, Nasdaq-100 rebalance, halt, or other non-continuous-market windows. It must not ingest arbitrary raw news, promote event families automatically, emit standalone event alpha, choose exposures/actions/options, or mutate broker/storage lifecycle state.
