"""Platform capability detection."""
from __future__ import annotations

import logging
import os
import platform

logger = logging.getLogger("un_idle.platform_info")


def detect_display_server() -> str:
    """Detect X11 vs Wayland on Linux."""
    if platform.system() != "Linux":
        return "none"
    
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type:
        return session_type
    
    # Fallback: check for Wayland display
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    
    # Check for X11 display
    if os.environ.get("DISPLAY"):
        return "x11"
    
    return "unknown"


def get_capabilities() -> dict[str, bool | str]:
    """Get platform capabilities and status."""
    system = platform.system()
    caps = {
        "platform": system,
        "idle_detection": True,  # pynput fallback always works
        "mouse_jiggle": True,
        "key_pulse": True,
        "power_assertion": False,
        "capture_exclusion": False,
        "display_server": "none",
    }
    
    if system == "Windows":
        caps["power_assertion"] = True
        from capture_guard import is_windows_capture_exclusion_supported
        caps["capture_exclusion"] = is_windows_capture_exclusion_supported()
    elif system == "Darwin":
        caps["power_assertion"] = True  # caffeinate available
    elif system == "Linux":
        display_server = detect_display_server()
        caps["display_server"] = display_server
        if display_server == "wayland":
            logger.warning("Wayland detected - some features may be limited")
            caps["capture_exclusion"] = False
            caps["mouse_jiggle"] = False  # May not work reliably
    
    return caps
