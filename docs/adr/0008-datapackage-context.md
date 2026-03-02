# 8. Datapackage Context

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-02

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Datapackage metadata is derived from RDF vocabularies,
eventually deriving a single datapackage property from the lookup of multiple `rdf:Properties`.
It would be useful a means to convert the Frictionless Data Package metadata back to RDF
or at least to link the datapackage metadata to the original RDF vocabulary URI.

See <https://datapackage.org/standard/data-package/#sources>.

## Decision

- [x] Use the `sources` property of the Frictionless Data Package metadata to link to the original RDF vocabulary URI.
- [x] Don't use `@context` or other automatic means to convert the Frictionless Data Package metadata back to RDF,
  as these approaches are not reliable.

## Consequences

- The Frictionless Datapackage metadata is a byproduct of the RDF data.
- The original RDF data can still be retrieved.
