from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List


DEFAULT_CONFIG_DIR = Path(
    os.environ.get("UN_IDLE_CONFIG_DIR")
    or (Path.home() / ".config" / "un-idle")
)
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"

VALID_MODES = ("micro-jiggle", "f15", "awake_only")


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
        if self.mode not in VALID_MODES:
            self.mode = "micro-jiggle"
        self.idle_threshold_sec = max(5.0, float(self.idle_threshold_sec))
        self.pulse_interval_sec = max(5.0, float(self.pulse_interval_sec))
        self.jiggle_pixels = max(1, min(25, int(self.jiggle_pixels)))
        self.hide_from_capture = bool(self.hide_from_capture)
        valid_days = [d for d in self.schedule.days if isinstance(d, int) and 0 <= d <= 6]
        self.schedule.days = valid_days or [0, 1, 2, 3, 4]
        return self


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    try:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            sched_raw = raw.get("schedule", {}) if isinstance(raw, dict) else {}
            schedule = ScheduleConfig(
                enabled=bool(sched_raw.get("enabled", False)),
                start_time=str(sched_raw.get("start_time", "09:00")),
                end_time=str(sched_raw.get("end_time", "18:00")),
                days=list(sched_raw.get("days", [0, 1, 2, 3, 4])),
            )
            cfg = AppConfig(
                enabled=bool(raw.get("enabled", True)),
                mode=str(raw.get("mode", "micro-jiggle")),
                idle_threshold_sec=float(raw.get("idle_threshold_sec", 45.0)),
                pulse_interval_sec=float(raw.get("pulse_interval_sec", 20.0)),
                jiggle_pixels=int(raw.get("jiggle_pixels", 1)),
                hide_from_capture=bool(raw.get("hide_from_capture", True)),
                schedule=schedule,
            )
            return cfg.normalized()
    except Exception:
        pass
    return AppConfig().normalized()


def save_config(cfg: AppConfig, path: Path = DEFAULT_CONFIG_PATH) -> Path:
    cfg.normalized()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(cfg)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
