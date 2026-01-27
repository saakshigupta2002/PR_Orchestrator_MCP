"""Project type detection.

Detects project type by running checks INSIDE the E2B sandbox.
Only Python repositories are supported in v1.
"""

from __future__ import annotations

import json


def detect_project(workspace_id: str) -> dict[str, str]:
    """Detect the project type and return default QA commands.

    This implementation runs detection inside the E2B sandbox by executing
    a Python script that checks for marker files.
    
    Only Python repositories are supported in v1.
    """
    from ..state import WORKSPACES

    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        raise RuntimeError("Workspace backend is not configured")

    # Run a Python script inside the sandbox to detect project type
    detect_script = '''
import os
import json

result = {"type": "unknown", "markers": []}

# Check for Python markers
python_markers = [
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
]

found_markers = []
for marker in python_markers:
    if os.path.isfile(marker):
        found_markers.append(marker)
    # Also check for requirements*.txt pattern
    if marker == "requirements.txt":
        for f in os.listdir("."):
            if f.startswith("requirements") and f.endswith(".txt"):
                if f not in found_markers:
                    found_markers.append(f)

if found_markers:
    result["type"] = "python"
    result["markers"] = found_markers

print(json.dumps(result))
'''

    result = ws.backend.run(["python", "-c", detect_script], "repo", 30)

    if result.get("exit_code", 1) != 0:
        raise RuntimeError(f"Project detection failed: {result.get('stderr', '')}")

    try:
        detection = json.loads(result.get("stdout", "{}"))
    except json.JSONDecodeError:
        detection = {"type": "unknown", "markers": []}

    # Enforce Python-only in v1
    if detection.get("type") != "python":
        raise NotImplementedError(
            "Only Python repositories are supported in v1. "
            "No pyproject.toml, setup.py, setup.cfg, or requirements*.txt found."
        )

    # Return default commands for Python
    return {
        "type": "python",
        "test_command": "pytest -q",
        "lint_command": "ruff check .",
        "typecheck_command": "mypy .",
        "format_command": "ruff format .",
        "markers": detection.get("markers", []),
    }
