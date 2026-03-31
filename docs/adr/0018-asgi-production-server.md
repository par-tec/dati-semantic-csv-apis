# 18. Use uvicorn as Production ASGI Server

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-31

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

The API is built on `connexion.AsyncApp`, which exposes a standard ASGI interface.
To provide a production-grade deployment,
we need to run the ASGI application with a server that supports
tunable concurrency, graceful shutdown, access logging,
and proper signal handling.

Uvicorn supports setting the number of worker processes via
command line options or environment variables.

## Decision

- [x] Use uvicorn directly as the ASGI server, in the container.
- [x] Pass configuration variables (e.g., the number of workers)
  via environment variables (e.g., `UVICORN_WORKERS`).
- [x] Ensure that the API application code is thread-safe when
  accesssing SQLite.

## Consequences

Pros:

- Production-grade server with proper signal handling and graceful shutdown.
- Worker configuration is outside the application code.

Cons:

- Each worker process loads the full application into its own memory space,
  so memory usage scales linearly with `UVICORN_WORKERS`.
- In case more complex concurrency management is needed in the future,
  we may need to switch to a more complex server like Gunicorn with
  Uvicorn workers, which is an overly complex addition to the deployment.
