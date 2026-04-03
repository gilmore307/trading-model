# TODO

## Documentation

- [x] rewrite the docs around the new repository mission
- [x] make `trading-data` and `trading-strategy` the explicit required upstreams
- [x] define the repository as an unsupervised market-state modeling repo
- [x] remove old hybrid docs assumptions
- [x] verify upstream assumptions against real scripts instead of trusting example data
- [x] define the first concrete learning-table contract
- [x] define layered dependency / graceful degradation as a core design rule
- [x] document stock / ETF / crypto as separate research-object scenarios
- [x] define the first layer policy matrix
- [x] define the first field mapping by dependency layer
- [x] define the first artifact-class to field-family mapping
- [x] define the first hard alignment / tolerance policy
- [x] define the first base-only model path

## Next implementation phase

- [ ] map exact upstream artifact filenames/partitions to each first-implementation field at the per-file level
- [ ] define the per-field aggregation rules for many-to-one joins
- [ ] define the first compact base-only feature set precisely
- [ ] define the first clustering choice and refresh policy
- [ ] define the first usefulness-evaluation report for base-only v1
- [ ] define the first stock layer stack after base-only v1
- [ ] define the first ETF layer stack after base-only v1
- [ ] define the first crypto layer stack after base-only v1, including market-hours-conditional context rules
- [ ] rebuild code only after the upstream contracts and model shape are explicit
