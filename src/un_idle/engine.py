from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from un_idle.config import AppConfig
from un_idle.idle_detector import IdleDetector
from un_idle.simulator import ActivitySimulator

logger = logging.getLogger("un_idle.engine")


class EngineState(str, Enum):
    PAUSED = "paused"
    TEMP_PAUSED = "temp_paused"  # Temporary pause (timer-based)
    OUT_OF_SCHEDULE = "out_of_schedule"
    MONITORING = "monitoring"
    SIMULATING = "simulating"
    DEGRADED = "degraded"  # Partial functionality
    UNSUPPORTED = "unsupported"  # Feature not available on platform


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
    """
    Check if current time is within the schedule window.
    
    - Selected weekdays are START days for the window
    - For overnight schedules (e.g., Mon 22:00-06:00), Tue 02:00 is IN schedule
    - Uses half-open interval [start, end)
    - If start == end, treat as 24/7 (all day)
    - Invalid time strings fail CLOSED (returns False)
    """
    sched = cfg.schedule
    if not sched.enabled:
        return True
    
    current = now or datetime.now()
    start = _parse_hhmm(sched.start_time)
    end = _parse_hhmm(sched.end_time)
    
    # Invalid times fail CLOSED
    if not start or not end:
        return False
    
    start_mins = start[0] * 60 + start[1]
    end_mins = end[0] * 60 + end[1]
    
    # Equal start/end means 24/7
    if start_mins == end_mins:
        return current.weekday() in sched.days
    
    cur_mins = current.hour * 60 + current.minute
    cur_day = current.weekday()
    
    # Non-overnight schedule (e.g., 09:00-17:00)
    if start_mins < end_mins:
        return cur_day in sched.days and start_mins <= cur_mins < end_mins
    
    # Overnight schedule (e.g., 22:00-06:00)
    # Check if we're in the late part (after start on selected day)
    if cur_mins >= start_mins and cur_day in sched.days:
        return True
    
    # Check if we're in the early part (before end on day after selected day)
    prev_day = (cur_day - 1) % 7
    if cur_mins < end_mins and prev_day in sched.days:
        return True
    
    return False


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
        self._pause_until = 0.0  # Unix timestamp for temporary pause
        self._thread = threading.Thread(target=self._run_loop, name="UnIdleEngine", daemon=True)
    
    def pause_for_duration(self, minutes: int) -> None:
        """Temporarily pause for specified minutes."""
        with self._lock:
            self._pause_until = time.time() + (minutes * 60)
        logger.info(f"Paused for {minutes} minutes")
    
    def pause_until_tomorrow(self) -> None:
        """Pause until tomorrow at 00:00."""
        from datetime import datetime, timedelta
        tomorrow = datetime.now() + timedelta(days=1)
        midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        with self._lock:
            self._pause_until = midnight.timestamp()
        logger.info(f"Paused until tomorrow ({midnight})")

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
                prev_state = self._state
                self._state = next_state
                changed = True
        if changed:
            logger.info(f"State transition: {prev_state.value} -> {next_state.value}")
            if self._on_state_change:
                try:
                    self._on_state_change(next_state)
                except Exception as e:
                    logger.error(f"State change callback failed: {e}")

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
                pause_until = self._pause_until
            
            # Check temporary pause
            if pause_until > time.time():
                self._simulator.set_awake_assertion(False)
                self._set_state(EngineState.TEMP_PAUSED)
                self._stop_event.wait(1.0)
                continue

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
            
            # Ignore idle resets that happen shortly after our own pulses
            # (within 3 seconds window to account for synthetic event detection)
            time_since_pulse = now_mono - self._last_pulse_time
            if self._last_pulse_time > 0 and time_since_pulse < 3.0 and idle_sec < 3.0:
                # Likely our own synthetic event, treat as still idle
                idle_sec = cfg.idle_threshold_sec + 1.0

            if idle_sec >= cfg.idle_threshold_sec:
                self._set_state(EngineState.SIMULATING)
                if (now_mono - self._last_pulse_time) >= cfg.pulse_interval_sec:
                    self._simulator.pulse(cfg.mode, cfg.jiggle_pixels)
                    self._last_pulse_time = time.monotonic()
            else:
                # Only stop simulating if idle is genuinely low (not in synthetic window)
                if time_since_pulse >= 3.0 or self._last_pulse_time == 0:
                    self._set_state(EngineState.MONITORING)

            self._stop_event.wait(0.25)
