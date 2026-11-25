from __future__ import annotations

import json
import logging
import math
import os
import platform
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List

logger = logging.getLogger("un_idle.config")


def get_config_dir() -> Path:
    """Get platform-specific config directory."""
    system = platform.system()
    
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "un-idle"
    elif system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "un-idle"
    else:  # Linux and others
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "un-idle"
        return Path.home() / ".config" / "un-idle"


# Check for old config location and migrate if needed
def _migrate_old_config() -> Path | None:
    """Migrate from old ~/.config/un-idle location if it exists."""
    old_path = Path.home() / ".config" / "un-idle" / "config.json"
    if old_path.exists():
        new_dir = get_config_dir()
        if new_dir != old_path.parent:
            logger.info(f"Migrating config from {old_path} to {new_dir}")
            return old_path
    return None


DEFAULT_CONFIG_DIR = get_config_dir()
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"

VALID_MODES = ("micro-jiggle", "f15", "awake_only")


# Preset configurations (applied after AppConfig is defined)
def get_preset(name: str) -> dict | None:
    """Get a preset configuration by name as a dict."""
    presets = {
        "Reading": {
            "enabled": True,
            "mode": "awake_only",
            "idle_threshold_sec": 180.0,
            "pulse_interval_sec": 60.0,
            "jiggle_pixels": 1,
            "hide_from_capture": True,
        },
        "Presentation": {
            "enabled": True,
            "mode": "awake_only",
            "idle_threshold_sec": 30.0,
            "pulse_interval_sec": 30.0,
            "jiggle_pixels": 1,
            "hide_from_capture": True,
        },
        "Download": {
            "enabled": True,
            "mode": "f15",
            "idle_threshold_sec": 120.0,
            "pulse_interval_sec": 60.0,
            "jiggle_pixels": 1,
            "hide_from_capture": True,
        },
    }
    return presets.get(name)


def _validate_time_string(time_str: str) -> bool:
    """Validate HH:MM format and range."""
    try:
        parts = time_str.strip().split(":")
        if len(parts) != 2:
            return False
        hour = int(parts[0])
        minute = int(parts[1])
        return 0 <= hour <= 23 and 0 <= minute <= 59
    except Exception:
        return False


@dataclass
class ScheduleConfig:
    enabled: bool = False
    start_time: str = "09:00"
    end_time: str = "18:00"
    days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon=0 .. Sun=6


