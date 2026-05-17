# Event-family all-association measurement

Contract: `event_family_all_association_v1`

This artifact emits an association row for every EventRiskGovernor family. It separates measured association from no-local-event and blocked-precondition statuses. It uses local source/study artifacts only and performs no provider calls, training, activation, broker/account mutation, destructive SQL, or artifact deletion.

`event_family_expanded_stability.csv` is a preparation-only stability screen for the next threshold/grading step. It does not assign final thresholds or grades.
