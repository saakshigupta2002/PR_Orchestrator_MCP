"""Quality assurance tool implementations.

This module exposes tools for detecting project type, installing dependencies,
running tests, linting, type checking, formatting and pre-commit hooks.  The
functions delegate to the underlying ``qa`` package.
"""

from __future__ import annotations

from ..qa.detect import detect_project as _detect_project
from ..qa.install import install_deps as _install_deps
from ..qa.lint import run_format as _run_format
from ..qa.lint import run_lint as _run_lint
from ..qa.lint import run_precommit as _run_precommit
from ..qa.tests import run_tests as _run_tests
from ..qa.tests import run_typecheck as _run_typecheck


def detect_project(workspace_id: str) -> dict[str, str]:  # pylint: disable=unused-argument
    return _detect_project(workspace_id)


def install_deps(workspace_id: str) -> dict[str, object]:  # pylint: disable=unused-argument
    return _install_deps(workspace_id)


def run_tests(workspace_id: str, command: str | None = None) -> dict[str, object]:
    return _run_tests(workspace_id, command)


def run_lint(workspace_id: str, command: str | None = None) -> dict[str, object]:
    return _run_lint(workspace_id, command)


def run_typecheck(workspace_id: str, command: str | None = None) -> dict[str, object]:
    return _run_typecheck(workspace_id, command)


def run_format(workspace_id: str, command: str | None = None) -> dict[str, object]:
    return _run_format(workspace_id, command)


def run_precommit(workspace_id: str) -> dict[str, object]:
    return _run_precommit(workspace_id)
