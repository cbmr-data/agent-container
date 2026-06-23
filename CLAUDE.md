# agent-container

## Background

- agent-container is a sandbox for running AI agents with limited scope
- agent-container is written in Python 3.12+
- agent-container uses `uv` for project management
- agent-container targets Unix-like operating systems, primarily Linux

## Dev environment tips

- Setup development environment with `uv sync`
- Run lints and tests-suite with `uv run nox`
- Run individual tests with `uv run python3 -m pytest <filename>`
- Run pre-commit hooks with `pre-commit run -a` or `prek run -a`

## Testing

- ALWAYS attempt to add a test case for changed behavior
- ALWAYS verify that lints, unit-tests, and pre-commit checks pass
- NEVER change existing tests, unless explicitly instructed to
- ALWAYS read and copy the style of similar tests when adding new cases

## Writing code

- AVOID shortening variable names, e.g., use `version` instead of `ver`
- NEVER silently ignore error codes, exceptions, or other failures
- ALWAYS terminate immediately if invalid user-provided input is detected

## Git

- ALWAYS treat the git repository as read-only
- NEVER use `git clean` or `git checkout`, if this would remove unstaged changes
- NEVER push changes
