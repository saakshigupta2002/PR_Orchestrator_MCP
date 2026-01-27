"""Unit tests for PR body validation.

These tests verify that auto-close keywords are rejected in PR bodies.
"""

import re

import pytest


def test_auto_close_pattern_matches_closes():
    """Test that 'closes #N' matches the pattern."""
    pattern = r"\b(closes|fixes|resolves)\s+#\d+"

    assert re.search(pattern, "This PR closes #123", re.IGNORECASE) is not None
    assert re.search(pattern, "Closes #456", re.IGNORECASE) is not None
    assert re.search(pattern, "CLOSES #789", re.IGNORECASE) is not None


def test_auto_close_pattern_matches_fixes():
    """Test that 'fixes #N' matches the pattern."""
    pattern = r"\b(closes|fixes|resolves)\s+#\d+"

    assert re.search(pattern, "This PR fixes #123", re.IGNORECASE) is not None
    assert re.search(pattern, "Fixes #456", re.IGNORECASE) is not None


def test_auto_close_pattern_matches_resolves():
    """Test that 'resolves #N' matches the pattern."""
    pattern = r"\b(closes|fixes|resolves)\s+#\d+"

    assert re.search(pattern, "This resolves #123", re.IGNORECASE) is not None
    assert re.search(pattern, "Resolves #456", re.IGNORECASE) is not None


def test_auto_close_pattern_not_match_related_to():
    """Test that 'Related to #N' does NOT match."""
    pattern = r"\b(closes|fixes|resolves)\s+#\d+"

    body = "This PR addresses an issue.\n\nRelated to #123"
    assert re.search(pattern, body, re.IGNORECASE) is None


def test_auto_close_pattern_not_match_references():
    """Test that 'References #N' does NOT match."""
    pattern = r"\b(closes|fixes|resolves)\s+#\d+"

    body = "References #123 for context"
    assert re.search(pattern, body, re.IGNORECASE) is None


def test_auto_close_pattern_not_match_see():
    """Test that 'See #N' does NOT match."""
    pattern = r"\b(closes|fixes|resolves)\s+#\d+"

    body = "See #123 for background"
    assert re.search(pattern, body, re.IGNORECASE) is None


def test_github_tools_validates_body(monkeypatch):
    """Test that github_open_pr validates the body."""
    # Import modules
    import pr_orchestrator.state as state_module
    from pr_orchestrator.tools.approval_tools import request_approval
    from pr_orchestrator.tools.github_tools import github_open_pr

    # Patch CONFIG to use test-user with wildcard allowlist
    mock_config = type('Config', (), {
        'github_token': 'test-token',
        'e2b_api_key': 'test-e2b-key',
        'github_username': 'test-user',
        'allowed_repos': ['*'],  # Allow all repos for this test
    })()
    monkeypatch.setattr(state_module, "CONFIG", mock_config)

    # Also patch in github_tools module
    import pr_orchestrator.tools.github_tools as github_tools_module
    monkeypatch.setattr(github_tools_module, "CONFIG", mock_config)

    # Get an approval
    approval = request_approval(
        summary="Test",
        unified_diff="diff",
        checks={},
        pr_draft=True,
        branch_plan={},
        approved=True,
    )
    approval_id = approval["approval_id"]

    # Test that body with auto-close keyword is rejected
    with pytest.raises(ValueError, match="auto-close keywords"):
        github_open_pr(
            upstream_repo_slug="owner/repo",
            base_branch="main",
            fork_repo_slug="test-user/repo",
            head_branch="fix/test",
            title="Test PR",
            body="This PR closes #123",
            draft=True,
            approval_id=approval_id,
        )


def test_github_tools_validates_fork_owner(monkeypatch):
    """Test that github_open_pr validates the fork owner."""
    import pr_orchestrator.state as state_module
    import pr_orchestrator.tools.github_tools as github_tools_module
    from pr_orchestrator.tools.approval_tools import request_approval
    from pr_orchestrator.tools.github_tools import github_open_pr

    # Patch CONFIG with wildcard allowlist
    mock_config = type('Config', (), {
        'github_token': 'test-token',
        'e2b_api_key': 'test-e2b-key',
        'github_username': 'test-user',
        'allowed_repos': ['*'],  # Allow all repos for this test
    })()
    monkeypatch.setattr(state_module, "CONFIG", mock_config)
    monkeypatch.setattr(github_tools_module, "CONFIG", mock_config)

    approval = request_approval(
        summary="Test",
        unified_diff="diff",
        checks={},
        pr_draft=True,
        branch_plan={},
        approved=True,
    )
    approval_id = approval["approval_id"]

    # Test that fork owner mismatch is rejected
    with pytest.raises(PermissionError, match="does not match"):
        github_open_pr(
            upstream_repo_slug="owner/repo",
            base_branch="main",
            fork_repo_slug="other-user/repo",  # Different user
            head_branch="fix/test",
            title="Test PR",
            body="Valid body without auto-close",
            draft=True,
            approval_id=approval_id,
        )
