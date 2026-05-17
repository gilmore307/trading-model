# Residual anomaly event discovery

Contract: `residual_anomaly_event_discovery_v1`

This artifact starts from Layers 1-7 evaluation residuals, not raw price anomalies. It then searches nearby point-in-time event families for explanations, observation-pool candidates, and strategy-promotion review packets. Strategy promotion remains blocked until an emitted packet receives agent review.

Safety: no provider calls, model training, model activation, broker/account mutation, service daemon start, destructive SQL, or artifact deletion.
