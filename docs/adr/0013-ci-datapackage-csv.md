# 1. Record architecture decisions

<!-- In vim, use !!date -I to get current date. -->

Date: 2025-12-03

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Providers need a way to integrate CSV creation inside their repository workflow,
using CLI commands.

## Decision

Create a github CI workflow in a separate file, that does the following:

1. when I

- commit into the asset/ or
- or run a manual workflow

I expect

- an asset-specific CI is executed

- ci-pre-tabular job is executed, that creates a datapackage in the #asset branch
  and commits it. No further actions should be triggered by this commit
  to avoid loops (e.g., skipci?)

- ci-tabular job is executed:

if a datapackage is present in asset/controlled-vocabularies/asset_name,
the job generates the asset_name.csv
validates asset_name.datapackage.yaml associated with asset_name.csv
creates a PR against the #asset branch with the CSV file
when the PR is merged, this action is not re-triggered automatically

## Consequences

- this repository tests the
