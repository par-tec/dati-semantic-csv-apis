# 2. Static Testing

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-02-18

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Provide consistent test definitions and expectations.

## Decision

- [x] Test docstrings have the following template:

  ```python
  """
  Test description.

  Given:
      - Test preconditions and setup.

  When:
      - Action or behavior being tested.

  Then:
      - Expected outcome or result.
  """
  ```

- [x] Test descriptions in data files (e.g., YAML) follow the same template as docstrings to ensure consistency and clarity in test expectations.

## Consequences

- Better readability and maintainability of tests by providing a clear structure for test descriptions and expectations.
- Improved communication of test intent and expected outcomes, making it easier for developers to understand and implement tests correctly.
