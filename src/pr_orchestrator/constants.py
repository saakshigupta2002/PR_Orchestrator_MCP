"""Global constants for PR Orchestrator MCP.

These values mirror the specification and serve as defaults for configuration and
limit enforcement.  Changing these values is discouraged; instead override
environment variables as needed.
"""

import os

# Default commands
DEFAULT_TEST_COMMAND = os.environ.get("DEFAULT_TEST_COMMAND", "pytest -q")
DEFAULT_LINT_COMMAND = os.environ.get("DEFAULT_LINT_COMMAND", "ruff check .")
DEFAULT_TYPECHECK_COMMAND = os.environ.get("DEFAULT_TYPECHECK_COMMAND", "mypy .")
DEFAULT_FORMAT_COMMAND = os.environ.get("DEFAULT_FORMAT_COMMAND", "ruff format .")

# Limits
COMMAND_TIMEOUT_S = int(os.environ.get("COMMAND_TIMEOUT_S", 300))
RUN_TTL_MINUTES = int(os.environ.get("RUN_TTL_MINUTES", 60))
RUN_TTL_MAX_MINUTES = int(os.environ.get("RUN_TTL_MAX_MINUTES", 360))
MAX_CHANGED_FILES = int(os.environ.get("MAX_CHANGED_FILES", 50))
MAX_PATCH_LINES = int(os.environ.get("MAX_PATCH_LINES", 5000))
FIX_LOOP_MAX_ITERS = int(os.environ.get("FIX_LOOP_MAX_ITERS", 5))
RETRY_COUNT = int(os.environ.get("RETRY_COUNT", 1))

# Transport
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")

# Logging
DEFAULT_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
