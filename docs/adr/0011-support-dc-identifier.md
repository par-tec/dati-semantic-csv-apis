# 11. Supper dc identifier

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-09

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

EU vocabularies may use dc http://purl.org/dc/elements/1.1/identifier
instead of skos:notation.

## Decision

When validationg elements we supports

- "http://www.w3.org/2004/02/skos/core#notation"
- "http://purl.org/dc/terms/identifier"
- "http://purl.org/dc/elements/1.1/identifier"

## Consequences

We can process EU vocbularies in stritc mode.
