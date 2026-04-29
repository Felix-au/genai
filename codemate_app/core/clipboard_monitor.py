"""
╔══════════════════════════════════════════════════════════════╗
║         CodeMate — Clipboard Monitor (Win32 Native)          ║
╚══════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
import ctypes, ctypes.wintypes, logging, re, time
from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)

CODE_PATTERNS = [
    re.compile(r"\bdef\s+\w+\s*\("), re.compile(r"\bclass\s+\w+"),
    re.compile(r"\bimport\s+\w+"), re.compile(r"\bfrom\s+\w+\s+import\b"),
    re.compile(r"\b(if|elif|else|for|while)\b.*:"),
    re.compile(r"\breturn\b"), re.compile(r"[{}\[\];]"),
    re.compile(r"^\s{2,}\S", re.MULTILINE),
    re.compile(r"(//|#|/\*|\*/)"),
    re.compile(r"\b(const|let|var|function|=>)\b"),
    re.compile(r"\b(public|private|static|void)\b"),
    re.compile(r"Traceback \(most recent call"),
    re.compile(r"std::|#include"), re.compile(r"\bprint\s*\("),
]

def looks_like_code(text: str) -> bool:
    if not text or len(text.strip()) < 20:
        return False
    return sum(1 for p in CODE_PATTERNS if p.search(text)) >= 2


class ClipboardMonitor(QThread):
    code_copied = Signal(str)
    status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._running = True
        self._last_text = ""

    def stop(self):
        self._running = False

    def run(self):
        try:
            self._run_win32()
        except Exception:
            self._run_polling()

    def _run_win32(self):
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM)
        WM_CLIPBOARDUPDATE = 0x031D

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_CLIPBOARDUPDATE:
                self._check_clipboard()
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wnd_proc_ref = WNDPROC(wnd_proc)
        wc = wintypes.WNDCLASSW()
        wc.lpfnWndProc = self._wnd_proc_ref
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "CMClip"
        user32.RegisterClassW(ctypes.byref(wc))
        hwnd = user32.CreateWindowExW(0, "CMClip", "CM", 0, 0, 0, 0, 0, wintypes.HWND(-3), None, wc.hInstance, None)
        if not hwnd:
            raise RuntimeError("hwnd failed")
        user32.AddClipboardFormatListener(hwnd)
        self.status_changed.emit("Clipboard monitor active (native)")
        msg = wintypes.MSG()
        while self._running:
            if user32.PeekMessageW(ctypes.byref(msg), hwnd, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.05)
        user32.DestroyWindow(hwnd)

    def _run_polling(self):
        import pyperclip
        self.status_changed.emit("Clipboard monitor active (polling)")
        while self._running:
            try:
                current = pyperclip.paste()
                if current and current != self._last_text:
                    self._last_text = current
                    if looks_like_code(current):
                        self.code_copied.emit(current)
            except Exception:
                pass
            time.sleep(0.5)

    def _check_clipboard(self):
        try:
            import pyperclip
            text = pyperclip.paste()
            if text and text != self._last_text:
                self._last_text = text
                if looks_like_code(text):
                    self.code_copied.emit(text)
        except Exception:
            pass
