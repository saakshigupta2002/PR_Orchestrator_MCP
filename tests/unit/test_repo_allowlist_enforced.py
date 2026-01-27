"""Tests for repository allowlist enforcement across tools."""

from __future__ import annotations

import pytest

from pr_orchestrator.policy.allowlist import (
    fork_owner_allowed,
    is_repo_allowed,
    upstream_allowed,
)


class TestIsRepoAllowed:
    """Tests for the legacy is_repo_allowed function."""

    def test_allowed_with_wildcard(self) -> None:
        """Repo under owner with wildcard is allowed."""
        allowed = ["saakshigupta2002/*"]
        assert is_repo_allowed("saakshigupta2002/myrepo", allowed)

    def test_allowed_explicit_match(self) -> None:
        """Repo explicitly in allowlist is allowed."""
        allowed = ["saakshigupta2002/specific-repo"]
        assert is_repo_allowed("saakshigupta2002/specific-repo", allowed)

    def test_not_allowed_different_owner(self) -> None:
        """Repo under different owner is not allowed."""
        allowed = ["saakshigupta2002/*"]
        assert not is_repo_allowed("other-user/myrepo", allowed)

    def test_not_allowed_not_in_list(self) -> None:
        """Repo not in allowlist is not allowed."""
        allowed = ["saakshigupta2002/allowed-repo"]
        assert not is_repo_allowed("saakshigupta2002/other-repo", allowed)


class TestUpstreamAllowed:
    """Tests for upstream_allowed function."""

    def test_allowed_global_wildcard(self) -> None:
        """Any repo is allowed with global wildcard."""
        assert upstream_allowed("any-org/any-repo", ["*"])
        assert upstream_allowed("any-org/any-repo", ["*/*"])

    def test_allowed_owner_wildcard(self) -> None:
        """Repo under owner with wildcard is allowed."""
        allowed = ["myorg/*"]
        assert upstream_allowed("myorg/repo1", allowed)
        assert upstream_allowed("myorg/repo2", allowed)

    def test_allowed_explicit_match(self) -> None:
        """Explicitly listed repo is allowed."""
        allowed = ["specific-org/specific-repo"]
        assert upstream_allowed("specific-org/specific-repo", allowed)

    def test_not_allowed_different_owner(self) -> None:
        """Repo under non-allowed owner is rejected."""
        allowed = ["allowed-org/*"]
        assert not upstream_allowed("other-org/repo", allowed)

    def test_case_insensitive(self) -> None:
        """Matching is case-insensitive."""
        allowed = ["MyOrg/MyRepo"]
        assert upstream_allowed("myorg/myrepo", allowed)


class TestForkOwnerAllowed:
    """Tests for fork_owner_allowed function."""

    def test_fork_allowed_under_username(self) -> None:
        """Fork under the correct username is allowed."""
        allowed = ["upstream-org/repo"]
        assert fork_owner_allowed("myuser/repo", "myuser", allowed)

    def test_fork_not_allowed_wrong_username(self) -> None:
        """Fork under wrong username is rejected."""
        allowed = ["upstream-org/repo"]
        assert not fork_owner_allowed("other-user/repo", "myuser", allowed)

    def test_fork_allowed_with_global_wildcard(self) -> None:
        """Fork is allowed with global wildcard."""
        allowed = ["*"]
        assert fork_owner_allowed("myuser/any-repo", "myuser", allowed)


class TestAllowlistEnforcementInTools:
    """Tests that tools properly enforce the allowlist."""

    def test_github_get_issue_rejects_unallowed_repo(self, mocker) -> None:
        """github_get_issue rejects repos not in allowlist."""
        # Mock CONFIG to have restricted allowlist
        mock_config = mocker.MagicMock()
        mock_config.allowed_repos = ["saakshigupta2002/*"]
        mocker.patch("pr_orchestrator.tools.github_tools.CONFIG", mock_config)

        from pr_orchestrator.tools.github_tools import github_get_issue

        with pytest.raises(PermissionError, match="not in the allowlist"):
            github_get_issue("unallowed-org/repo", 123)

    def test_github_find_prs_rejects_unallowed_repo(self, mocker) -> None:
        """github_find_prs_for_issue rejects repos not in allowlist."""
        mock_config = mocker.MagicMock()
        mock_config.allowed_repos = ["saakshigupta2002/*"]
        mocker.patch("pr_orchestrator.tools.github_tools.CONFIG", mock_config)

        from pr_orchestrator.tools.github_tools import github_find_prs_for_issue

        with pytest.raises(PermissionError, match="not in the allowlist"):
            github_find_prs_for_issue("unallowed-org/repo", 123)

    def test_github_open_pr_rejects_unallowed_upstream(self, mocker) -> None:
        """github_open_pr rejects unallowed upstream repos.
        
        The allowlist check happens BEFORE approval check, so we don't need to
        mock approval consumption for this test.
        """
        mock_config = mocker.MagicMock()
        mock_config.allowed_repos = ["saakshigupta2002/*"]
        mock_config.github_username = "saakshigupta2002"
        mocker.patch("pr_orchestrator.tools.github_tools.CONFIG", mock_config)

        from pr_orchestrator.tools.github_tools import github_open_pr

        with pytest.raises(PermissionError, match="not in the allowlist"):
            github_open_pr(
                upstream_repo_slug="unallowed-org/repo",
                base_branch="main",
                fork_repo_slug="saakshigupta2002/repo",
                head_branch="feature",
                title="Test PR",
                body="Test body",
                approval_id="test-approval",
            )
