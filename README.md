# Un-Idle

A lightweight Python desktop utility that prevents unwanted system sleep, screen locks, and chat/collaboration app idle statuses. Features idle-aware detection, configurable simulation modes, active schedules, system tray controls, and optional Windows screen-capture exclusion.

## Download

**[Download the latest release](https://github.com/4hmed-n/un-idle/releases)** — Windows executable available

After launching, check your system tray (click the `^` arrow near the clock) for the Un-Idle icon.

## Features

- **Idle-Aware Detection** — Reads native OS idle timers with pynput fallback
- **Simulation Modes:**
  - `micro-jiggle` — Moves cursor by small pixel offset and returns
  - `f15` — Emits F15 key tap (minimal conflict with existing shortcuts)
  - `awake_only` — OS power assertions without synthetic input
- **Schedule Windows** — Restrict activity to specific days/times (supports overnight ranges)
- **Pause Timers** — Temporarily pause for 30 min, 1 hour, or until tomorrow
- **Presets** — Quick configurations for Reading, Presentation, Download
- **System Tray** — Runs in background with settings dialog
- **Windows Capture Exclusion** — Hides UI from screen capture/sharing apps (Windows 10 v2004+, build 19041+)

## Capability Matrix

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| Idle Detection | ✅ Tested | ⚠️ Untested | ⚠️ Untested |
| Mouse Jiggle | ✅ Tested | ⚠️ Untested | ⚠️ X11 only |
| Key Pulse (F15) | ✅ Tested | ⚠️ Untested | ⚠️ X11 only |
| Power Assertion (`awake_only`) | ✅ Tested | ⚠️ Untested | ❌ Unavailable |
| Capture Exclusion | ✅ Build 19041+ | ❌ N/A | ❌ N/A |
| Schedule Windows | ✅ Tested | ⚠️ Untested | ⚠️ Untested |
| System Tray | ✅ Tested | ⚠️ Untested | ⚠️ X11 only |
| Start at Login | ✅ Tested | ❌ Not implemented | ❌ Not implemented |

**Legend:**
- ✅ Tested and working
- ⚠️ Should work but untested
- ❌ Not available/implemented

**Note:** Windows is the primary tested platform. macOS and Linux support is best-effort based on capability detection.

## Limitations

**What Un-Idle Does NOT Do:**
- **Policy-Enforced Locking:** Cannot prevent system locks enforced by Group Policy, MDM, or corporate security policies
- **Server-Side Presence:** Does not affect presence status determined server-side by collaboration apps (Teams, Slack, etc.)
- **Hardware/Firmware Locks:** Cannot bypass BIOS/UEFI idle timers or hardware-level sleep modes
- **Screen Capture Detection:** Capture exclusion only hides the UI window pixels; it does not prevent:
  - Process enumeration (Task Manager, `ps`, etc.)
  - Window handle detection (`EnumWindows`)
  - Hardware capture devices (cameras pointed at screen)
  - Detection of synthetic input events by monitoring software

**Wayland Limitations (Linux):**
- Mouse jiggle may not work reliably
- Screen capture exclusion unavailable
- Use X11 for best compatibility

## Responsible Use

**Follow your workplace and device policies.** This tool is designed for personal convenience (reading long documents, watching training videos, preventing interruptions during focused work), not for circumventing security policies or misrepresenting your availability.

If your employer, school, or device owner has policies about idle detection or activity monitoring, **respect those policies**. Violating such policies can have serious consequences.

## Run From Source

1. Create virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   pip install -r requirements.txt
   
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run:
   ```bash
   # Windows:
   scripts\run.bat
   
   # macOS/Linux:
   ./scripts/run.sh
   ```

## Build Executable

```bash
pip install -r requirements-dev.txt
pyinstaller --clean --noconfirm un-idle.spec
```

Output: `dist/un-idle.exe` (Windows) or `dist/un-idle` (macOS/Linux)

## Configuration

Config location:
- **Windows:** `%LOCALAPPDATA%\un-idle\config.json`
- **macOS:** `~/Library/Application Support/un-idle/config.json`
- **Linux:** `$XDG_CONFIG_HOME/un-idle/config.json` or `~/.config/un-idle/config.json`

Logs location:
- **Windows:** `%LOCALAPPDATA%\un-idle\app.log`
- **macOS:** `~/Library/Logs/un-idle/app.log`
- **Linux:** `$XDG_STATE_HOME/un-idle/app.log` or `~/.local/state/un-idle/app.log`

## License

See [LICENSE](LICENSE) for details.
