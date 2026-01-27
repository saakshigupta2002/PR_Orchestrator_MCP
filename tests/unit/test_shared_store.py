"""Unit tests for shared store functionality.

These tests verify that workspace IDs work across tool modules.
"""



def test_workspace_id_accessible_via_state(fake_workspace):
    """Test that workspace can be accessed via shared state."""
    from pr_orchestrator.state import WORKSPACES

    # Access workspace via shared store
    ws = WORKSPACES.get(fake_workspace.id)
    assert ws is not None
    assert ws.id == fake_workspace.id
    assert ws.backend is not None


def test_workspace_backend_can_run_commands(fake_workspace):
    """Test that workspace backend can execute commands."""
    ws = fake_workspace

    # Run a simple command
    result = ws.backend.run(["echo", "hello"], ".", 10)

    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]


def test_workspace_backend_can_read_write_files(fake_workspace):
    """Test that workspace backend can read/write files."""
    ws = fake_workspace

    # Write a file
    ws.backend.write_text("test.txt", "hello world")

    # Read it back
    content = ws.backend.read_text("test.txt")
    assert content == "hello world"
