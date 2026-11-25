"""Logging configuration with rotating file handler."""
from __future__ import annotations

import logging
import logging.handlers
import platform
from pathlib import Path


def get_log_dir() -> Path:
    """Get platform-specific log directory."""
    system = platform.system()
    
    if system == "Windows":
        import os
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "un-idle"
    elif system == "Darwin":
        return Path.home() / "Library" / "Logs" / "un-idle"
    else:  # Linux and others
        import os
        xdg_state = os.environ.get("XDG_STATE_HOME")
        if xdg_state:
            return Path(xdg_state) / "un-idle"
        return Path.home() / ".local" / "state" / "un-idle"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Set up rotating file logger.
    - 1 MB max per file
    - 3 backup files
    - Never logs keystrokes or window contents
    """
    logger = logging.getLogger("un_idle")
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    
    # Rotating file handler: 1MB x 3 backups
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=3,
        encoding="utf-8"
    )
    
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
