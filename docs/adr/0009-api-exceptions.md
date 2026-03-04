# 9. API Exceptions

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-04

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

REST APIs errors must be logged
and returned to the client in a consistent format.
Responses should help the client to eventually
modify the request in order to succeed,
or desist for a reasonable time if the error is transient.

## Decision

- [x] Errors use Problem Details for HTTP APIs
  as already defined in the OpenAPI specification.
- [x] Exceptions are always catched and logged,
  while the client receives a generic error message that does not leak internal information about the API implementation.
- [x] API tests are generated via Schemathesis, a framework that generates successful and failing test cases based on the OpenAPI specification of the API.

## Consequences

- Comprehensive tests
- More code coverage
- Better error handling and logging
- No information about the API implementation is leaked to the client in case of errors.
