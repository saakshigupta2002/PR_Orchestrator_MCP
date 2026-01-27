"""Secret redaction utilities.

This module removes occurrences of secrets from text before logs, diffs
or commit messages are persisted.  Redaction is a simple string replacement
that substitutes secrets with the string ``"<REDACTED>"``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_TOKEN_PATTERNS = [
    # GitHub personal access tokens: ghp_xxx or github_pat_xxx
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}", re.IGNORECASE),
    # OpenAI and other API keys (e.g., sk-...)
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
    # AWS access keys (e.g., AKIA... or ASIA... 20 chars)
    re.compile(r"A(KIA|SIA)[A-Z0-9]{16}", re.IGNORECASE),
    # AWS secret keys (40 base64-like chars)
    re.compile(r"[A-Za-z0-9/+=]{40}", re.IGNORECASE),
    # Bearer tokens (JWT or opaque strings following 'Bearer ')
    re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+/]+=*", re.IGNORECASE),
    # Generic long hex/base64 strings (32+ chars)
    re.compile(r"[A-Za-z0-9_-]{32,}", re.IGNORECASE),
    # Private key blocks (BEGIN/END markers)
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----", re.IGNORECASE),
]


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Return ``text`` with secrets and common token patterns replaced.

    The function replaces any explicit secret strings provided in ``secrets``
    as well as matches to a set of regular expression patterns corresponding
    to common credentials (GitHub tokens, API keys, generic long tokens) with
    the placeholder ``<REDACTED>``.

    :param text: arbitrary text that may contain secrets
    :param secrets: iterable of secret strings to redact
    :return: redacted text
    """
    redacted = text or ""
    # Replace explicit secrets
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "<REDACTED>")
    # Replace pattern matches
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub("<REDACTED>", redacted)
    return redacted
