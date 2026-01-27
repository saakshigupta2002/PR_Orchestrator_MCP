"""Templates for generating GitHub PR bodies."""

from __future__ import annotations


def generate_pr_body(
    summary: str,
    changes: list[str],
    unit_tests: list[str],
    verification_commands: list[str],
    related_issue: str,
    notes: str,
    base_template: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Return a formatted pull request body.

    The body includes required sections (Summary, Changes, Unit Tests Added/Updated,
    Verification, Related to, Notes/Risks) and avoids auto‑close keywords.
    If a ``base_template`` is provided (e.g., loaded from
    `.github/pull_request_template.md`), it is prepended to the generated
    sections.  An ``issue_url`` can be supplied to explicitly link to the
    relevant issue instead of relying on the caller to insert the URL in
    ``related_issue``.
    """
    body_parts: list[str] = []
    # Include the base template if provided
    if base_template:
        base = base_template.strip()
        if base:
            body_parts.append(base)
            # Ensure separation
            if not base.endswith("\n\n"):
                body_parts.append("\n\n")
    # Core sections
    body_parts.append("### Summary\n")
    body_parts.append(summary.strip() + "\n\n")
    body_parts.append("### Changes\n")
    for change in changes:
        body_parts.append(f"- {change}\n")
    body_parts.append("\n### Unit Tests Added/Updated\n")
    if unit_tests:
        for test in unit_tests:
            body_parts.append(f"- {test}\n")
    else:
        body_parts.append("None\n")
    body_parts.append("\n### Verification\n")
    for cmd in verification_commands:
        body_parts.append(f"- `{cmd}`\n")
    body_parts.append("\n### Related to\n")
    # Always include the issue reference line with the prefix "Related to".
    # The related_issue argument should contain the issue number prefixed with '#'.
    body_parts.append(f"Related to {related_issue}\n")
    # On the next line, include the issue URL if available.  Leave a blank line
    # afterwards to separate from the notes section.
    if issue_url:
        body_parts.append(f"{issue_url}\n\n")
    else:
        # If no URL provided, still insert a blank line to maintain spacing.
        body_parts.append("\n")
    body_parts.append("### Notes/Risks\n")
    body_parts.append(notes.strip() + "\n")
    return "".join(body_parts)
