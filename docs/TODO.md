# TODO

## Data ingestion isolation / completion

- [x] switch primary raw fetch scripts to direct monthly partition writes
- [x] add shared monthly JSONL directory loader for downstream consumers
- [x] update core research dataset builders to read monthly partition directories
- [ ] add explicit bootstrap-new-symbol workflow and docs
- [ ] add earliest-available discovery for new symbols
- [ ] add month-level progress / resume metadata for long bootstrap jobs
- [ ] add incomplete-month safeguards / markers
- [ ] validate end-to-end flow: fetch -> market state -> parameter utility datasets
- [ ] after ingestion layer stabilizes, audit and remove truly obsolete legacy fetch/research scripts
