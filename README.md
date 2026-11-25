# Un-Idle

A lightweight Python desktop utility that prevents unwanted system sleep, screen locks, and chat/collaboration app idle statuses. Features idle-aware detection, configurable simulation modes, active schedules, system tray controls, and optional Windows screen-capture exclusion.

## Features

- **Idle-Aware Detection** — Reads native OS idle timers (`GetLastInputInfo` on Windows, `IOHIDSystem` on macOS, `xprintidle` on Linux) with `pynput` fallback
- **Simulation Modes:**
  - `micro-jiggle` — Moves cursor by small pixel offset and returns
  - `f15` — Emits F15 key tap (minimal conflict with existing shortcuts)
  - `awake_only` — OS power assertions without synthetic input
- **Schedule Windows** — Restrict activity to specific days/times (supports overnight ranges)
- **System Tray** — Runs in background with tray icon and settings dialog
- **Windows Capture Exclusion** — Hides UI from screen capture/sharing apps (Windows 10 v2004+, build 19041+)

## Download

**[Download the latest release](https://github.com/4hmed-n/un-idle/releases)** — Windows executable available

After launching, check your system tray (click the `^` arrow near the clock) for the Un-Idle icon.

## Run From Source

1. Create virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run:
   - Windows: `scripts\run.bat`
   - macOS/Linux: `./scripts/run.sh`

3. Run tests:
   ```bash
   # Windows:
   set PYTHONPATH=src\un_idle
   pytest -v
   
   # macOS/Linux:
   PYTHONPATH=src/un_idle pytest -v
   ```

## Build Executable

```bash
pyinstaller --clean --noconfirm un-idle.spec
```

Output: `dist/un-idle.exe`

## License

See [LICENSE](LICENSE) for details.
