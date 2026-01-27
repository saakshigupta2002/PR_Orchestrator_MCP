"""Linting, formatting and pre-commit runners.

All operations execute INSIDE the E2B sandbox.
"""

from __future__ import annotations

import json


def run_lint(workspace_id: str, command: str | None = None) -> dict[str, object]:
    """Run the linter in the workspace.

    Uses ``ruff check .`` by default.
    """
    from ..tools.workspace_tools import run_command as ws_run_command

    cmd = command or "ruff check ."
    resp = ws_run_command(workspace_id, cmd, cwd="repo", mode="safe")
    logs = (resp.get("stdout", "") or "") + (resp.get("stderr", "") or "")
    passed = resp.get("exit_code", 1) == 0 and not resp.get("timed_out", False)
    return {"passed": passed, "logs": logs}


def run_format(workspace_id: str, command: str | None = None) -> dict[str, object]:
    """Run the formatter on the codebase.

    Uses ``ruff format .`` by default.
    """
    from ..tools.workspace_tools import run_command as ws_run_command

    cmd = command or "ruff format ."
    resp = ws_run_command(workspace_id, cmd, cwd="repo", mode="safe")
    logs = (resp.get("stdout", "") or "") + (resp.get("stderr", "") or "")
    ran = resp.get("exit_code", 1) == 0 and not resp.get("timed_out", False)
    return {"ran": ran, "logs": logs}


def run_precommit(workspace_id: str) -> dict[str, object]:
    """Run pre-commit hooks if configuration exists.

    Checks for `.pre-commit-config.yaml` by running a check inside the sandbox.
    """
    from ..state import WORKSPACES
    from ..tools.workspace_tools import run_command as ws_run_command

    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        return {"ran": False, "passed": False, "logs": "Workspace backend is not configured"}

    # Check if pre-commit config exists inside sandbox
    check_script = '''
import os
import json
print(json.dumps({"exists": os.path.isfile(".pre-commit-config.yaml")}))
'''

    check_result = ws.backend.run(["python", "-c", check_script], "repo", 10)

    try:
        check = json.loads(check_result.get("stdout", "{}"))
    except json.JSONDecodeError:
        check = {"exists": False}

    if not check.get("exists"):
        return {"ran": False, "passed": True, "logs": "No pre-commit config; skipped."}

    resp = ws_run_command(workspace_id, "pre-commit run --all-files", cwd="repo", mode="expert")
    logs = (resp.get("stdout", "") or "") + (resp.get("stderr", "") or "")
    passed = resp.get("exit_code", 1) == 0 and not resp.get("timed_out", False)
    return {"ran": True, "passed": passed, "logs": logs}
