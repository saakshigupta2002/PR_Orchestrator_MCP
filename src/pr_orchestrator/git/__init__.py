"""Git package placeholder.

This package previously exposed GitPython‑based operations and a branch name
strategy.  Since the orchestrator now relies on the git command‑line
interface and high‑level tools in ``pr_orchestrator.tools.repo_tools``, the
GitPython modules have been removed.  The package remains for backward
compatibility but exports no symbols.
"""

__all__: list[str] = []
