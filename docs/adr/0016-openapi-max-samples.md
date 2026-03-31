# 16. Add max-samples option to openapi create

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-31

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Processing large vocabularies can be resource-intensive.

## Decision

- [x] Add a `--max-samples` option to the `openapi create` command.
- [x] When this option is set, dataset is sampled using the specified value.
- [x] Validation is still performed over the entire dataset.
- [x] By default there is no sampling.

## Consequences

Pros:

- Reduces memory usage and processing time when processing large vocabularies.

- Validation is performed over the entire dataset.
  Cons:

- Sampling could lead to incomplete OpenAPI because embedded resources may reference to nodes that were excluded from the sample.
