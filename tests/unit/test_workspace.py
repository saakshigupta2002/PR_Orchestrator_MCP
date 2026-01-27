"""Unit tests for workspace operations.

These tests use the FakeBackend from conftest.py and don't require E2B.
"""

import pytest


def test_workspace_store_get_returns_workspace(fake_workspace):
    """Test that workspace store returns workspace by ID."""
    from pr_orchestrator.state import WORKSPACES

    ws = WORKSPACES.get(fake_workspace.id)
    assert ws is not None
    assert ws.id == fake_workspace.id


def test_workspace_store_get_raises_for_unknown():
    """Test that workspace store raises KeyError for unknown ID."""
    from pr_orchestrator.state import WORKSPACES

    with pytest.raises(KeyError, match="Unknown workspace"):
        WORKSPACES.get("nonexistent-id")


def test_workspace_destroy(fake_workspace):
    """Test workspace destruction."""
    from pr_orchestrator.state import WORKSPACES

    result = WORKSPACES.destroy(fake_workspace.id)
    assert result is True

    with pytest.raises(KeyError):
        WORKSPACES.get(fake_workspace.id)


def test_workspace_destroy_nonexistent():
    """Test destroying non-existent workspace returns False."""
    from pr_orchestrator.state import WORKSPACES

    result = WORKSPACES.destroy("nonexistent-id")
    assert result is False
