from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import time

try:
    from pynput import keyboard, mouse
    _HAS_PYNPUT = True
except Exception:
    keyboard = None
    mouse = None
    _HAS_PYNPUT = False

logger = logging.getLogger("un_idle.idle_detector")


class IdleDetector:
    """Tracks seconds since last user input using OS idle timers with listener fallback."""

    def __init__(self) -> None:
        self._last_listener_event = time.monotonic()
        self._mouse_listener = None
        self._key_listener = None
        logger.info("IdleDetector initializing")
        self._start_listeners()

    def _on_activity(self, *args, **kwargs) -> None:
        self._last_listener_event = time.monotonic()

    def _start_listeners(self) -> None:
        if not _HAS_PYNPUT:
            return
        try:
            self._mouse_listener = mouse.Listener(
                on_move=self._on_activity,
                on_click=self._on_activity,
                on_scroll=self._on_activity,
            )
            self._mouse_listener.daemon = True
            self._mouse_listener.start()
        except Exception:
            self._mouse_listener = None

        try:
            self._key_listener = keyboard.Listener(
                on_press=self._on_activity,
            )
            self._key_listener.daemon = True
            self._key_listener.start()
        except Exception:
            self._key_listener = None

    def stop(self) -> None:
        for listener in (self._mouse_listener, self._key_listener):
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass

    def _windows_idle_seconds(self) -> float | None:
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                return None
            tick_count = ctypes.windll.kernel32.GetTickCount()
            elapsed_ms = (tick_count - lii.dwTime) & 0xFFFFFFFF
            return elapsed_ms / 1000.0
        except Exception:
            return None

    def _macos_idle_seconds(self) -> float | None:
        try:
            out = subprocess.check_output(
                ["ioreg", "-c", "IOHIDSystem", "-d", "4"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1.5,
            )
            for line in out.splitlines():
                if "HIDIdleTime" in line:
                    parts = line.split("=")
                    if len(parts) >= 2:
                        raw_val = parts[-1].strip().split()[0]
                        ns = int(raw_val)
                        return ns / 1_000_000_000.0
        except Exception:
            return None
        return None

    def _linux_idle_seconds(self) -> float | None:
        if shutil.which("xprintidle"):
            try:
                out = subprocess.check_output(
                    ["xprintidle"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=1.0,
                ).strip()
                return int(out) / 1000.0
            except Exception:
                return None
        return None

    def get_idle_seconds(self) -> float:
        system = platform.system()
        os_idle: float | None = None
        if system == "Windows":
            os_idle = self._windows_idle_seconds()
        elif system == "Darwin":
            os_idle = self._macos_idle_seconds()
        elif system == "Linux":
            os_idle = self._linux_idle_seconds()

        listener_idle = max(0.0, time.monotonic() - self._last_listener_event)
        if os_idle is not None:
            return max(0.0, min(os_idle, listener_idle))
        return listener_idle
