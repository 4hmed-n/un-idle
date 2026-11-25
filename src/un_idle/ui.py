from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from PIL import Image, ImageDraw
import pystray

from capture_guard import apply_capture_exclusion, is_windows_capture_exclusion_supported
from config import AppConfig, VALID_MODES


def create_tray_icon_image(active: bool = True, size: int = 64) -> Image.Image:
    bg = (24, 24, 27, 255)
    accent = (34, 197, 94, 255) if active else (161, 161, 170, 255)
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)
    pad = max(4, size // 8)
    draw.ellipse([pad, pad, size - pad, size - pad], outline=accent, width=max(3, size // 12))
    inner = max(10, size // 3)
    draw.ellipse([inner, inner, size - inner, size - inner], fill=accent)
    return img


class SettingsWindow:
    def __init__(
        self,
        parent: tk.Misc | None,
        config: AppConfig,
        on_save: Callable[[AppConfig], None],
    ) -> None:
        self._on_save = on_save
        self._working = AppConfig(
            enabled=config.enabled,
            mode=config.mode,
            idle_threshold_sec=config.idle_threshold_sec,
            pulse_interval_sec=config.pulse_interval_sec,
            jiggle_pixels=config.jiggle_pixels,
            hide_from_capture=config.hide_from_capture,
            schedule=type(config.schedule)(
                enabled=config.schedule.enabled,
                start_time=config.schedule.start_time,
                end_time=config.schedule.end_time,
                days=list(config.schedule.days),
            ),
        ).normalized()

        self.win = tk.Toplevel(parent) if parent else tk.Tk()
        self.win.title("Un-Idle Settings")
        self.win.geometry("450x480")
        self.win.resizable(False, False)

        self.win.update()
        self._initial_capture_state = self._working.hide_from_capture
        apply_capture_exclusion(self.win, enabled=self._initial_capture_state)

        self._build_form()
    
    def _cancel(self) -> None:
        """Cancel and revert live capture exclusion change."""
        # Revert capture exclusion to initial state
        apply_capture_exclusion(self.win, enabled=self._initial_capture_state)
        self.win.destroy()

    def _build_form(self) -> None:
        pad = {"padx": 14, "pady": 6}

        self.enabled_var = tk.BooleanVar(value=self._working.enabled)
        ttk.Checkbutton(self.win, text="Enable Un-Idle", variable=self.enabled_var).pack(
            anchor="w", **pad
        )

        mode_frame = ttk.Frame(self.win)
        mode_frame.pack(fill="x", **pad)
        ttk.Label(mode_frame, text="Simulation Mode:").pack(side="left")
        self.mode_var = tk.StringVar(value=self._working.mode)
        ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=list(VALID_MODES),
            state="readonly",
            width=18,
        ).pack(side="right")

        idle_frame = ttk.Frame(self.win)
        idle_frame.pack(fill="x", **pad)
        ttk.Label(idle_frame, text="Idle Threshold (sec):").pack(side="left")
        self.idle_var = tk.StringVar(value=str(self._working.idle_threshold_sec))
        ttk.Entry(idle_frame, textvariable=self.idle_var, width=10).pack(side="right")

        pulse_frame = ttk.Frame(self.win)
        pulse_frame.pack(fill="x", **pad)
        ttk.Label(pulse_frame, text="Pulse Interval (sec):").pack(side="left")
        self.pulse_var = tk.StringVar(value=str(self._working.pulse_interval_sec))
        ttk.Entry(pulse_frame, textvariable=self.pulse_var, width=10).pack(side="right")

        jiggle_frame = ttk.Frame(self.win)
        jiggle_frame.pack(fill="x", **pad)
        ttk.Label(jiggle_frame, text="Jiggle Pixels:").pack(side="left")
        self.jiggle_var = tk.StringVar(value=str(self._working.jiggle_pixels))
        ttk.Entry(jiggle_frame, textvariable=self.jiggle_var, width=10).pack(side="right")

        sched_frame = ttk.LabelFrame(self.win, text="Active Schedule")
        sched_frame.pack(fill="x", padx=14, pady=6)
        self.sched_enabled_var = tk.BooleanVar(value=self._working.schedule.enabled)
        ttk.Checkbutton(
            sched_frame, text="Restrict to time window", variable=self.sched_enabled_var
        ).grid(row=0, column=0, columnspan=7, sticky="w", padx=8, pady=4)

        ttk.Label(sched_frame, text="Start (HH:MM):").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.start_var = tk.StringVar(value=self._working.schedule.start_time)
        ttk.Entry(sched_frame, textvariable=self.start_var, width=8).grid(row=1, column=1, columnspan=2, padx=4)

        ttk.Label(sched_frame, text="End (HH:MM):").grid(row=1, column=3, sticky="w", padx=8, pady=4)
        self.end_var = tk.StringVar(value=self._working.schedule.end_time)
        ttk.Entry(sched_frame, textvariable=self.end_var, width=8).grid(row=1, column=4, columnspan=2, padx=4)
        
        # Weekday checkboxes
        ttk.Label(sched_frame, text="Days:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.day_vars = []
        for i, day_name in enumerate(day_names):
            var = tk.BooleanVar(value=(i in self._working.schedule.days))
            self.day_vars.append(var)
            ttk.Checkbutton(sched_frame, text=day_name, variable=var).grid(
                row=2, column=i+1, padx=2, pady=4
            )

        self.capture_var = tk.BooleanVar(value=self._working.hide_from_capture)
        capture_cb = ttk.Checkbutton(
            self.win,
            text="Exclude window from Windows screen capture (WDA_EXCLUDEFROMCAPTURE)",
            variable=self.capture_var,
            command=self._on_capture_toggle,
        )
        capture_cb.pack(anchor="w", **pad)
        if not is_windows_capture_exclusion_supported():
            capture_cb.state(["disabled"])

        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=14, pady=12)
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self._cancel).pack(side="right", padx=4)

    def _on_capture_toggle(self) -> None:
        apply_capture_exclusion(self.win, enabled=bool(self.capture_var.get()))

    def _save(self) -> None:
        try:
            idle_val = float(self.idle_var.get())
        except ValueError:
            idle_val = self._working.idle_threshold_sec

        try:
            pulse_val = float(self.pulse_var.get())
        except ValueError:
            pulse_val = self._working.pulse_interval_sec

        try:
            jiggle_val = int(self.jiggle_var.get())
        except ValueError:
            jiggle_val = self._working.jiggle_pixels
        
        # Collect selected weekdays from checkboxes
        selected_days = [i for i, var in enumerate(self.day_vars) if var.get()]
        if not selected_days:
            selected_days = [0, 1, 2, 3, 4]  # Default to Mon-Fri

        updated = AppConfig(
            enabled=bool(self.enabled_var.get()),
            mode=self.mode_var.get(),
            idle_threshold_sec=idle_val,
            pulse_interval_sec=pulse_val,
            jiggle_pixels=jiggle_val,
            hide_from_capture=bool(self.capture_var.get()),
            schedule=type(self._working.schedule)(
                enabled=bool(self.sched_enabled_var.get()),
                start_time=self.start_var.get().strip() or "09:00",
                end_time=self.end_var.get().strip() or "18:00",
                days=selected_days,
            ),
        ).normalized()

        apply_capture_exclusion(self.win, enabled=updated.hide_from_capture)
        self._on_save(updated)
        self.win.destroy()


class TrayController:
    """Manages system tray icon and opens Tkinter settings windows on the UI thread."""

    def __init__(
        self,
        get_config: Callable[[], AppConfig],
        on_save_config: Callable[[AppConfig], None],
        on_toggle_enabled: Callable[[bool], None],
        on_quit: Callable[[], None],
        engine=None,  # UnIdleEngine instance for pause features
    ) -> None:
        self._get_config = get_config
        self._on_save_config = on_save_config
        self._on_toggle_enabled = on_toggle_enabled
        self._on_quit = on_quit
        self._engine = engine
        self._tk_root: Optional[tk.Tk] = None
        self._settings_win: Optional[SettingsWindow] = None
        self._icon: Optional[pystray.Icon] = None
        self._ready = threading.Event()
        self._tk_thread = threading.Thread(target=self._run_tk_loop, name="UnIdleUI", daemon=True)

    def _run_tk_loop(self) -> None:
        root = tk.Tk()
        root.withdraw()
        apply_capture_exclusion(root, enabled=self._get_config().hide_from_capture)
        self._tk_root = root
        self._ready.set()
        root.mainloop()

    def _open_settings_on_ui_thread(self) -> None:
        if self._tk_root is None:
            return
        if self._settings_win is not None:
            try:
                if self._settings_win.win.winfo_exists():
                    self._settings_win.win.lift()
                    apply_capture_exclusion(
                        self._settings_win.win, enabled=self._get_config().hide_from_capture
                    )
                    return
            except Exception:
                pass
        self._settings_win = SettingsWindow(
            self._tk_root,
            self._get_config(),
            self._on_save_config,
        )

    def request_open_settings(self, icon=None, item=None) -> None:
        self._ready.wait(timeout=3.0)
        if self._tk_root is not None:
            try:
                self._tk_root.after(0, self._open_settings_on_ui_thread)
            except Exception:
                pass

    def _toggle_enabled(self, icon=None, item=None) -> None:
        cfg = self._get_config()
        next_enabled = not cfg.enabled
        self._on_toggle_enabled(next_enabled)
        self.refresh_icon(active=next_enabled)

    def refresh_icon(self, active: Optional[bool] = None) -> None:
        if self._icon is None:
            return
        is_act = self._get_config().enabled if active is None else bool(active)
        try:
            self._icon.icon = create_tray_icon_image(active=is_act)
        except Exception:
            pass

    def _handle_quit(self, icon=None, item=None) -> None:
        if self._tk_root is not None:
            try:
                self._tk_root.after(0, self._tk_root.quit)
            except Exception:
                pass
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
        self._on_quit()

    def _pause_30min(self, icon=None, item=None) -> None:
        if self._engine:
            self._engine.pause_for_duration(30)
    
    def _pause_1hour(self, icon=None, item=None) -> None:
        if self._engine:
            self._engine.pause_for_duration(60)
    
    def _pause_until_tomorrow(self, icon=None, item=None) -> None:
        if self._engine:
            self._engine.pause_until_tomorrow()

    def run(self) -> None:
        self._tk_thread.start()
        self._ready.wait(timeout=3.0)
        cfg = self._get_config()
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: "Enabled" if self._get_config().enabled else "Paused",
                self._toggle_enabled,
                checked=lambda item: self._get_config().enabled,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Pause 30 min", self._pause_30min),
            pystray.MenuItem("Pause 1 hour", self._pause_1hour),
            pystray.MenuItem("Pause until tomorrow", self._pause_until_tomorrow),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings...", self.request_open_settings, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._handle_quit),
        )
        self._icon = pystray.Icon(
            "un-idle",
            create_tray_icon_image(active=cfg.enabled),
            "Un-Idle",
            menu,
        )
        self._icon.run()
