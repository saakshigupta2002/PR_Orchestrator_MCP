"""Tests for GitHub PR head format."""

from __future__ import annotations


class TestPRHeadFormat:
    """Tests that PR head is correctly formatted as fork_owner:branch."""

    def test_head_format_uses_fork_owner(self, mocker) -> None:
        """PR head should be fork_owner:branch, not repo name."""
        # Mock the HTTP response
        mock_response = mocker.MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "html_url": "https://github.com/upstream/repo/pull/1",
            "number": 1,
        }

        # Create mock httpx client
        mock_client = mocker.MagicMock()
        mock_client.request.return_value = mock_response
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch(
            "pr_orchestrator.github.api.get_github_client",
            return_value=mock_client,
        )

        # Mock config
        mock_config = mocker.MagicMock()
        mock_config.github_token = "test-token"

        from pr_orchestrator.github.api import open_pr

        open_pr(
            config=mock_config,
            upstream_repo_slug="upstream-org/repo",
            base_branch="main",
            fork_repo_slug="my-username/repo",
            head_branch="feature-branch",
            title="Test PR",
            body="Test body",
            draft=True,
        )

        # Verify the request was made with correct head format
        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        json_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")

        # Head should be "my-username:feature-branch"
        assert json_payload["head"] == "my-username:feature-branch"
        assert json_payload["base"] == "main"

    def test_head_format_with_different_fork_owner(self, mocker) -> None:
        """Test with different fork owner name."""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "html_url": "https://github.com/org/repo/pull/42",
            "number": 42,
        }

        mock_client = mocker.MagicMock()
        mock_client.request.return_value = mock_response
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch(
            "pr_orchestrator.github.api.get_github_client",
            return_value=mock_client,
        )

        mock_config = mocker.MagicMock()
        mock_config.github_token = "test-token"

        from pr_orchestrator.github.api import open_pr

        open_pr(
            config=mock_config,
            upstream_repo_slug="organization/project",
            base_branch="develop",
            fork_repo_slug="saakshigupta2002/project",
            head_branch="fix/bug-123",
            title="Fix bug",
            body="Fixes the bug",
            draft=False,
        )

        call_kwargs = mock_client.request.call_args
        json_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")

        # Head should be "saakshigupta2002:fix/bug-123"
        assert json_payload["head"] == "saakshigupta2002:fix/bug-123"

    def test_fork_owner_extracted_correctly(self) -> None:
        """Test that fork owner is extracted correctly from slug."""
        # Test the extraction logic directly
        fork_repo_slug = "myuser/myrepo"
        fork_owner = fork_repo_slug.split("/", 1)[0]
        assert fork_owner == "myuser"

        # Edge case: org with dash
        fork_repo_slug = "my-org-name/my-repo-name"
        fork_owner = fork_repo_slug.split("/", 1)[0]
        assert fork_owner == "my-org-name"
