"""Bundle artifacts into a zip archive."""

from __future__ import annotations

import json
import logging
import tempfile
import zipfile
from pathlib import Path

from ..policy.redaction import redact_secrets

logger = logging.getLogger(__name__)


def bundle_artifacts(
    diff_text: str,
    metadata: dict[str, object],
    before_failures: dict[str, object],
    after_failures: dict[str, object],
    logs: dict[str, str],
    secrets: list[str],
) -> Path:
    """Create a zip archive of redacted artifacts and return its path.

    All textual content in the archive is passed through ``redact_secrets``
    to scrub sensitive information.  The metadata and failure objects are
    serialized to JSON prior to redaction.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="mcp_artifacts_"))
    archive_path = tmpdir / "artifacts.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("diff.patch", redact_secrets(diff_text, secrets))
        # Serialize and redact metadata and failure objects
        meta_str = json.dumps(metadata)
        before_str = json.dumps(before_failures)
        after_str = json.dumps(after_failures)
        zf.writestr("metadata.json", redact_secrets(meta_str, secrets))
        zf.writestr("before_failures.json", redact_secrets(before_str, secrets))
        zf.writestr("after_failures.json", redact_secrets(after_str, secrets))
        for name, log in logs.items():
            zf.writestr(f"logs/{name}.txt", redact_secrets(log, secrets))
    logger.debug("Created artifact bundle at %s", archive_path)
    return archive_path