@dataclass
class AppConfig:
    enabled: bool = True
    mode: str = "micro-jiggle"
    idle_threshold_sec: float = 45.0
    pulse_interval_sec: float = 20.0
    jiggle_pixels: int = 1
    hide_from_capture: bool = True
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)

    def normalized(self) -> "AppConfig":
        """
        Normalize and validate config values.
        - Reject non-finite numbers
        - Validate types (don't bool("false"))
        - Add upper bounds
        - Validate schedule times
        """
        # Mode validation
        if self.mode not in VALID_MODES:
            logger.warning(f"Invalid mode '{self.mode}', defaulting to 'micro-jiggle'")
            self.mode = "micro-jiggle"
        
        # Number validation - reject non-finite
        if not math.isfinite(self.idle_threshold_sec):
            logger.warning(f"Non-finite idle_threshold_sec, using default")
            self.idle_threshold_sec = 45.0
        if not math.isfinite(self.pulse_interval_sec):
            logger.warning(f"Non-finite pulse_interval_sec, using default")
            self.pulse_interval_sec = 20.0
        
        # Bounds: idle_threshold [5, 3600], pulse_interval [5, 3600], jiggle [1, 25]
        self.idle_threshold_sec = max(5.0, min(3600.0, float(self.idle_threshold_sec)))
        self.pulse_interval_sec = max(5.0, min(3600.0, float(self.pulse_interval_sec)))
        self.jiggle_pixels = max(1, min(25, int(self.jiggle_pixels)))
        
        # Boolean validation (strict)
        if not isinstance(self.enabled, bool):
            self.enabled = bool(self.enabled) if self.enabled not in ("false", "False", "0") else False
        if not isinstance(self.hide_from_capture, bool):
            self.hide_from_capture = bool(self.hide_from_capture) if self.hide_from_capture not in ("false", "False", "0") else False
        
        # Schedule validation
        if not isinstance(self.schedule.enabled, bool):
            self.schedule.enabled = bool(self.schedule.enabled) if self.schedule.enabled not in ("false", "False", "0") else False
        
        # Validate time strings
        if not _validate_time_string(self.schedule.start_time):
            logger.warning(f"Invalid start_time '{self.schedule.start_time}', using 09:00")
            self.schedule.start_time = "09:00"
        if not _validate_time_string(self.schedule.end_time):
            logger.warning(f"Invalid end_time '{self.schedule.end_time}', using 18:00")
            self.schedule.end_time = "18:00"
        
        # Validate weekdays
        valid_days = [d for d in self.schedule.days if isinstance(d, int) and 0 <= d <= 6]
        if not valid_days:
            logger.warning("No valid weekdays, defaulting to Mon-Fri")
            valid_days = [0, 1, 2, 3, 4]
        self.schedule.days = valid_days
        
        return self


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load config with migration support and corruption handling."""
    # Check for old location first
    old_path = _migrate_old_config()
    if old_path and old_path.exists():
        try:
            logger.info(f"Loading config from old location: {old_path}")
            cfg = _load_from_path(old_path)
            # Save to new location
            save_config(cfg, path)
            # Keep old as backup
            old_path.rename(old_path.with_suffix(".json.migrated"))
            return cfg
        except Exception as e:
            logger.error(f"Migration failed: {e}")
    
    return _load_from_path(path)


def _load_from_path(path: Path) -> AppConfig:
    """Load config from specific path with corruption handling."""
    try:
        if path.exists():
            raw_text = path.read_text(encoding="utf-8")
            raw = json.loads(raw_text)
            sched_raw = raw.get("schedule", {}) if isinstance(raw, dict) else {}
            schedule = ScheduleConfig(
                enabled=sched_raw.get("enabled", False),
                start_time=str(sched_raw.get("start_time", "09:00")),
                end_time=str(sched_raw.get("end_time", "18:00")),
                days=list(sched_raw.get("days", [0, 1, 2, 3, 4])),
            )
            cfg = AppConfig(
                enabled=raw.get("enabled", True),
                mode=str(raw.get("mode", "micro-jiggle")),
                idle_threshold_sec=float(raw.get("idle_threshold_sec", 45.0)),
                pulse_interval_sec=float(raw.get("pulse_interval_sec", 20.0)),
                jiggle_pixels=int(raw.get("jiggle_pixels", 1)),
                hide_from_capture=raw.get("hide_from_capture", True),
                schedule=schedule,
            )
            logger.info(f"Config loaded from {path}")
            return cfg.normalized()
    except json.JSONDecodeError as e:
        logger.error(f"Corrupt JSON in {path}: {e}")
        # Save corrupt file for analysis
        try:
            corrupt_path = path.with_suffix(".corrupt.json")
            path.rename(corrupt_path)
            logger.info(f"Corrupt config saved to {corrupt_path}")
        except Exception as e2:
            logger.error(f"Failed to save corrupt config: {e2}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
    
    logger.info("Using default config")
    return AppConfig().normalized()


def save_config(cfg: AppConfig, path: Path = DEFAULT_CONFIG_PATH) -> bool:
    """
    Save config atomically with backup.
    Returns True on success, False on failure.
    """
    cfg.normalized()
    
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing config
        if path.exists():
            backup_path = path.with_suffix(".json.bak")
            try:
                path.replace(backup_path)
                logger.debug(f"Backed up config to {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")
        
        # Atomic save: write to temp file, then rename
        payload = asdict(cfg)
        json_str = json.dumps(payload, indent=2)
        
        # Use temp file in same directory for atomic rename
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=path.parent,
            delete=False,
            suffix='.tmp'
        ) as tmp:
            tmp.write(json_str)
            tmp_path = Path(tmp.name)
        
        # Atomic rename
        tmp_path.replace(path)
        logger.info(f"Config saved to {path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False
