"""errors.py — exceptions cho approach_script_completion providers."""
from __future__ import annotations


class ApproachScriptCompletionError(RuntimeError):
    """Raised when an ApproachScriptCompletionProvider fails to produce a completion."""
