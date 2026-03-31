# 17. Harvesting PoC

<!-- In vim, use !!date -I to get current date. -->

Date: 2025-03-30

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

We need to create an harvesting process for the PoC,
to populate the datastore with real vocabularies and test the API.

## Decision

The harvesting process:

- [x] is implemented via the CLI `apistore collect` command.
- [x] collect supports logging and --force options like all commands.
- [x] collects either files or URLs passed as CLI arguments.
- [x] tests whether all URLs are reachable before downloading them.
- [x] if `--skip-not-found` option is passed, URLs returning 404
  are logged and skipped.
- [x] is executed in an environment separated from this repository.
- [x] references a released version of the CLI, to ensure stability and avoid breaking changes during development.
- [x] is executed periodically.

## Consequences

Pros:

- The harvesting process can be developed and tested independently
  from the main repository, separating the concerns between
  the development of the API and the harvesting process.

Cons:

- Requires coordination to test newer implementations
  of the harvesting CLI.
