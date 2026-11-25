from __future__ import annotations

import threading
import time
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from config import AppConfig
from idle_detector import IdleDetector
from simulator import ActivitySimulator


class EngineState(str, Enum):
    PAUSED = "paused"
    OUT_OF_SCHEDULE = "out_of_schedule"
    MONITORING = "monitoring"
    SIMULATING = "simulating"


def _parse_hhmm(value: str) -> tuple[int, int] | None:
    try:
        parts = value.strip().split(":")
        if len(parts) != 2:
            return None
        hour = int(parts[0])
        minute = int(parts[1])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except Exception:
        pass
    return None


def is_within_schedule(cfg: AppConfig, now: datetime | None = None) -> bool:
    sched = cfg.schedule
    if not sched.enabled:
        return True
    current = now or datetime.now()
    if current.weekday() not in sched.days:
        return False

    start = _parse_hhmm(sched.start_time)
    end = _parse_hhmm(sched.end_time)
    if not start or not end:
        return True

    cur_mins = current.hour * 60 + current.minute
    start_mins = start[0] * 60 + start[1]
    end_mins = end[0] * 60 + end[1]

    if start_mins <= end_mins:
        return start_mins <= cur_mins <= end_mins
    return cur_mins >= start_mins or cur_mins <= end_mins


class UnIdleEngine:
    """Background state machine coordinating idle detection and simulation pulses."""

    def __init__(
        self,
        config: AppConfig,
        on_state_change: Optional[Callable[[EngineState], None]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._config = config.normalized()
        self._detector = IdleDetector()
        self._simulator = ActivitySimulator()
        self._on_state_change = on_state_change
        self._state = EngineState.PAUSED if not self._config.enabled else EngineState.MONITORING
        self._stop_event = threading.Event()
        self._last_pulse_time = 0.0
        self._thread = threading.Thread(target=self._run_loop, name="UnIdleEngine", daemon=True)

    @property
    def state(self) -> EngineState:
        with self._lock:
            return self._state

    @property
    def config(self) -> AppConfig:
        with self._lock:
            return self._config

    def update_config(self, new_config: AppConfig) -> None:
        with self._lock:
            self._config = new_config.normalized()
            if not self._config.enabled or self._config.mode != "awake_only":
                self._simulator.set_awake_assertion(False)

    def _set_state(self, next_state: EngineState) -> None:
        changed = False
        with self._lock:
            if self._state != next_state:
                self._state = next_state
                changed = True
        if changed and self._on_state_change:
            try:
                self._on_state_change(next_state)
            except Exception:
                pass

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._simulator.cleanup()
        self._detector.stop()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                cfg = self._config

            if not cfg.enabled:
                self._simulator.set_awake_assertion(False)
                self._set_state(EngineState.PAUSED)
                self._stop_event.wait(0.5)
                continue

            if not is_within_schedule(cfg):
                self._simulator.set_awake_assertion(False)
                self._set_state(EngineState.OUT_OF_SCHEDULE)
                self._stop_event.wait(1.0)
                continue

            if cfg.mode == "awake_only":
                self._simulator.set_awake_assertion(True)

            idle_sec = self._detector.get_idle_seconds()
            now_mono = time.monotonic()

            if idle_sec >= cfg.idle_threshold_sec:
                self._set_state(EngineState.SIMULATING)
                if (now_mono - self._last_pulse_time) >= cfg.pulse_interval_sec:
                    self._simulator.pulse(cfg.mode, cfg.jiggle_pixels)
                    self._last_pulse_time = time.monotonic()
            else:
                self._set_state(EngineState.MONITORING)

            self._stop_event.wait(0.25)
