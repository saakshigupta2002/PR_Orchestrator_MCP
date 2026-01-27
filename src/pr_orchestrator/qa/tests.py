"""Test and type check runners.

All operations execute INSIDE the E2B sandbox.
"""

from __future__ import annotations


def run_tests(workspace_id: str, command: str | None = None) -> dict[str, object]:
    """Run the test suite in the workspace.

    Supports running pytest or unittest.  If no command is provided, ``pytest -q``
    is used.  Captures the exit code, raw logs and extracts a list of
    failing test identifiers via ``parse_failing_tests``.
    """
    from ..tools.workspace_tools import run_command as ws_run_command
    from .failure_parser import parse_failing_tests

    cmd = command or "pytest -q"
    resp = ws_run_command(workspace_id, cmd, cwd="repo", mode="safe")
    logs = (resp.get("stdout", "") or "") + (resp.get("stderr", "") or "")
    exit_code = resp.get("exit_code", 1)
    passed = exit_code == 0 and not resp.get("timed_out", False)

    failing_tests: list[str] = []
    if not passed:
        failing_tests = parse_failing_tests(logs)

    return {
        "passed": passed,
        "exit_code": exit_code,
        "failing_tests": failing_tests,
        "logs": logs,
    }


def run_typecheck(workspace_id: str, command: str | None = None) -> dict[str, object]:
    """Run the type checker (mypy) on the repository.

    If no command is provided, ``mypy .`` is used.
    """
    from ..tools.workspace_tools import run_command as ws_run_command

    cmd = command or "mypy ."
    resp = ws_run_command(workspace_id, cmd, cwd="repo", mode="safe")
    logs = (resp.get("stdout", "") or "") + (resp.get("stderr", "") or "")
    passed = resp.get("exit_code", 1) == 0 and not resp.get("timed_out", False)

    return {
        "passed": passed,
        "logs": logs,
    }
