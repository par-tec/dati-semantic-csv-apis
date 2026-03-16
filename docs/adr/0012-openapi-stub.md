# 12. OpenAPI stub

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-10

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Providers that want to publish an API for their vocabularies
need to create an OpenAPI specification file in the vocabulary directory.

To facilitate this process, we can provide a stub OpenAPI specification
that includes the necessary structure and references to the vocabulary data.
Providers need to modify the stub file to validate it and ensure its correctness.

## Decision

- [x] The `openapi` command of the CLI will generate a stub OpenAPI specification file.
- [x] The `openapi` command requires the RDF vocabulary information to populate
  the metadata fields in the OpenAPI specification (e.g., title, description, version).
- [ ] The generated file will include a comment with provider instructions.
- [ ] The OAS file will not include `servers` or `paths` sections: these will be
  dynamically provided by the Data API implementation.
- [ ] Schema array fields will be constrained using maxItems and minItems.
- [ ] Schema numeric fields will not be constrained because this depends
  on Provider needs (Q: use `format` int64?).
- [ ] Schema labels and URIs will be constrained to suitable values.
- [ ] Item identifiers should be \<= 64 characters.

## Consequences

- Providers can quickly create an OpenAPI specification
  for their vocabulary by modifying the generated stub file.
- Vocabularies without an OAS file will not be published
  as an API, even if NDC:keyConcept is defined.
