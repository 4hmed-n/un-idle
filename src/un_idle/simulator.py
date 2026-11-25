from __future__ import annotations

import platform
import subprocess
import time

try:
    from pynput.keyboard import Controller as KeyController, Key
    from pynput.mouse import Controller as MouseController
    _HAS_PYNPUT_CTRL = True
except Exception:
    KeyController = None
    Key = None
    MouseController = None
    _HAS_PYNPUT_CTRL = False


class ActivitySimulator:
    """Executes simulation pulses and manages OS power assertions."""

    def __init__(self) -> None:
        self._mouse = MouseController() if (_HAS_PYNPUT_CTRL and MouseController) else None
        self._keyboard = KeyController() if (_HAS_PYNPUT_CTRL and KeyController) else None
        self._caffeinate_proc: subprocess.Popen | None = None
        self._awake_asserted = False

    def set_awake_assertion(self, active: bool) -> None:
        system = platform.system()
        if active == self._awake_asserted:
            return

        if system == "Windows":
            try:
                import ctypes
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_DISPLAY_REQUIRED = 0x00000002
                flags = (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED) if active else ES_CONTINUOUS
                ctypes.windll.kernel32.SetThreadExecutionState(flags)
                self._awake_asserted = active
            except Exception:
                pass
        elif system == "Darwin":
            if active and self._caffeinate_proc is None:
                try:
                    self._caffeinate_proc = subprocess.Popen(
                        ["caffeinate", "-dim"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self._awake_asserted = True
                except Exception:
                    pass
            elif not active and self._caffeinate_proc is not None:
                try:
                    self._caffeinate_proc.terminate()
                    self._caffeinate_proc.wait(timeout=2)
                except Exception:
                    pass
                finally:
                    self._caffeinate_proc = None
                    self._awake_asserted = False
        else:
            self._awake_asserted = active

    def pulse(self, mode: str, jiggle_pixels: int = 1) -> None:
        if mode == "awake_only":
            self.set_awake_assertion(True)
            return

        if mode == "micro-jiggle" and self._mouse is not None:
            try:
                x, y = self._mouse.position
                delta = max(1, int(jiggle_pixels))
                self._mouse.position = (x + delta, y)
                time.sleep(0.03)
                self._mouse.position = (x, y)
            except Exception:
                pass
        elif mode == "f15" and self._keyboard is not None and Key is not None:
            try:
                self._keyboard.press(Key.f15)
                time.sleep(0.02)
                self._keyboard.release(Key.f15)
            except Exception:
                pass

    def cleanup(self) -> None:
        self.set_awake_assertion(False)
