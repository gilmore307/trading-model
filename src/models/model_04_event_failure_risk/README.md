# model_04_event_failure_risk

Current package for Layer 4 `EventFailureRiskModel`.

The package emits point-in-time `event_failure_risk_vector` rows only from agent-reviewed event/strategy-failure gates or frozen M06 accepted focus-pool event contracts. It covers scheduled calendar and market-structure event risk such as overnight/weekend/holiday windows, early closes, triple-witching, major option expiry, index reconstitution, Nasdaq-100 rebalance, halt, or other non-continuous-market windows.

M06 owns event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, and later demotion/split/reweight/parameter revision. Layer 4 consumes those frozen parameters and estimates only quantitative response/failure-risk features, including `4_event_response_strength_score_<horizon>`, `4_event_response_direction_score_<horizon>`, and `4_event_response_uncertainty_score_<horizon>`. Layer 5 is the first layer allowed to produce adjusted after-cost alpha.

This package must not ingest arbitrary raw news, promote event families automatically, mutate M06 event parameters, emit standalone event alpha, choose exposures/actions/options, or mutate broker/storage lifecycle state.
