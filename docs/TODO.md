# TODO

## Repo split: trading-model vs quantitative-trading

- [x] define repo split direction and document the new boundary
- [ ] classify modules into keep / move / split buckets
- [ ] migrate realtime/runtime/execution code to `quantitative-trading`
- [ ] remove hybrid-repo docs once split is complete
- [ ] delete truly obsolete leftovers only after migration stabilizes

## Data ingestion isolation / completion

- [x] switch primary raw fetch scripts to direct monthly partition writes
- [ ] define ingestion layer only in terms of its own responsibilities (no downstream rewrites mixed in)
- [ ] add explicit bootstrap-new-symbol workflow and docs
- [ ] add earliest-available discovery for new symbols
- [ ] add month-level progress / resume metadata for long bootstrap jobs
- [ ] add incomplete-month safeguards / markers
- [ ] validate ingestion layer end-to-end on its own terms

## Historical modeling / research

- [ ] keep `trading-model` focused on historical data, research, parameter modeling, and backtests
- [ ] review `src/review/`, `src/market/`, and `src/routing/` for keep-vs-move decisions under the repo split
