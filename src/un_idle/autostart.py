"""Start-at-login configuration."""
from __future__ import annotations

import logging
import platform
import sys
from pathlib import Path

logger = logging.getLogger("un_idle.autostart")


def is_autostart_enabled() -> bool:
    """Check if start-at-login is enabled."""
    system = platform.system()
    
    if system == "Windows":
        return _is_autostart_windows()
    elif system == "Darwin":
        logger.warning("macOS autostart check not implemented")
        return False
    else:
        logger.warning("Linux autostart check not implemented")
        return False


def set_autostart(enabled: bool) -> bool:
    """Enable or disable start-at-login. Returns True on success."""
    system = platform.system()
    
    if system == "Windows":
        return _set_autostart_windows(enabled)
    elif system == "Darwin":
        logger.warning("macOS autostart not implemented")
        return False
    else:
        logger.warning("Linux autostart not implemented")
        return False


def _is_autostart_windows() -> bool:
    """Check Windows registry for autostart entry."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            try:
                winreg.QueryValueEx(key, "Un-Idle")
                return True
            except FileNotFoundError:
                return False
    except Exception as e:
        logger.error(f"Failed to check autostart: {e}")
        return False


def _set_autostart_windows(enabled: bool) -> bool:
    """Set Windows registry autostart entry."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        if enabled:
            # Get executable path
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                # Running from source - use python + script path
                exe_path = f'"{sys.executable}" "{Path(__file__).parent / "main.py"}"'
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "Un-Idle", 0, winreg.REG_SZ, exe_path)
            logger.info(f"Autostart enabled: {exe_path}")
            return True
        else:
            # Remove entry
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, "Un-Idle")
                    logger.info("Autostart disabled")
                except FileNotFoundError:
                    pass  # Already removed
            return True
            
    except Exception as e:
        logger.error(f"Failed to set autostart: {e}")
        return False
