# 19. Support Remote Harvest DB Download at Startup

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-04-01

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

The API requires a local `harvest.db` SQLite file at startup.
Deployments that pull the database from a remote artifact store must
handle the download externally, before the process starts.
Moving the download inside the startup lifecycle reduces operational
complexity and makes the container self-contained.

## Decision

- [x] Allow `HARVEST_DB` to be an `https://` URL in addition to a local path.
  When a URL is detected, the file is downloaded at startup using the URL
  basename as the local destination filename.
- [x] Reject non-`https://` schemes (`http://`, `file://`, …) at startup with a
  `ValueError`, to reduce SSRF surface.
- [x] Disable redirect following to avoid redirect-based SSRF.
- [x] Gate the download with two additional environment variables:
  - `HARVEST_DB_MAX_SIZE` (default 100 MB): abort if download exceeds this size.
  - `HARVEST_DB_TIMEOUT` (default 30 s, max 120 s): total download timeout.
- [x] Validate the downloaded database with the existing `_validate_db` logic
  before opening it.

## Consequences

Pros:

- No external download step needed in the deployment pipeline.
- Download limits and timeout are enforced at the application level.
- Validation catches corrupt or incompatible databases before serving traffic.

Cons:

- Startup time increases by the download duration.
- The downloaded file persists on the local filesystem alongside any
  pre-existing local DB; operators must manage disk space accordingly.
