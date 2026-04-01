# 21. Add CORS Support to the Data API

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-04-01

## Status

Accepted

## Context

OpenAPI schema editors (e.g. Swagger Editor, Stoplight) fetch the
`/vocabularies/{agencyId}/{keyConcept}/openapi.yaml` endpoint directly from
the browser. Without CORS headers, cross-origin requests from these tools are
blocked by the browser, making the API spec unreachable for editing and
validation workflows.

## Decision

- [x] Add `starlette.middleware.cors.CORSMiddleware` to the Connexion app.
- [x] Expose `CORS_ORIGINS` as a comma-separated environment variable, defaulting
  to no origins (CORS disabled unless explicitly configured).
- [x] Allow only `GET` methods, since the API is read-only.

## Consequences

Pros:

- OpenAPI specs can be loaded directly into browser-based schema editors.
- No origins are allowed by default; operators opt in explicitly via `CORS_ORIGINS`.

Cons:

- Operators must configure `CORS_ORIGINS` correctly; a wildcard `*` would expose
  all endpoints to any origin.
