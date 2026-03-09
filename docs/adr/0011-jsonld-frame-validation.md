# 11. Projection Frame validation

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-09

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Proposed

## Context

schema.gov.it vocabularies use SKOS and DCAT,
and thus skos:notation and dcterms:identifier to identify concepts.

While most EU vocabularies use SKOS, some may only use Dublin Core
and reference <http://purl.org/dc/elements/1.1/identifier>
instead of skos:notation.

To ensure projection consistency between different
vocabularies and provide further validation
on field values,
the current JSON LD Frame validation process provides a "strict" mode that only accepts
a specific mapping between rdf:Properties
and JSON member names.

## Decision

When validating elements we support the following
mapping:

id:

- <http://www.w3.org/2004/02/skos/core#notation>
- <http://purl.org/dc/terms/identifier>
- <http://purl.org/dc/elements/1.1/identifier>

label:

- <http://www.w3.org/2004/02/skos/core#prefLabel>

vocab:

- <http://www.w3.org/2004/02/skos/core#inScheme>

## Consequences

We can process EU vocabularies
using <http://purl.org/dc/elements/1.1/identifier>
even in strict mode.
