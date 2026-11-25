from __future__ import annotations

import signal
import sys
import threading

from config import AppConfig, load_config, save_config
from engine import UnIdleEngine
from logging_config import setup_logging
from single_instance import SingleInstanceLock
from ui import TrayController


def main() -> int:
    logger = setup_logging()
    logger.info("Un-Idle starting")
    logger.info(f"Python {sys.version}, Platform {sys.platform}")
    
    # Single instance check
    lock = SingleInstanceLock("un-idle")
    if not lock.acquire():
        logger.info("Another instance already running, exiting silently")
        return 0
    
    try:
        cfg = load_config()
        logger.info(f"Config loaded: mode={cfg.mode}, enabled={cfg.enabled}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        cfg = AppConfig()
    
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
        
        # Always apply in memory first
        engine.update_config(normalized)
        tray.refresh_icon(active=normalized.enabled)
        
        # Then try to persist
        if not save_config(normalized):
            logger.error("Config changes applied in memory but persistence failed")
            # TODO: Show user notification about save failure

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
        logger.info("Quit requested")
        stop_event.set()

    try:
        engine = UnIdleEngine(get_cfg())
        logger.info("Engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        return 1
    
    try:
        tray = TrayController(
            get_config=get_cfg,
            on_save_config=apply_cfg,
            on_toggle_enabled=set_enabled,
            on_quit=on_quit,
        )
        logger.info("Tray controller initialized")
    except Exception as e:
        logger.error(f"Failed to initialize tray: {e}")
        return 1

    def _signal_handler(signum, frame):
        logger.info(f"Signal {signum} received")
        stop_event.set()
        tray._handle_quit()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _signal_handler)
        except Exception as e:
            logger.warning(f"Could not set signal handler for {sig}: {e}")

    engine.start()
    logger.info("Engine started, entering main loop")
    try:
        tray.run()
    finally:
        logger.info("Shutting down")
        engine.stop()
        lock.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
