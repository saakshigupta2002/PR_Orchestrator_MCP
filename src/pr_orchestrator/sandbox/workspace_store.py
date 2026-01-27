"""Workspace store for managing active workspaces."""

from __future__ import annotations

import logging
import posixpath
import uuid
from dataclasses import dataclass

from ..config import Config
from ..policy.redaction import redact_secrets
from .e2b_code import E2BCodeWorkspace

logger = logging.getLogger(__name__)

# Internal git subcommands allowed for repo tools
# These bypass the run_command allowlist but are still restricted to safe git operations
INTERNAL_GIT_SUBCMDS = {
    "clone",
    "remote",
    "rev-parse",
    "symbolic-ref",
    "checkout",
    "branch",
    "fetch",
    "log",
    "diff",
    "status",
    "add",
    "commit",
    "show",
}


def _validate_pip_uv_command(tokens: list[str], mode: str) -> None:
    """Validate pip/uv install commands for safe mode restrictions.
    
    In safe mode, only allow:
    - uv sync [--dev]
    - pip install -r <file>
    - pip install . / pip install -e .
    - pip install <package-name> (simple package names only)
    
    Block:
    - Direct URL installs: pip install https://...
    - Custom index URLs: --index-url, --extra-index-url
    - Trusted hosts: --trusted-host
    - Git installs: git+https://... (unless expert mode)
    
    Raises PermissionError if command violates safe mode restrictions.
    """
    if not tokens:
        return

    first = tokens[0]

    # Only check pip and uv commands
    is_pip = first == "pip" or (first == "python" and "-m" in tokens and "pip" in tokens)
    is_uv = first == "uv"

    if not is_pip and not is_uv:
        return

    # In expert mode, allow more flexibility (but still block truly dangerous patterns)
    if mode == "expert":
        # Even in expert mode, block certain dangerous patterns
        dangerous_patterns = ["--trusted-host"]
        for tok in tokens:
            for pattern in dangerous_patterns:
                if tok.startswith(pattern):
                    raise PermissionError(f"'{pattern}' is not allowed even in expert mode")
        return

    # Safe mode restrictions
    # Block dangerous flags
    blocked_flags = [
        "--index-url",
        "--extra-index-url",
        "-i",  # short for --index-url
        "--trusted-host",
        "--find-links",
        "-f",  # short for --find-links
    ]

    for tok in tokens:
        # Check for blocked flags
        for flag in blocked_flags:
            if tok == flag or tok.startswith(f"{flag}="):
                raise PermissionError(
                    f"'{flag}' is not allowed in safe mode. "
                    "Only standard PyPI installs are permitted."
                )

        # Block direct URL installs
        if tok.startswith("http://") or tok.startswith("https://"):
            raise PermissionError(
                "Direct URL package installs are not allowed in safe mode. "
                "Use package names from PyPI instead."
            )

        # Block git+ installs
        if tok.startswith("git+"):
            raise PermissionError(
                "Git-based package installs (git+https://...) are not allowed in safe mode. "
                "Use package names from PyPI instead."
            )


def normalize_repo_cwd(cwd: str | None) -> str:
    """Normalize and validate cwd to ensure it's within repo/.
    
    This uses pure string operations - no host filesystem access.
    
    Args:
        cwd: The working directory path (relative)
        
    Returns:
        Normalized path within repo/
        
    Raises:
        PermissionError: If cwd escapes repo/ or is invalid
    """
    # Default to repo root
    if not cwd:
        cwd = "repo"

    # Reject absolute paths
    if cwd.startswith("/") or cwd.startswith("~"):
        raise PermissionError("cwd must be relative and within repo/")

    # Normalize the path
    norm = posixpath.normpath(cwd)

    # Handle "." as repo
    if norm == ".":
        norm = "repo"

    # Ensure path is within repo/
    if not (norm == "repo" or norm.startswith("repo/")):
        raise PermissionError(f"cwd '{cwd}' must be within repo/")

    # Prevent directory traversal escapes
    if "/.." in ("/" + norm) or norm.startswith(".."):
        raise PermissionError(f"cwd '{cwd}' escapes repo/")

    return norm


