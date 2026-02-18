# 2. Static Testing

<!-- In vim, use !!date -I to get current date. -->

Date: 2025-12-03

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Provide a consistent development environment.

## Decision

- [x] Use static testing tools to ensure code quality and consistency.
- [x] Use pre-commit hooks to run static tests before committing code.
- [x] Define PR and Issue templates to ensure that contributors provide necessary information and follow the contribution guidelines.
- [x] Use GitHub Actions to run static tests on every push and pull request.

## Consequences

- Static testing tools will help catch issues early in the development process, improving code quality and reducing bugs.
- Developers will need to setup pre-commit hooks and ensure they run successfully before committing code.
- PR and Issue templates will help maintain a consistent format for contributions, making it easier for maintainers to review and manage contributions.
