"""E2B code mode workspace implementation.

This module provisions an isolated workspace via the E2B Sandbox API.
The E2B_API_KEY environment variable MUST be set - there is no local fallback.

Per spec: All code runs inside E2B sandbox. No local execution is allowed
in production.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from ..config import Config


@dataclass
class E2BCodeWorkspace:
    """Representation of a code mode workspace backed by E2B Sandbox.

    This class uses the E2B SDK to provision a remote code sandbox.
    The E2B_API_KEY MUST be configured in the environment.
    
    There is NO local fallback - E2B sandbox is required for all execution.
    """

    mode: str = "code"
    ttl_minutes: int = 60
    created_at: float = field(default_factory=time.time)

    # Backend used to run commands, read and write files.
    backend: object | None = field(init=False, default=None)

    # Internal reference to the E2B sandbox instance
    _sandbox: object | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        from .backend import E2BBackend

        api_key = os.environ.get("E2B_API_KEY")
        # NOTE: Older versions of the E2B SDK accepted a ``template`` argument
        # and explicit ``timeout`` value when constructing ``Sandbox``.
        # The current SDK (used in this project) exposes a generic
        # ``Sandbox(**SandboxOpts)`` interface which no longer supports those
        # parameters directly.  TTL is enforced at the PR Orchestrator layer
        # (see ``WorkspaceStore``), so we simply create a default sandbox here.

        if not api_key:
            raise RuntimeError(
                "E2B_API_KEY environment variable is required. "
                "The PR Orchestrator requires E2B sandbox for safe execution. "
                "No local fallback is available."
            )

        # Create E2B sandbox
        try:
            from e2b import Sandbox

            # Create sandbox with timeout based on TTL (in seconds)
            timeout_seconds = self.ttl_minutes * 60
            e2b_template = os.environ.get("E2B_TEMPLATE")  # None = use default

            # Use Sandbox.create() class method with optional template/timeout
            self._sandbox = Sandbox.create(
                template=e2b_template,
                timeout=timeout_seconds,
            )

            # Create backend using E2B
            cfg = Config.load_from_env()
            self.backend = E2BBackend(self._sandbox, cfg)

            # Write the git-askpass script to the sandbox
            self._write_askpass_script()

        except ImportError as exc:
            raise RuntimeError(
                f"E2B SDK is not installed: {exc}. "
                "Install with: pip install e2b"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to create E2B sandbox: {exc}. "
                "Check your E2B_API_KEY and network connectivity."
            ) from exc

    def _write_askpass_script(self) -> None:
        """Write the git-askpass script to the E2B sandbox."""
        if self._sandbox is None:
            return

        script_contents = (
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "  *Username*) echo \"x-access-token\" ;;\n"
            "  *) echo \"$GITHUB_TOKEN\" ;;\n"
            "esac\n"
        )

        try:
            self._sandbox.files.write("/home/user/git-askpass.sh", script_contents)
            # Make executable
            self._sandbox.commands.run("chmod +x /home/user/git-askpass.sh")
        except Exception:
            # Non-fatal if creation fails
            pass

    def destroy(self) -> None:
        """Kill the E2B sandbox."""
        if self._sandbox is not None:
            try:
                self._sandbox.kill()
            except Exception:
                pass
            self._sandbox = None

        if self.backend is not None:
            try:
                if hasattr(self.backend, 'destroy'):
                    self.backend.destroy()
            except Exception:
                pass
            self.backend = None

    def expired(self) -> bool:
        """Return True if the workspace TTL has elapsed."""
        return (time.time() - self.created_at) > self.ttl_minutes * 60
