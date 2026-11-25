from __future__ import annotations

import ctypes
import platform
import sys
import tkinter as tk

WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 v2004+ (build 19041+)
GA_ROOT = 2


def get_windows_build() -> int | None:
    if platform.system() != "Windows":
        return None
    winver = getattr(sys, "getwindowsversion", None)
    if callable(winver):
        try:
            return int(winver().build)
        except Exception:
            pass
    ver = getattr(platform, "win32_ver", lambda: ("", ""))()
    parts = str(ver[1]).split(".")
    if len(parts) >= 3 and parts[2].isdigit():
        return int(parts[2])
    return None


def is_windows_capture_exclusion_supported() -> bool:
    build = get_windows_build()
    return build is not None and build >= 19041


def apply_capture_exclusion(window: tk.Misc, enabled: bool = True) -> bool:
    """Set or clear WDA_EXCLUDEFROMCAPTURE on a Tkinter window's top-level HWND on Windows."""
    if not is_windows_capture_exclusion_supported():
        return False

    try:
        window.update_idletasks()
        user32 = ctypes.windll.user32
        hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
        if not hwnd:
            return False
        affinity = WDA_EXCLUDEFROMCAPTURE if enabled else WDA_NONE
        return bool(user32.SetWindowDisplayAffinity(hwnd, affinity))
    except Exception:
        return False
