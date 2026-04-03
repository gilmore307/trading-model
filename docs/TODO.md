# TODO

## Documentation

- [x] rewrite the docs around the new repository mission
- [x] make `trading-data` and `trading-strategy` the explicit required upstreams
- [x] define the repository as an unsupervised market-state modeling repo
- [x] remove old hybrid docs assumptions
- [x] verify upstream assumptions against real scripts instead of trusting example data

## Next implementation phase

- [ ] define the first concrete aligned learning table built from real `trading-data` artifacts and real `trading-strategy` outputs
- [ ] write the first exact field-level join contract
- [ ] define the first concrete unsupervised state representation
- [ ] define the first clustering / state-refresh workflow
- [ ] define the first usefulness-evaluation workflow against strategy outputs
- [ ] rebuild code only after the upstream contracts and model shape are explicit
