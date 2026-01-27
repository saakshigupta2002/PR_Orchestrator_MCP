# Contributing Guide

First off, thanks for taking the time to contribute!  This project welcomes contributions from the community.  In order to make the process as smooth as possible, please follow these guidelines.

## Workflow

1. **Fork the repository** on GitHub and clone your fork locally.
2. Create a new branch from `main` for your change.  If you are addressing an open issue, name your branch `issue/<number>`; otherwise use a descriptive name.
3. Make your changes.  Be sure to:
   * Add or update unit tests in `tests/` to cover the new behaviour.
   * Run `make test lint typecheck` to ensure the test suite passes, the code is formatted, and there are no type errors.
   * Update documentation in `docs/` as necessary.
   * Add a new entry to `CHANGELOG.md` under the `Unreleased` section (create it if it does not exist).
4. Push your branch to your fork and open a **draft** pull request against `main` on this repository.  The PR body should include:
   * **Summary:** a brief description of why the change is needed.
   * **Changes:** a high‑level summary of what was changed.
   * **Unit Tests Added/Updated:** list of new or modified tests.
   * **Verification:** exact commands you ran (e.g. tests, lint, typecheck).
   * **Notes/Risks:** anything reviewers should be aware of.
5. A maintainer will review your PR.  You may be asked to make changes; please address feedback promptly.
6. Once approved, your PR will be merged.  Do **not** use auto‑close keywords such as "closes"/"fixes" in your PR description as the MCP server prohibits them.

## Development Tips

* Use a virtual environment to manage dependencies.
* Run `pre-commit install` after cloning to enable automatic linting and formatting.
* When adding new tools or modifying existing ones, update `docs/tool-spec.md` and any relevant unit tests.
* Avoid introducing dependencies not listed in `pyproject.toml` without discussing with maintainers.

## Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting.  Run `make lint` to check style and `make format` to automatically format your code.  Type checking is enforced with [mypy](https://mypy-lang.org/); run `make typecheck` to ensure static types are valid.

## Security

Never commit secrets or access tokens.  Configuration values must be loaded from `.env` files at runtime.  If you discover a security vulnerability, please refer to `SECURITY.md` for responsible disclosure guidelines.