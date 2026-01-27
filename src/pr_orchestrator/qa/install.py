"""Dependency installation.

Installs project dependencies by running commands INSIDE the E2B sandbox.
"""

from __future__ import annotations

import json


def install_deps(workspace_id: str) -> dict[str, object]:
    """Install project dependencies inside the workspace.

    The installer examines the repository for dependency specification files
    by running checks inside the sandbox.  Priority order:

      1. ``uv.lock`` exists → ``uv sync --dev``
      2. ``pyproject.toml`` exists → ``uv sync`` or ``uv pip install -e .``
      3. ``requirements*.txt`` exists → ``pip install -r <file>``

    If no dependency manifest is found, installation is skipped.
    """
    from ..state import WORKSPACES
    from ..tools.workspace_tools import run_command as ws_run_command

    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        return {"success": False, "logs": "Workspace backend is not configured"}

    # Detect which installer to use by checking files inside sandbox
    detect_script = '''
import os
import json

result = {"installer": None, "file": None}

if os.path.isfile("uv.lock"):
    result = {"installer": "uv_lock", "file": "uv.lock"}
elif os.path.isfile("pyproject.toml"):
    result = {"installer": "pyproject", "file": "pyproject.toml"}
else:
    # Find requirements file
    for f in sorted(os.listdir(".")):
        if f.startswith("requirements") and f.endswith(".txt"):
            result = {"installer": "pip", "file": f}
            break

print(json.dumps(result))
'''

    detect_result = ws.backend.run(["python", "-c", detect_script], "repo", 30)

    if detect_result.get("exit_code", 1) != 0:
        return {"success": False, "logs": f"Detection failed: {detect_result.get('stderr', '')}"}

    try:
        detection = json.loads(detect_result.get("stdout", "{}"))
    except json.JSONDecodeError:
        detection = {"installer": None}

    installer = detection.get("installer")
    dep_file = detection.get("file")

    if not installer:
        return {"success": True, "logs": "No dependency manifests found; skipping install."}

    # Determine command based on installer type
    if installer == "uv_lock":
        cmd = "uv sync --dev"
    elif installer == "pyproject":
        cmd = "uv sync"
    elif installer == "pip":
        cmd = f"pip install -r {dep_file}"
    else:
        return {"success": True, "logs": "No recognized dependency format."}

    # Execute command
    logs = ""
    resp = ws_run_command(workspace_id, cmd, cwd="repo", mode="safe")
    logs += resp.get("stdout", "") + resp.get("stderr", "")
    success = resp.get("exit_code", 1) == 0 and not resp.get("timed_out", False)

    return {"success": success, "logs": logs}
