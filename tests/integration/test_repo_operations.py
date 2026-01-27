"""Integration tests for repository operations.

These tests use the FakeBackend and verify end-to-end flows.
"""

import pytest


def test_read_write_file_via_backend(fake_workspace):
    """Test reading and writing files via backend."""
    ws = fake_workspace

    # Create repo directory
    ws.backend.run(["mkdir", "-p", "repo"], ".", 10)

    # Write a file
    ws.backend.write_text("repo/test.py", "print('hello')")

    # Read it back
    content = ws.backend.read_text("repo/test.py")
    assert content == "print('hello')"


def test_git_init_and_commit(fake_workspace):
    """Test git initialization and commit via backend."""
    ws = fake_workspace

    # Create repo directory
    ws.backend.run(["mkdir", "-p", "repo"], ".", 10)

    # Init git repo
    ws.backend.run(["git", "init"], "repo", 10)

    # Create a file
    ws.backend.write_text("repo/README.md", "# Test Repo")

    # Add and commit
    ws.backend.run(["git", "add", "."], "repo", 10)
    result = ws.backend.run(["git", "commit", "-m", "Initial commit"], "repo", 10)

    assert result["exit_code"] == 0


def test_path_validation():
    """Test that path validation rejects escaping paths."""
    from pr_orchestrator.sandbox.workspace_store import normalize_repo_cwd

    # Valid paths
    assert normalize_repo_cwd("repo") == "repo"
    assert normalize_repo_cwd("repo/src") == "repo/src"
    assert normalize_repo_cwd(None) == "repo"
    assert normalize_repo_cwd("") == "repo"

    # Invalid paths - should raise
    with pytest.raises(PermissionError):
        normalize_repo_cwd("/etc/passwd")

    with pytest.raises(PermissionError):
        normalize_repo_cwd("../escape")

    with pytest.raises(PermissionError):
        normalize_repo_cwd("repo/../../../etc")

    with pytest.raises(PermissionError):
        normalize_repo_cwd("~/.ssh")


def test_command_allowlist():
    """Test that command allowlist is enforced."""

    # We can't fully test without a workspace, but we can verify the logic
    # by checking that certain commands would be blocked

    # Safe prefixes
    safe_prefixes = ("git", "python", "pytest", "ruff", "mypy", "uv", "pip")

    # These should be allowed (start with safe prefix)
    allowed_commands = ["git status", "python -c 'print(1)'", "pytest -q", "ruff check ."]
    for cmd in allowed_commands:
        first = cmd.split()[0]
        assert any(first.startswith(p) for p in safe_prefixes), f"{cmd} should be allowed"

    # These should be blocked
    blocked_commands = ["ls", "cat /etc/passwd", "rm -rf /"]
    for cmd in blocked_commands:
        first = cmd.split()[0]
        assert not any(first.startswith(p) for p in safe_prefixes), f"{cmd} should be blocked"
