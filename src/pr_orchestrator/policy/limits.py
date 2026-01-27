"""Limit enforcement for diff and patch operations."""

from __future__ import annotations

from collections.abc import Iterable

from ..constants import MAX_CHANGED_FILES, MAX_PATCH_LINES


def enforce_patch_limits(files_modified: Iterable[str], diff_lines: int) -> None:
    """Ensure that the patch does not exceed configured limits.

    :param files_modified: names of files modified by the patch
    :param diff_lines: total number of added and removed lines
    :raises ValueError: if the patch exceeds configured limits
    """
    file_count = len(list(files_modified))
    if file_count > MAX_CHANGED_FILES:
        raise ValueError(
            f"Patch modifies {file_count} files which exceeds the limit of {MAX_CHANGED_FILES}"
        )
    if diff_lines > MAX_PATCH_LINES:
        raise ValueError(
            f"Patch has {diff_lines} lines which exceeds the limit of {MAX_PATCH_LINES}"
        )
