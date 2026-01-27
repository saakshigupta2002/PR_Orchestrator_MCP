"""Mocked integration tests for github_ensure_fork functionality."""

from __future__ import annotations

import pytest


class TestGithubEnsureForkMocked:
    """Integration tests for github_ensure_fork with mocked GitHub API."""

    def test_ensure_fork_creates_fork_if_missing(self, mocker) -> None:
        """Test that ensure_fork creates a fork if it doesn't exist."""
        # Mock CONFIG
        mock_config = mocker.MagicMock()
        mock_config.github_token = "test-token"
        mock_config.github_username = "testuser"
        mock_config.allowed_repos = ["*"]
        mocker.patch("pr_orchestrator.tools.repo_tools.CONFIG", mock_config)

        # First GET returns 404 (fork doesn't exist)
        # POST creates fork (returns 202)
        # Second GET returns 200 (fork now exists)
        mock_get_response_404 = mocker.MagicMock()
        mock_get_response_404.status_code = 404

        mock_post_response = mocker.MagicMock()
        mock_post_response.status_code = 202

        mock_get_response_200 = mocker.MagicMock()
        mock_get_response_200.status_code = 200

        # Create a mock httpx.Client that returns these responses
        mock_client = mocker.MagicMock()
        mock_client.get.side_effect = [mock_get_response_404, mock_get_response_200]
        mock_client.post.return_value = mock_post_response
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch("httpx.Client", return_value=mock_client)

        from pr_orchestrator.tools.repo_tools import ensure_fork

        result = ensure_fork("upstream-org/repo")

        assert result["fork_slug"] == "testuser/repo"
        assert result["fork_url"] == "https://github.com/testuser/repo.git"
        assert result["created"] is True

        # Verify POST was called to create fork
        mock_client.post.assert_called_once()

    def test_ensure_fork_returns_existing_fork(self, mocker) -> None:
        """Test that ensure_fork returns existing fork without creating."""
        mock_config = mocker.MagicMock()
        mock_config.github_token = "test-token"
        mock_config.github_username = "testuser"
        mock_config.allowed_repos = ["*"]
        mocker.patch("pr_orchestrator.tools.repo_tools.CONFIG", mock_config)

        # GET returns 200 (fork already exists)
        mock_get_response = mocker.MagicMock()
        mock_get_response.status_code = 200

        mock_client = mocker.MagicMock()
        mock_client.get.return_value = mock_get_response
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch("httpx.Client", return_value=mock_client)

        from pr_orchestrator.tools.repo_tools import ensure_fork

        result = ensure_fork("upstream-org/repo")

        assert result["fork_slug"] == "testuser/repo"
        assert result["created"] is False

        # Verify POST was NOT called
        mock_client.post.assert_not_called()

    def test_ensure_fork_rejects_unallowed_upstream(self, mocker) -> None:
        """Test that ensure_fork rejects repos not in allowlist."""
        mock_config = mocker.MagicMock()
        mock_config.github_token = "test-token"
        mock_config.github_username = "testuser"
        mock_config.allowed_repos = ["allowed-org/*"]  # Only allow specific org
        mocker.patch("pr_orchestrator.tools.repo_tools.CONFIG", mock_config)

        from pr_orchestrator.tools.repo_tools import ensure_fork

        with pytest.raises(PermissionError, match="not in the allowlist"):
            ensure_fork("unallowed-org/repo")

    def test_github_ensure_fork_tool_wrapper(self, mocker) -> None:
        """Test the github_ensure_fork MCP tool wrapper."""
        mock_config = mocker.MagicMock()
        mock_config.github_token = "test-token"
        mock_config.github_username = "testuser"
        mock_config.allowed_repos = ["*"]
        mocker.patch("pr_orchestrator.tools.repo_tools.CONFIG", mock_config)
        mocker.patch("pr_orchestrator.tools.github_tools.CONFIG", mock_config)

        mock_get_response = mocker.MagicMock()
        mock_get_response.status_code = 200

        mock_client = mocker.MagicMock()
        mock_client.get.return_value = mock_get_response
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch("httpx.Client", return_value=mock_client)

        from pr_orchestrator.tools.github_tools import github_ensure_fork

        result = github_ensure_fork("upstream-org/repo")

        assert result["fork_repo_slug"] == "testuser/repo"
        assert result["fork_clone_url"] == "https://github.com/testuser/repo.git"
        assert result["upstream_clone_url"] == "https://github.com/upstream-org/repo.git"

    def test_ensure_fork_handles_api_error(self, mocker) -> None:
        """Test that ensure_fork handles API errors gracefully."""
        mock_config = mocker.MagicMock()
        mock_config.github_token = "test-token"
        mock_config.github_username = "testuser"
        mock_config.allowed_repos = ["*"]
        mocker.patch("pr_orchestrator.tools.repo_tools.CONFIG", mock_config)

        # GET returns 500 (server error)
        mock_get_response = mocker.MagicMock()
        mock_get_response.status_code = 500
        mock_get_response.text = "Internal Server Error"

        mock_client = mocker.MagicMock()
        mock_client.get.return_value = mock_get_response
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch("httpx.Client", return_value=mock_client)

        from pr_orchestrator.tools.repo_tools import ensure_fork

        with pytest.raises(RuntimeError, match="Unexpected status"):
            ensure_fork("upstream-org/repo")
