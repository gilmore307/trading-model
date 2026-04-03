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

## Next implementation phase

- [ ] map exact upstream artifact filenames/partitions to each first-implementation field at the per-file level
- [ ] define the first bar-alignment and tolerance rules for joining the two upstreams
- [ ] define the first base-layer-only model path
- [ ] define the first stock layer stack
- [ ] define the first ETF layer stack
- [ ] define the first crypto layer stack, including market-hours-conditional context rules
- [ ] define the first concrete unsupervised state representation
- [ ] define the first clustering / state-refresh workflow
- [ ] define the first usefulness-evaluation workflow against strategy outputs and oracle outputs
- [ ] rebuild code only after the upstream contracts and model shape are explicit
