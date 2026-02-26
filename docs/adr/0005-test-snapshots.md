# 5. Snapshot Testing

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-02-26

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Provide consistent test definitions and expectations.

## Decision

- [x] Use snapshot testing to easily verify the generated output of
      processing functions.
- [x] Store snapshots in a dedicated directory (e.g., `tests/data/snapshots/`)
      to keep them organized and separate from test code.
- [x] Avoid uploading large snapshots.

## Consequences

Pros:

- Improved communication of test intent and expected outcomes, making it easier for developers to understand and implement tests correctly.

Cons:

- Need to ensure snapshots are updated when the expected output changes, to avoid false test failures.
