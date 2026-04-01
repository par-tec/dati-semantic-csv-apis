# 20. Defer Filesystem Cache for Vocabulary Dump Endpoint

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-04-01

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Deferred

## Context

The `/vocabularies/{agencyId}/{keyConcept}/dump` endpoint builds a gzip-compressed
JSON dump of all items in a vocabulary on every request.
The underlying SQLite database is read-only and loaded once at container startup,
so the output for a given `(agencyId, keyConcept)` pair is deterministic and
does not change within a process lifetime.

With `UVICORN_WORKERS=4`, an in-memory cache would be duplicated across processes.
A filesystem cache under `/tmp` would be shared across all workers and
auto-invalidated on container restart, which coincides with a DB refresh.

If traffic on the dump endpoint grows, or vocabulary sizes increase significantly,
a filesystem cache under `/tmp/dump_cache/{agencyId}_{keyConcept}_dump.json.gz`
should be introduced. The implementation would:

- Return the cached file directly if present, streaming it to the client.
- Generate and write the file on cache miss, then stream it.
- Require no explicit invalidation — the cache is ephemeral with the container.
- The Kubernetes deployment should set a reasonable `emptyDir` size limit to prevent disk exhaustion.

## Decision

- [x] No caching is implemented for now.
- [x] Wait for user feedback and traffic patterns before adding complexity of a filesystem cache.

## Consequences

Pros:

- No added complexity or writable volume requirement.
- No cache invalidation logic to maintain.

Cons:

- Each request re-generates the compressed dump from SQLite, duplicating CPU work
  across workers.
