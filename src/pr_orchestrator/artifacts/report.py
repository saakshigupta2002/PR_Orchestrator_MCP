"""Generate a human‑readable report from run results."""

from __future__ import annotations


def generate_report(before_failures: dict[str, object], after_failures: dict[str, object]) -> str:
    """Generate a simple report summarising test results before and after."""
    report_lines = []
    report_lines.append("### Before Failures\n")
    report_lines.append(str(before_failures) + "\n\n")
    report_lines.append("### After Failures\n")
    report_lines.append(str(after_failures) + "\n")
    return "".join(report_lines)
