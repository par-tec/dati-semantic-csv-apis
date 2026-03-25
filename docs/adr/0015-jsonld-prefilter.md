# 15. Add pre-filtering option to JSON-LD framing process

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-25

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Framing large vocabularies can be resource-intensive,
especially when the RDF data contains information that
is not relevant to the user's needs, such as
inverse relationships.

## Decision

- [x] Add a `--pre-filter-by-type` option to the `jsonld` command.
- [x] When this option is set, the JSON-LD will be pre-filtered
  to include only fields matching the specified types before the framing process.
- [x] The CLI will output a warning message when this option is used.

## Consequences

Pros:

- Reduces memory usage and processing time when framing large vocabularies with many irrelevant fields.

Cons:

- `@embed` fields referencing non-matching types will be lost, which may lead to incomplete data in the framed output.
