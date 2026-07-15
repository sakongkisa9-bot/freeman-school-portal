"""Lightweight debug logging support without a visible console UI."""

from __future__ import annotations

import os
from typing import List, Optional

_DEBUG_BUFFER: List[str] = []
_DEBUG_LOG_FILE: Optional[str] = None


def clear_debug_buffer() -> None:
    """Clear the in-memory debug buffer."""
    _DEBUG_BUFFER.clear()


def get_debug_buffer() -> List[str]:
    """Return a copy of the in-memory debug buffer."""
    return list(_DEBUG_BUFFER)


def set_debug_log_file(path: str) -> None:
    """Set an optional file path for debug output."""
    global _DEBUG_LOG_FILE
    _DEBUG_LOG_FILE = path
    if path:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)


def debug_log(message: object, *args, **_kwargs) -> None:
    """Append a message to the buffer and optional log file."""
    text = str(message)
    if args:
        text = (
            text % args
            if "%" in text
            else f"{text} {' '.join(str(arg) for arg in args)}"
        )

    _DEBUG_BUFFER.append(text)
    if len(_DEBUG_BUFFER) > 1000:
        _DEBUG_BUFFER.pop(0)

    if _DEBUG_LOG_FILE:
        with open(_DEBUG_LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
