# Event layer final judgment

Contract: `event_layer_final_judgment_v1`

Final posture: `build_event_risk_governor_not_standalone_event_alpha`

Short answer: Build the event layer now only as EventRiskGovernor/EventIntelligenceOverlay. Do not build or train a standalone event alpha model under current evidence.

This artifact finalizes the current event-model decision from local reviewed evidence. It does not perform provider calls, model training, model activation, broker/account mutation, destructive SQL, or artifact deletion.

Standalone alpha families accepted now: `0`.
Risk/control families accepted now: `earnings_guidance_scheduled_shell;cpi_inflation_release`.