@dataclass
class Workspace:
    """Represent an active workspace.

    A workspace encapsulates a sandboxed environment (remote via E2B)
    along with a backend used to execute commands and perform filesystem
    operations.  The backend is optional at construction time and will be
    populated when the workspace is created in ``WorkspaceStore.create``.
    """

    id: str
    impl: E2BCodeWorkspace
    # Backend for running commands and file operations.  Populated from the
    # workspace implementation.  See ``sandbox.backend`` for details.
    backend: object | None = None


class WorkspaceStore:
    """Registry for tracking workspaces and running commands within them."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._store: dict[str, Workspace] = {}
        # Single run lock (v1 requirement - one run at a time)
        self._run_active: bool = False

    def create(self, mode: str = "code", ttl_minutes: int = 60) -> Workspace:
        """Create a new workspace and register it.

        The workspace type is determined by ``mode``:

        - ``code``: creates a code-mode E2B workspace (via ``E2BCodeWorkspace``)
        - ``desktop``: not supported in v1; raises NotImplementedError

        The TTL is clamped to the maximum allowed value from configuration.
        """
        # Clamp TTL to within [1, RUN_TTL_MAX_MINUTES]
        from ..constants import RUN_TTL_MAX_MINUTES
        ttl_minutes = max(1, min(ttl_minutes, RUN_TTL_MAX_MINUTES))

        # Instantiate the appropriate workspace implementation
        if mode == "code":
            impl = E2BCodeWorkspace(mode=mode, ttl_minutes=ttl_minutes)
        elif mode == "desktop":
            # Desktop workspaces are not supported in v1
            from .e2b_desktop import E2BDesktopWorkspace
            impl = E2BDesktopWorkspace(ttl_minutes=ttl_minutes)
        else:
            raise NotImplementedError(f"Unsupported workspace mode: {mode}")

        ws_id = str(uuid.uuid4())
        workspace = Workspace(id=ws_id, impl=impl)

        # Attach the backend from the workspace implementation
        try:
            workspace.backend = impl.backend
        except Exception:
            workspace.backend = None

        self._store[ws_id] = workspace

        # Write git-askpass script to sandbox via backend
        self._write_askpass_script(workspace)

        return workspace

    def _write_askpass_script(self, workspace: Workspace) -> None:
        """Write git-askpass script to the sandbox via backend."""
        if workspace.backend is None:
            return

        script_contents = (
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "  *Username*) echo \"x-access-token\" ;;\n"
            "  *) echo \"$GITHUB_TOKEN\" ;;\n"
            "esac\n"
        )

        try:
            workspace.backend.write_text("git-askpass.sh", script_contents)
            # Make executable via command
            workspace.backend.run(["chmod", "+x", "git-askpass.sh"], ".", 10)
        except Exception:
            # Non-fatal if creation fails
            pass

    def destroy(self, workspace_id: str) -> bool:
        """Destroy a workspace by ID."""
        ws = self._store.pop(workspace_id, None)
        if not ws:
            return False
        ws.impl.destroy()
        return True

    def get(self, workspace_id: str) -> Workspace:
        """Retrieve a workspace or raise KeyError.

        If the workspace has expired based on its TTL, it is destroyed and
        a ``KeyError`` is raised with a clear message.
        """
        if workspace_id not in self._store:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        ws = self._store[workspace_id]
        # TTL enforcement
        if ws.impl.expired():
            # Remove and destroy expired workspace
            self.destroy(workspace_id)
            raise KeyError(
                f"Workspace '{workspace_id}' has expired. "
                "Create a new workspace with workspace_create."
            )
        return ws

    def run_command(
        self,
        workspace_id: str,
        command: str,
        cwd: str = "repo",
        timeout_s: int = 300,
        mode: str = "safe",
    ) -> dict[str, object]:
        """Execute a command inside the workspace.

        Commands are run with strict validation to prevent shell injection and
        enforce repository isolation.  The first token of the command must
        match an allowlisted prefix according to ``mode``.  Metacharacters
        commonly used for chaining commands are rejected.  Execution uses
        ``shell=False`` and passes arguments as a list.  The current working
        directory must be within the ``repo`` directory.  Concurrency is
        limited to one active run at a time.
        """
        import shlex

        workspace = self.get(workspace_id)

        # Validate mode
        if mode not in {"safe", "expert"}:
            raise ValueError("mode must be 'safe' or 'expert'")

        # Build allowlists
        safe_prefixes = (
            "git",  # git operations
            "python",  # python commands and modules
            "pytest",  # pytest
            "ruff",  # lint/format
            "mypy",  # type check
            "uv",  # uv commands
            "pip",  # pip install
        )
        expert_prefixes = safe_prefixes + (
            "pre-commit",
            # Additional expert tools can be added here
        )
        prefixes = safe_prefixes if mode == "safe" else expert_prefixes

        # Parse the command into tokens
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise PermissionError(f"Failed to parse command '{command}': {exc}") from exc

        if not tokens:
            raise PermissionError("Empty command is not allowed")

        first = tokens[0]
        if not any(first.startswith(prefix) for prefix in prefixes):
            raise PermissionError(f"Command '{command}' is not allowed in {mode} mode")

        # Reject metacharacters that could lead to injection
        forbidden_chars = [";", "&&", "||", "|", "`", "$(", ">", "<"]
        for frag in forbidden_chars:
            if frag in command:
                raise PermissionError(f"Command '{command}' contains forbidden sequence '{frag}'")

        # Additional forbidden substrings
        forbidden_substrings = ["sudo", "rm -rf", "curl", "bash", "wget", "ssh"]
        for forbidden in forbidden_substrings:
            if forbidden in command:
                raise PermissionError(f"Command '{command}' contains forbidden substring '{forbidden}'")

        # Validate pip/uv commands for safe mode restrictions
        _validate_pip_uv_command(tokens, mode)

        # Block disallowed git subcommands
        if first == "git" and len(tokens) >= 2:
            subcmd = tokens[1]
            subcmd_lower = subcmd.lower()

            # Disallow dangerous subcommands regardless of mode
            if subcmd_lower == "push":
                raise PermissionError("Direct 'git push' is not permitted; use repo_push tool with approval")
            if subcmd_lower == "apply":
                raise PermissionError("Direct 'git apply' is not permitted; use apply_patch tool")
            if subcmd_lower == "clone":
                raise PermissionError("Direct 'git clone' is not permitted; use repo_clone tool")
            if subcmd_lower == "remote" and len(tokens) >= 3:
                if tokens[2].lower() in {"set-url"}:
                    raise PermissionError("Changing remote URLs is not permitted via run_command")
            if subcmd_lower in {"config", "reset", "clean"}:
                raise PermissionError(f"git {subcmd_lower} is not permitted via run_command")

            # Safe-mode allowlist for git subcommands via run_command (per spec).
            # The spec allows: status, diff, checkout, branch, commit, push, log, fetch
            #
            # NOTE: 'push' is NOT in this set because it's handled specially above:
            # - Direct 'git push' via run_command is BLOCKED (line ~339)
            # - Push is only allowed through the approval-gated repo_push() tool
            # This ensures the approval gate cannot be bypassed.
            allowed_git_safe_run_command = {
                "status",
                "diff",
                "checkout",
                "branch",
                "commit",
                "log",
                "fetch",
            }
            if mode == "safe" and subcmd_lower not in allowed_git_safe_run_command:
                raise PermissionError(f"git {subcmd_lower} is not allowed in safe mode")

        # Validate and normalize cwd (pure string validation, no host filesystem)
        norm_cwd = normalize_repo_cwd(cwd)

        # Enforce single active run
        if self._run_active:
            raise RuntimeError("Another command is currently running; only one run is allowed at a time")
        self._run_active = True

        try:
            if getattr(workspace, "backend", None) is None:
                raise RuntimeError("Workspace backend is not configured")
            result = workspace.backend.run(tokens, norm_cwd, timeout_s)
        finally:
            self._run_active = False

        # Redact secrets from output
        secrets = [self.config.github_token, self.config.e2b_api_key]
        stdout = redact_secrets(str(result.get("stdout", "")), secrets)
        stderr = redact_secrets(str(result.get("stderr", "")), secrets)

        return {
            "run_id": str(uuid.uuid4()),
            "exit_code": int(result.get("exit_code", 1)),
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": int(result.get("duration_ms", 0)),
            "timed_out": bool(result.get("timed_out", False)),
        }

    def run_internal_git(
        self,
        workspace_id: str,
        argv: list[str],
        *,
        cwd: str | None = None,
        timeout_s: int = 600,
    ) -> dict[str, object]:
        """Run an internal git command for repo tools.

        This bypasses the run_command git subcommand allowlist but still
        enforces that:
        - argv[0] must be 'git'
        - argv[1] must be in INTERNAL_GIT_SUBCMDS
        - cwd must be within the workspace
        - No shell metacharacters are allowed
        - Secret redaction is applied

        This is used by repo_clone, repo_setup_remotes, and other internal
        git operations.
        """
        workspace = self.get(workspace_id)

        # Validate argv structure
        if not argv or len(argv) < 2:
            raise PermissionError("Internal git commands require at least 'git <subcommand>'")

        if argv[0] != "git":
            raise PermissionError("Internal git runner only accepts git commands")

        subcmd = argv[1].lower()
        if subcmd not in INTERNAL_GIT_SUBCMDS:
            raise PermissionError(f"git {subcmd} is not allowed via internal git runner")

        # Check for forbidden patterns in arguments
        forbidden_chars = [";", "&&", "||", "|", "`", "$(", ">", "<"]
        for arg in argv:
            for frag in forbidden_chars:
                if frag in arg:
                    raise PermissionError(f"Argument contains forbidden sequence '{frag}'")

        # Normalize cwd - allow workspace root for initial clone, otherwise repo/
        if cwd is None or cwd == "" or cwd == ".":
            cwd = "repo"

        # For clone operation, we may need to run from workspace root
        if subcmd == "clone":
            # Clone runs from workspace root, cloning into repo/
            norm_cwd = "."
        else:
            norm_cwd = normalize_repo_cwd(cwd)

        # Execute via backend
        if getattr(workspace, "backend", None) is None:
            raise RuntimeError("Workspace backend is not configured")

        result = workspace.backend.run(argv, norm_cwd, timeout_s)

        # Redact secrets
        secrets = [self.config.github_token, self.config.e2b_api_key]
        stdout = redact_secrets(str(result.get("stdout", "")), secrets)
        stderr = redact_secrets(str(result.get("stderr", "")), secrets)

        return {
            "run_id": str(uuid.uuid4()),
            "exit_code": int(result.get("exit_code", 1)),
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": int(result.get("duration_ms", 0)),
            "timed_out": bool(result.get("timed_out", False)),
        }

    def run_git_push(
        self,
        workspace_id: str,
        remote: str,
        refspec: str,
        timeout_s: int = 300,
    ) -> dict[str, object]:
        """Push a refspec to a remote.

        This bypasses the run_command git subcommand allowlist but still
        enforces repo isolation, environment setup and secret redaction.
        """
        workspace = self.get(workspace_id)
        argv = ["git", "push", remote, refspec]

        if getattr(workspace, "backend", None) is None:
            raise RuntimeError("Workspace backend is not configured")

        result = workspace.backend.run(argv, "repo", timeout_s)

        # Redact secrets
        secrets = [self.config.github_token, self.config.e2b_api_key]
        return {
            "run_id": str(uuid.uuid4()),
            "exit_code": int(result.get("exit_code", 1)),
            "stdout": redact_secrets(str(result.get("stdout", "")), secrets),
            "stderr": redact_secrets(str(result.get("stderr", "")), secrets),
            "duration_ms": int(result.get("duration_ms", 0)),
            "timed_out": bool(result.get("timed_out", False)),
        }

    def run_git_apply(
        self,
        workspace_id: str,
        patch_path: str,
        timeout_s: int = 300,
    ) -> dict[str, object]:
        """Apply a patch file using git apply.

        The patch_path should be relative to repo/ (e.g., ".pr_orchestrator/tmp.patch").
        """
        workspace = self.get(workspace_id)
        argv = ["git", "apply", "--whitespace=nowarn", patch_path]

        if getattr(workspace, "backend", None) is None:
            raise RuntimeError("Workspace backend is not configured")

        result = workspace.backend.run(argv, "repo", timeout_s)

        secrets = [self.config.github_token, self.config.e2b_api_key]
        return {
            "run_id": str(uuid.uuid4()),
            "exit_code": int(result.get("exit_code", 1)),
            "stdout": redact_secrets(str(result.get("stdout", "")), secrets),
            "stderr": redact_secrets(str(result.get("stderr", "")), secrets),
            "duration_ms": int(result.get("duration_ms", 0)),
            "timed_out": bool(result.get("timed_out", False)),
        }
