# Model Decomposition Framework

Status: draft  
Owner intent: use one reviewable structure for every model layer before implementation, evaluation, or promotion work expands.

## Purpose

Every `trading-model` layer must be explained with the same nine-part decomposition before its implementation is treated as accepted design:

1. **Data** — what point-in-time input tables/artifacts are eligible, who owns them, and which timestamps define availability.
2. **Features** — what model-facing `X` fields are built from the data and which fields are diagnostic, evaluation-only, or intentionally unused.
3. **Prediction target** — what `y` is predicted, scored, ranked, optimized, or inferred; if unsupervised, what latent state/vector replaces a supervised target.
4. **Model mapping** — how the model maps `X` to `y` or to the output vector/parameter surface.
5. **Loss / error measure** — how wrongness is measured during fitting, scoring, calibration, or evaluation.
6. **Training / parameter update** — how parameters, thresholds, scalers, weights, or rules are updated over time without leakage.
7. **Validation / usefulness** — how the layer proves it helps the trading decision stack rather than merely fitting history.
8. **Overfitting control** — how the layer avoids hindsight, data snooping, unstable refits, over-complexity, and false confidence.
9. **Decision deployment** — how the output enters the real decision flow, including downstream consumers, gates, audit rows, and non-owned live execution boundaries.

This is a design and review template, not a mandate that every layer must be a supervised predictive model. Some layers produce continuous state vectors, parameter surfaces, rankers, overlays, or risk gates.

## Cross-Layer Rules

- Preserve point-in-time semantics: every row must be keyed by a time that was genuinely knowable to the system.
- Keep data acquisition and source evidence in `trading-data`; keep global shared contracts and registry terms routed through `trading-manager`.
- Do not collapse rich context into a scalar unless the retained output also preserves enough supporting fields for audit and downstream interpretation.
- Validation must test decision usefulness and leakage resistance, not only statistical fit.
- Deployment means offline decision-record integration in this repository; live/paper order mutation remains outside `trading-model`.

## Layer 1 Decomposition: MarketRegimeModel

Status: accepted as the Layer 1 V1 contract on 2026-05-01.

### 1. Data

Primary input:

```text
trading_data.feature_01_market_regime
```

Eligible evidence is broad-market, cross-asset, credit/rate/dollar/commodity, volatility, breadth, correlation, concentration, trend, and market-structure evidence available at or before `available_time`.

Layer 1 must not use sector/industry rotation labels, selected securities, strategy performance, option-contract outcomes, portfolio PnL, or future-return labels as construction inputs.

### 2. Features

`X` is the point-in-time feature vector from `feature_01_market_regime`, grouped into reviewed evidence blocks such as:

- price behavior and broad index returns;
- trend certainty and momentum persistence;
- volatility, correlation, breadth, and market-structure stress;
- credit, rate, dollar, commodity, and funding/liquidity proxies;
- sentiment/risk-appetite proxies;
- data-quality and signal-coverage diagnostics.

Feature roles must be explicit:

- **used** — contributes to a factor;
- **diagnostic/quality** — informs confidence or data quality;
- **evaluation-only** — used only after output construction to test usefulness;
- **intentionally unused** — excluded with a reason.

### 3. Prediction target

V1 has no supervised target and no required hard regime label.

The output is a continuous point-in-time market-state vector for:

```text
trading_model.model_01_market_regime
```

Current output fields are market-property factors: price behavior, trend certainty, capital/funding flow, sentiment, valuation pressure, fundamental strength, macro environment, market-wide structure, risk stress, transition pressure, and data quality. Observable returns, ratios, volatility, correlation, credit/rate/dollar/commodity, breadth, and risk-appetite signals are sensors that support those properties rather than public output names.

Future-return labels may be attached later for evaluation only, not for constructing the vector.

### 4. Model mapping from X to output

Current V1 mapping:

```text
rolling/expanding point-in-time scaler
  -> per-signal z-score with clipping/floors
  -> reviewed sign direction
  -> factor-level reducer
  -> bounded continuous factor values
  -> transition pressure and data-quality score
```

No current or future row may be used to fit the scaler for the row being scored.

### 5. Loss / error measure

Because V1 is unsupervised, construction does not optimize a supervised prediction loss. Wrongness is reviewed through proxy and evaluation measures:

- leakage or timestamp violation count;
- missing/low signal coverage;
- factor instability under rolling/expanding refits;
- unintuitive sign behavior against reviewed evidence blocks;
- poor downstream separation for future risk/return/drawdown diagnostics;
- poor usefulness for option-expression constraints, strategy compatibility, or portfolio risk policy.

If later supervised/calibrated sub-models are introduced, their loss functions must be recorded separately and must not redefine the Layer 1 output as a future-return predictor.

### 6. Training / parameter update

Current parameters are reviewed configuration and rolling state, not learned black-box weights:

- factor membership and signs live in config;
- lookback, minimum history, floors, z-score clipping, reducers, and coverage thresholds are explicit;
- rolling/expanding statistics update only from prior available rows;
- config changes require tests and decision/acceptance evidence.

Future learned weights may be added only after a leakage-safe training/evaluation design is accepted.

### 7. Validation / usefulness

Validation should show that the state vector is:

- point-in-time correct;
- stable enough for decision use but responsive to actual regime transitions;
- interpretable from supporting evidence;
- useful as background context for `OptionExpressionModel`, `StrategySelectionModel`, and `PortfolioRiskModel`;
- useful for risk/drawdown/volatility-transition diagnostics;
- not acting as a hidden sector/security selector.

Minimum validation evidence should include chronological splits, factor distribution checks, stability/refit checks, evaluation labels kept outside construction, and downstream usefulness tests.

### 8. Overfitting control

Controls:

- chronological train/validation/test or walk-forward evaluation;
- no future labels in vector construction;
- limited factor count with reviewed evidence membership;
- bounded/clipped factor values;
- minimum signal coverage and data-quality scoring;
- config-driven formulas rather than ad hoc notebook tuning;
- sector/industry rotation kept out of Layer 1;
- promotion gate requires evaluation-backed evidence, not visual plausibility.

### 9. Decision deployment

Layer 1 output enters the decision stack as broad market background:

```text
model_01_market_regime
  -> strategy compatibility / disabled-strategy context
  -> option-expression constraints such as DTE, delta/moneyness, IV/theta tolerance, and no-trade filters
  -> portfolio risk/exposure/sizing/execution-policy gate
  -> unified decision record audit context
```

It must not directly rank sectors, ETFs, or stocks. `SecuritySelectionModel` owns sector/industry rotation and candidate parameter surfaces.

## Remaining Layer Decomposition Queue

The same nine-part decomposition still needs to be completed for:

1. `SecuritySelectionModel` — sector/industry rotation and candidate parameter surfaces.
2. `StrategySelectionModel` — strategy-component composition and compatibility.
3. `TradeQualityModel` — trade outcome distribution, target/stop, MFE/MAE, and horizon.
4. `OptionExpressionModel` — stock/ETF/long-call/long-put expression and contract constraints.
5. `EventOverlayModel` — scheduled/breaking event risk and abnormal-activity overlays.
6. `PortfolioRiskModel` — final offline sizing, exposure, execution-style, exit, and kill-switch gate.
