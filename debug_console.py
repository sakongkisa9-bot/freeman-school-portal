import os
import sys
import threading
from datetime import datetime
from typing import List

try:
    import customtkinter as ctk
except Exception:  # pragma: no cover - optional runtime dependency
    ctk = None

_DEBUG_BUFFER: List[str] = []
_DEBUG_LOG_FILE = None
_DEBUG_LOCK = threading.Lock()
_DEBUG_WINDOW = None


def set_debug_log_file(path: str | None):
    global _DEBUG_LOG_FILE
    _DEBUG_LOG_FILE = path


def get_debug_buffer() -> List[str]:
    return list(_DEBUG_BUFFER)


def clear_debug_buffer():
    global _DEBUG_BUFFER
    _DEBUG_BUFFER = []


def debug_log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    with _DEBUG_LOCK:
        _DEBUG_BUFFER.append(entry)
        if len(_DEBUG_BUFFER) > 400:
            _DEBUG_BUFFER[:] = _DEBUG_BUFFER[-400:]
        print(entry)

        if _DEBUG_LOG_FILE:
            try:
                with open(_DEBUG_LOG_FILE, "a", encoding="utf-8") as handle:
                    handle.write(entry + "\n")
            except Exception:
                pass

    if _DEBUG_WINDOW is not None and hasattr(_DEBUG_WINDOW, "refresh_display"):
        try:
            _DEBUG_WINDOW.refresh_display()
        except Exception:
            pass

    return entry


def format_debug_buffer(limit: int = 200) -> str:
    with _DEBUG_LOCK:
        return "\n".join(_DEBUG_BUFFER[-limit:])


class DebugConsoleWindow:
    def __init__(self, master=None):
        if ctk is None:
            raise RuntimeError("customtkinter is not available")

        self.window = ctk.CTkToplevel(master)
        self.window.title("Freeman Debug Console")
        self.window.geometry("900x500")
        self.window.minsize(700, 350)

        self.textbox = ctk.CTkTextbox(
            self.window, font=("Consolas", 11), activate_scrollbars=True
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(button_frame, text="Clear", command=self.clear).pack(side="right")
        ctk.CTkButton(
            button_frame, text="Save to file", command=self.save_to_file
        ).pack(side="right", padx=5)

        self.refresh_display()

    def clear(self):
        clear_debug_buffer()
        self.refresh_display()

    def save_to_file(self):
        path = _DEBUG_LOG_FILE or os.path.join(
            os.path.expanduser("~"), "FreemanSchoolPortal", "debug_output.txt"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(format_debug_buffer(400))

    def refresh_display(self):
        text = format_debug_buffer(400)
        if not text:
            text = "No debug output yet. Saving marks errors will appear here."
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.insert("0.0", text)
        self.textbox.configure(state="disabled")


def show_debug_console(master=None):
    global _DEBUG_WINDOW
    if ctk is None:
        return None
    if (
        _DEBUG_WINDOW is None
        or not getattr(_DEBUG_WINDOW, "window", None)
        or not _DEBUG_WINDOW.window.winfo_exists()
    ):
        _DEBUG_WINDOW = DebugConsoleWindow(master)
    else:
        _DEBUG_WINDOW.window.lift()
        _DEBUG_WINDOW.window.focus_force()
    return _DEBUG_WINDOW
