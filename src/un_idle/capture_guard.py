from __future__ import annotations

import ctypes
import logging
import platform
import sys
import tkinter as tk

logger = logging.getLogger("un_idle.capture_guard")

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
        logger.debug("Capture exclusion not supported on this platform/build")
        return False

    try:
        window.update_idletasks()
        user32 = ctypes.windll.user32
        
        # Declare argtypes and restype for type safety
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.SetWindowDisplayAffinity.restype = ctypes.c_bool
        
        hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
        if not hwnd:
            logger.error("Failed to get window handle")
            return False
        
        affinity = WDA_EXCLUDEFROMCAPTURE if enabled else WDA_NONE
        result = user32.SetWindowDisplayAffinity(hwnd, affinity)
        
        if not result:
            logger.error(f"SetWindowDisplayAffinity failed for hwnd={hwnd}")
            return False
        
        logger.info(f"Capture exclusion {'enabled' if enabled else 'disabled'} for hwnd={hwnd}")
        return True
    except Exception as e:
        logger.error(f"Exception in apply_capture_exclusion: {e}")
        return False
