# 7. CLI Overview

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-02-26

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

CLI generates output files based on input data and configuration,
and those files can be accidentally overwritten.

## Decision

- [x] CLI uses different commands instead of options for creating and validating files
- [x] CLI requires the `--force` flag to overwrite generated files, and it is disabled by default

## Consequences

- Reduced risk of accidental overwriting of generated files
