"""Quality assurance helpers."""

from .detect import detect_project
from .install import install_deps
from .lint import run_format, run_lint, run_precommit
from .tests import run_tests, run_typecheck

__all__ = [
    "detect_project",
    "install_deps",
    "run_tests",
    "run_lint",
    "run_typecheck",
    "run_format",
    "run_precommit",
]
