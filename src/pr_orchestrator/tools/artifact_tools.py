"""Artifact tool wrappers.

This module exposes a simple wrapper around the artifact bundler so that
clients can request a redacted bundle of their run artifacts.  The bundler
takes care to redact secrets from all included files.

S3: The bundle_artifacts_tool now returns base64-encoded zip bytes so that
clients can retrieve the artifact bundle directly through the MCP protocol.
"""

from __future__ import annotations

import base64
from pathlib import Path

from ..artifacts.bundler import bundle_artifacts


def bundle_artifacts_tool(
    diff_text: str,
    metadata: dict[str, object],
    before_failures: dict[str, object],
    after_failures: dict[str, object],
    logs: dict[str, str],
    secrets: list[str],
) -> dict[str, object]:
    """Bundle artifacts into a redacted zip and return it as base64.

    The caller must provide the diff text, metadata dictionary, before and
    after failure structures, and any logs to include.  A list of secrets
    should be supplied to aid in redaction.
    
    S3: Returns the zip archive as base64-encoded bytes so the client can
    retrieve it directly via the MCP protocol without needing filesystem
    access to the server.
    
    Returns:
        A dictionary containing:
        - artifact_path: Local filesystem path to the zip (for debugging)
        - zip_filename: The filename of the zip archive
        - zip_base64: Base64-encoded contents of the zip file
        - size_bytes: Size of the zip file in bytes
    """
    path: Path = bundle_artifacts(
        diff_text=diff_text,
        metadata=metadata,
        before_failures=before_failures,
        after_failures=after_failures,
        logs=logs,
        secrets=secrets,
    )

    # Read the zip file and encode as base64
    with open(path, "rb") as f:
        zip_bytes = f.read()

    zip_base64 = base64.b64encode(zip_bytes).decode("ascii")

    return {
        "artifact_path": str(path),
        "zip_filename": path.name,
        "zip_base64": zip_base64,
        "size_bytes": len(zip_bytes),
    }
