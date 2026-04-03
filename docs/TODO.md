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
- [x] define model composite vs oracle composite as the main evaluation rule
- [x] split the system into state discovery first, strategy-state mapping second
- [x] define the first state-discovery spec
- [x] clarify that discovery may fully use market-descriptive data from `trading-data`
- [x] define the first market-rich discovery expansion order
- [x] define the first base-only feature formulas
- [x] replace mean/std scaling with robust preprocessing for clustering
- [x] define the past-only causality rule for every discovery feature
- [x] define multi-signal k-selection rather than silhouette-only selection
- [x] define the first stability-report structure
- [x] set GMM as the primary discovery model and KMeans as the baseline
- [x] define state -> policy mapping as a post-discovery step
- [x] define model composite construction as a post-discovery step
- [x] define partitioned output/report policy to avoid oversized files
- [x] define the first state-evaluation table shape
- [x] define the preferred-variant rule at the design level
- [x] switch evaluation horizons from hard-coded hour labels to canonical bar-based horizons
- [x] define the first exact state-winner score
- [x] define the first model-composite stitching defaults
- [x] define the first oracle-gap report shape
- [x] define exact state-winner tie-break defaults

## Next implementation phase

- [ ] define exact geometry metrics used in model selection
- [ ] define exact thresholds for cluster-size sanity and fragmentation
- [ ] define exact recurrence metrics and thresholds
- [ ] define exact refit-matching metric and threshold
- [ ] define the exact microstructure feature set for expansion 1
- [ ] define the exact derivatives-context feature set for expansion 2
- [ ] define the exact news/options feature set for expansion 3
- [ ] define the exact structural-context feature set for expansion 4
- [ ] tune threshold defaults after first empirical pass
- [ ] only after that, define implementation details
