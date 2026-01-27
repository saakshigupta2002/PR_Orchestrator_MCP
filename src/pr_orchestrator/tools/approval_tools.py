"""Approval tool implementation.

This tool records the approval decision from the client.  It does not
automatically approve or reject; the client is responsible for providing
the ``approved`` flag.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

# In-memory store of approval records.  Each approved request yields a unique
# UUID which must be supplied to any subsequent tool that performs an
# irreversible action (e.g. pushing commits or opening a PR).  Approvals are
# multi-use: they can be used for both "push" and "open_pr" actions, but each
# action can only be performed once per approval.
_PENDING_APPROVALS: dict[str, dict[str, Any]] = {}


def request_approval(
    summary: str,
    unified_diff: str,
    checks: dict[str, object],
    pr_draft: bool,
    branch_plan: dict[str, object],
    approved: bool,
    notes: str = "",
    # S1: Additional fields for PR title/body and issue linking
    pr_title: str = "",
    pr_body: str = "",
    issue_url: str | None = None,
) -> dict[str, object]:
    """Record the approval decision and return an approval token if approved.

    The server verifies that mandatory fields (summary, unified_diff, checks,
    branch_plan) are present.  If ``approved`` is True, a unique approval
    identifier is generated and stored.  This identifier must be provided to
    tools that perform side effects (e.g., pushing commits or opening
    pull requests).
    
    The approval ID is multi-use: it can be consumed for both "push" and
    "open_pr" actions, but each action can only be performed once per approval.
    The approval record is only deleted when all allowed actions have been used.
    """
    if summary is None or unified_diff is None or checks is None or branch_plan is None:
        raise ValueError("summary, unified_diff, checks and branch_plan are required")
    if not approved:
        return {"approved": False, "notes": notes or ""}

    approval_id = str(uuid.uuid4())

    # B3: Store structured approval record that allows both push and open_pr
    _PENDING_APPROVALS[approval_id] = {
        "approved": True,
        "allowed_actions": {"push": True, "open_pr": True},
        "used": {"push": False, "open_pr": False},
        "checks": checks,
        "summary": summary,
        "unified_diff": unified_diff,
        "branch_plan": branch_plan,
        "pr_draft": pr_draft,
        "pr_title": pr_title,
        "pr_body": pr_body,
        "issue_url": issue_url,
        "notes": notes,
        "created_at": datetime.utcnow().isoformat(),
    }

    return {"approved": True, "approval_id": approval_id, "notes": notes or ""}


def consume_approval(approval_id: str, action: str = "push") -> bool:
    """Consume a pending approval ID for a specific action.

    Returns True if the approval ID exists, is approved, and the specified
    action has not already been used.  The action is marked as used, and
    the approval record is deleted only when all allowed actions have been
    consumed.
    
    This helper is used by irreversible actions (push/PR) to validate
    approvals.  Valid actions are "push" and "open_pr".
    """
    if action not in {"push", "open_pr"}:
        return False

    record = _PENDING_APPROVALS.get(approval_id)
    if record is None:
        return False

    # Check if approved
    if not record.get("approved", False):
        return False

    # Check if action is allowed
    allowed_actions = record.get("allowed_actions", {})
    if not allowed_actions.get(action, False):
        return False

    # Check if action has already been used
    used = record.get("used", {})
    if used.get(action, False):
        return False

    # Mark action as used
    record["used"][action] = True

    # Check if all actions have been used - if so, clean up the record
    all_used = all(record["used"].get(a, False) for a in record["allowed_actions"] if record["allowed_actions"].get(a))
    if all_used:
        del _PENDING_APPROVALS[approval_id]

    return True


def get_approval_record(approval_id: str) -> dict[str, Any] | None:
    """Retrieve an approval record without consuming it.
    
    This is useful for inspecting the approval state, including which
    actions have been used.
    """
    return _PENDING_APPROVALS.get(approval_id)
