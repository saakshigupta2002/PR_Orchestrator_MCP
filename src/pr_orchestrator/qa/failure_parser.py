"""Failure log parser for test runs."""

from __future__ import annotations

import re


def parse_failing_tests(logs: str) -> list[str]:
    """Extract failing test names from pytest output.

    Searches the logs for lines that indicate test failures.  Pytest reports
    failing tests with a ``::`` delimiter, e.g. ``tests/test_example.py::test_foo
    FAILED``.  Returns a list of ``file::test`` identifiers.  If no failures
    are detected, an empty list is returned.
    """
    if not logs:
        return []
    failing: list[str] = []
    pattern = re.compile(r"^(.*?)::(.*?)\s+FAILED", re.MULTILINE)
    for match in pattern.finditer(logs):
        file_part, test_name = match.groups()
        identifier = f"{file_part}::{test_name}"
        if identifier not in failing:
            failing.append(identifier)
    return failing
