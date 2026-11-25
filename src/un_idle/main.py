from __future__ import annotations

import signal
import sys
import threading

from config import AppConfig, load_config, save_config
from engine import UnIdleEngine
from ui import TrayController


def main() -> int:
    cfg = load_config()
    cfg_lock = threading.RLock()
    current_cfg = cfg
    stop_event = threading.Event()

    def get_cfg() -> AppConfig:
        with cfg_lock:
            return current_cfg

    def apply_cfg(updated: AppConfig) -> None:
        nonlocal current_cfg
        normalized = updated.normalized()
        with cfg_lock:
            current_cfg = normalized
        save_config(normalized)
        engine.update_config(normalized)
        tray.refresh_icon(active=normalized.enabled)

    def set_enabled(enabled: bool) -> None:
        cur = get_cfg()
        next_cfg = AppConfig(
            enabled=enabled,
            mode=cur.mode,
            idle_threshold_sec=cur.idle_threshold_sec,
            pulse_interval_sec=cur.pulse_interval_sec,
            jiggle_pixels=cur.jiggle_pixels,
            hide_from_capture=cur.hide_from_capture,
            schedule=cur.schedule,
        )
        apply_cfg(next_cfg)

    def on_quit() -> None:
        stop_event.set()

    engine = UnIdleEngine(get_cfg())
    tray = TrayController(
        get_config=get_cfg,
        on_save_config=apply_cfg,
        on_toggle_enabled=set_enabled,
        on_quit=on_quit,
    )

    def _signal_handler(signum, frame):
        stop_event.set()
        tray._handle_quit()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _signal_handler)
        except Exception:
            pass

    engine.start()
    try:
        tray.run()
    finally:
        engine.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
