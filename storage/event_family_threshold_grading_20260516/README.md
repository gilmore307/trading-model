# Event-family threshold grading queue

Contract: `event_family_threshold_grading_v1`

This artifact shapes the next threshold/grading queue. Families with measured no-clear local association are deleted from the active threshold queue, not physically deleted from evidence storage. No provider calls, model training, activation, broker/account mutation, artifact deletion, or destructive SQL are performed.
