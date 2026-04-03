# TODO

## Documentation

- [x] rewrite the docs around the new repository mission
- [x] make `trading-data` and `trading-strategy` the explicit required upstreams
- [x] define the repository as an unsupervised market-state modeling repo
- [x] remove old hybrid docs assumptions
- [x] verify upstream assumptions against real scripts instead of trusting example data
- [x] define the first concrete learning-table contract

## Next implementation phase

- [ ] write the first exact field-level mapping from `trading-data` artifacts into the learning table
- [ ] write the first exact field-level mapping from `trading-strategy` artifacts into the learning table
- [ ] define the first bar-alignment and tolerance rules for joining the two upstreams
- [ ] define the first concrete unsupervised state representation
- [ ] define the first clustering / state-refresh workflow
- [ ] define the first usefulness-evaluation workflow against strategy outputs and oracle outputs
- [ ] rebuild code only after the upstream contracts and model shape are explicit
