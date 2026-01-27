"""Unit tests for multi-use approval functionality.

These tests verify that approval IDs can be used for both
push and open_pr actions, but each action can only be used once.
"""


from pr_orchestrator.tools.approval_tools import (
    consume_approval,
    get_approval_record,
    request_approval,
)


def test_approval_multiuse_push_and_pr():
    """Test that one approval can be used for both push and open_pr."""
    result = request_approval(
        summary="Test changes",
        unified_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new",
        checks={"tests": "passed", "lint": "passed"},
        pr_draft=True,
        branch_plan={"branch": "fix/test", "from_ref": "main"},
        approved=True,
        pr_title="Fix test issue",
        pr_body="This PR fixes a test issue.",
    )

    assert result["approved"] is True
    approval_id = result["approval_id"]

    # Consume for push - should succeed
    assert consume_approval(approval_id, "push") is True

    # Consume for open_pr - should also succeed (multi-use)
    assert consume_approval(approval_id, "open_pr") is True

    # Both actions used - approval should be cleaned up
    assert get_approval_record(approval_id) is None


def test_approval_single_action_use():
    """Test that each action can only be used once per approval."""
    result = request_approval(
        summary="Test",
        unified_diff="diff",
        checks={},
        pr_draft=True,
        branch_plan={},
        approved=True,
    )

    approval_id = result["approval_id"]

    # First push should succeed
    assert consume_approval(approval_id, "push") is True

    # Second push should fail
    assert consume_approval(approval_id, "push") is False

    # open_pr should still work
    assert consume_approval(approval_id, "open_pr") is True


def test_approval_rejected():
    """Test that rejected approvals don't generate an approval_id."""
    result = request_approval(
        summary="Test",
        unified_diff="diff",
        checks={},
        pr_draft=True,
        branch_plan={},
        approved=False,
        notes="Changes need revision",
    )

    assert result["approved"] is False
    assert "approval_id" not in result


def test_approval_invalid_action():
    """Test that invalid actions are rejected."""
    result = request_approval(
        summary="Test",
        unified_diff="diff",
        checks={},
        pr_draft=True,
        branch_plan={},
        approved=True,
    )

    approval_id = result["approval_id"]

    # Invalid action should fail
    assert consume_approval(approval_id, "invalid_action") is False


def test_approval_nonexistent_id():
    """Test that non-existent approval IDs are rejected."""
    assert consume_approval("nonexistent-id", "push") is False


def test_approval_stores_pr_metadata():
    """Test that approval stores PR title, body, and issue URL."""
    result = request_approval(
        summary="Fix bug #123",
        unified_diff="diff content",
        checks={"tests": "passed"},
        pr_draft=True,
        branch_plan={"branch": "fix/issue-123"},
        approved=True,
        pr_title="Fix: Resolve issue #123",
        pr_body="This PR addresses issue #123.\n\nRelated to #123",
        issue_url="https://github.com/owner/repo/issues/123",
    )

    approval_id = result["approval_id"]
    record = get_approval_record(approval_id)

    assert record is not None
    assert record["pr_title"] == "Fix: Resolve issue #123"
    assert record["pr_body"] == "This PR addresses issue #123.\n\nRelated to #123"
    assert record["issue_url"] == "https://github.com/owner/repo/issues/123"

    # Clean up
    consume_approval(approval_id, "push")
    consume_approval(approval_id, "open_pr")
