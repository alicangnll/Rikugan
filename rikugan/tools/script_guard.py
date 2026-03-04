"""Shared security patterns and execution helper for Python script execution tools."""

from __future__ import annotations

import contextlib
import io
import re
from typing import Callable, Dict, Any

# Patterns that indicate process execution — blocked for safety.
BLOCKED_SCRIPT_PATTERNS = [
    r"\bsubprocess\b",
    r"\bos\.system\s*\(",
    r"\bos\.popen\s*\(",
    r"\bos\.exec\w*\s*\(",
    r"\bos\.spawn\w*\s*\(",
    r"\bPopen\s*\(",
    r"\b__import__\s*\(\s*['\"]subprocess['\"]\s*\)",
]
BLOCKED_SCRIPT_RE = re.compile("|".join(BLOCKED_SCRIPT_PATTERNS))


def run_guarded_script(code: str, namespace_factory: Callable[[], Dict[str, Any]]) -> str:
    """Block dangerous patterns, exec code, and return captured stdout/stderr."""
    match = BLOCKED_SCRIPT_RE.search(code)
    if match:
        return f"Error: Blocked — code contains disallowed process execution: '{match.group()}'"

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    namespace = namespace_factory()

    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        try:
            exec(code, namespace)  # noqa: S102 — intentional scripting tool
        except Exception as e:
            stderr_buf.write(f"{type(e).__name__}: {e}\n")

    stdout = stdout_buf.getvalue()
    stderr = stderr_buf.getvalue()
    parts = []
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    if not parts:
        parts.append("(no output)")
    return "\n".join(parts)
