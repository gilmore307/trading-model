# Model Training Governance

This package owns reusable training-artifact mechanics for maintained model layers.

It does not own layer objectives, feature definitions, labels, promotion gates, or runtime
activation. Each layer remains responsible for its own target semantics and allowed inputs;
shared helpers only standardize artifact shape, dependency loading, model serialization, and
point-in-time inference mechanics.
