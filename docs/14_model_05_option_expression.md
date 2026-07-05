# Model 05 Option Expression

Status: accepted current model contract; deterministic implementation present; promotion evidence deferred.

## Role

`M05 Option Expression` owns optional option/underlying expression after `M04 Unified Decision` has produced clean direct-underlying intent. It remains separate because option chains, liquidity, volatility, theta, spread, DTE, and structure constraints are a distinct domain.

M05 does not own event-family identity or event-impact taxonomy. Option-sensitive event attributes, such as triple witching, expiry/gamma flow, volatility-surface dislocation, IV crush, and option liquidity/spread disruption, are governed by M03 event-governance tooling and applied point-in-time by M03. M05 consumes those M03 event-state channels to decide expression consequences.

## Output

```text
model_05_option_expression
  -> expression_probability_surface      # primary option-expression probability function
  -> expression_candidate_set            # candidate-level comparable probability support
  -> option_expression_plan / expression_vector # derived selected expression summary
```

The model may choose underlying-only, long call, long put, no-option, or unavailable/not-applicable status according to accepted option-expression policy. Broker orders and account mutation remain outside `trading-model`.

M05 compares expression candidates on top of M04's source thesis distribution
surface. M04 owns the PIT underlying return distribution by horizon; M05 owns
the expression probability function:

```text
D5(e, p, tau) = calibrate(G05(D4(y, tau), option_chain, expression_policy))
```

- `D4` is M04's direct-underlying posterior `thesis_distribution_surface`.
- `G05` is the M05 expression/payoff translation operator.
- `D5` is the M05 `expression_probability_surface` over expression candidate
  `e`, payoff event `p`, and horizon `tau`.

For each decision M05 should preserve a complete candidate set containing the
underlying-equity proxy plus PIT-visible call and put candidates, including
rejected contracts with rejection reasons.

Each expression candidate vector must remain same-shaped so the underlying
proxy, call, and put candidates can be compared on one calibrated probability
scale. The vector is an expression-adjusted projection of the M04 thesis
surface: it inherits M04 direction, horizon, confidence, and
distribution-surface reference, then applies expression-specific cost,
liquidity, fill, DTE, theta, IV, Greek, spread, and policy adjustments.
`no_option_expression` / underlying proxy is a scored candidate, not an
unscored fallback.

The raw M04 distribution surface is not itself an option-expression probability
surface. M05 converts the surface and instrument terms into comparable
candidate payoff probabilities while preserving the M04/M05 boundary: M05 must
not redefine the M04 target-level direction thesis or use future realized
outcomes at decision time.

The local M01-M05 chain receipt now checks the surface handoff explicitly:
M05's `thesis_distribution_surface_ref` must match M04's emitted surface ref,
and the `expression_candidate_set.source_thesis_distribution_surface_summary`
must be available. This closes the read-only surface path from
`tradable_time_return_distribution_surface` evidence into M04 thesis formation
and then into M05 expression comparison without enabling production behavior.

For targets with structurally unavailable listed options, such as crypto spot, M05 emits `non_optionable_underlying` as the option surface status and falls back to direct-underlying/no-option expression states. It must not treat structural no-option availability as zero-valued IV, spread, flow, or open-interest evidence.

## Inputs

- `unified_decision_vector`.
- `thesis_distribution_surface` from M04, when available.
- `direct_underlying_intent` from M04.
- `event_state_vector` from M03, including option-price, volatility-surface, option-liquidity/spread, and expiry/gamma-flow impact channels.
- Point-in-time option-chain snapshots, bid/ask, liquidity, IV, Greeks, DTE, spread, and conservative fill assumptions.

## Training vs Live Invocation

Historical training/evaluation should preserve full-minute M04 thesis coverage. Minutes with temporarily missing option chains, non-optionable instruments, direct-underlying-only routes, or crypto routes should emit explicit option-surface status evidence instead of fabricated option selections. Structural no-option rows are a capability-conditioned action-space state; temporary option-chain-missing rows remain a data/source coverage state.

Live execution may invoke the heavier option-expression component only when M04 produces an option-expression-relevant thesis and option-chain context is available.

## Migration Source

`model_05_option_expression` is the current M05 implementation package and the only maintained option-expression model surface.

## Current Gate

The current implementation lives in `src/models/model_05_option_expression/` and local generate/evaluate/review entrypoints live under `scripts/models/model_05_option_expression/`. It consumes M04 `direct_underlying_intent` / `unified_decision_vector_ref` and the optional M04 `thesis_distribution_surface_ref`, emits `expression_probability_surface`, `expression_candidate_set`, `5_*` option-expression fields, and does not expose retired `underlying_action_plan` outputs. Production promotion still requires option-chain replay labels, candidate-level expression utility labels, cost/fill/theta/IV validation, baseline comparison, leakage checks, and manager-side promotion review.
