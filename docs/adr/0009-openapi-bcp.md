# 9. OpenAPI Best Current Practices

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-03

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

This project need to support the publication of REST APIs for controlled vocabularies.
APIs are defined using OpenAPI specifications documents that should be valid
according to the Italian Interoperability Framework (ModI).

## Decision

- [x] Specs are defined using OpenAPI 3.0 in multiple files and bundled
  using pre-commit hooks and CI checks.
- [x] Common components are defined in a shared `components.oas3.yaml` file.
- [x] Specs are validated using Spectral with the ModI ruleset
  published in <https://github.com/italia/api-oas-checker-rules>.
- [x] ModI ruleset have been added to the repository.
- [x] To avoid duplicate validation, some API checks (e.g. Checkov) have been disabled.

## Consequences

Pros:

- Specs are more maintainable and easier to read.
- Published specs are assembled in a single, versioned, file.
- Specs are compliant with the ModI ruleset.

Cons:

- A periodic review of Checkov rules vs Spectral rules is needed to avoid missing important checks.
  Results should be shared with the <https://github.com/italia/api-oas-checker-rules> maintainers
  to improve the ModI ruleset.
