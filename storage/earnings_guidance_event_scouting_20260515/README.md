# Earnings/guidance event-family scouting study

This artifact reruns the event-risk amplifier question using canonical Nasdaq earnings-calendar shells instead of Alpaca headline-keyword family labels.

## Inputs

- Abnormal option windows: `storage/option_activity_matched_control_study_20260515/matched_abnormal_windows.csv`
- Matched controls: `storage/option_activity_matched_control_study_20260515/matched_control_windows.csv`
- Calendar artifacts: `16` reviewed `release_calendar.csv` files

## Result

- Calendar events for target symbols: 10
- Abnormal windows tested: 152
- Windows on canonical earnings-shell dates: 9
- Windows with verified non-earnings controls: 152

This remains diagnostic only. It proves the shell/result/control separation can be enforced, but does not yet prove an event-layer model edge.
