# J.A.R.V.I.S. — Personal Hybrid Assistant

> Offline-first, multi-modal assistant with voice + gesture input and a strict safety policy.

---

## Requirements

- Python 3.11+
- Windows 10/11 (primary target; macOS / Linux supported for most actions)

---

## Installation

```bash
# Clone the repo
git clone https://github.com/JatinDhimanx/jarvis.git
cd jarvis

# Install the package in editable mode (includes dev/test dependencies)
pip install -e ".[dev]"
```

This installs only the `jarvis/` Python package. The `brain/` folder (spec docs) and `config/` folder (default YAML) are not packaged as Python code.

---

## Running JARVIS

### Quick start (safe simulation mode)

```bash
python run.py --skip-diagnostics
```

This starts JARVIS in **VIRTUAL mode** — all actions (open app, set volume, etc.) are simulated in-memory. Nothing touches your actual OS. Safe for demos and development.

### With the Web HUD

```bash
python run.py
```

Opens the **Tactical Web HUD** at [http://127.0.0.1:8080/](http://127.0.0.1:8080/) automatically. Type commands in the input bar and see live responses.

### Run without opening browser

```bash
python run.py --no-browser
```

---

## Execution Modes

JARVIS has two backend modes, always printed in the startup banner:

| Flag | Mode | What it does |
|------|------|-------------|
| *(default)* | **VIRTUAL** | Simulates all actions in-memory. Safe for demos, CI, and development. |
| `--virtual` | **VIRTUAL** | Explicit virtual mode (same as default). |
| `--real` | **REAL** | Actually executes OS-level actions: launches apps via `subprocess`, changes volume, locks screen via `ctypes`, etc. |

```bash
# Simulation mode (default — nothing touches the OS)
python run.py --virtual

# Real mode — actually opens Notepad, changes volume, locks screen
python run.py --real
```

> **⚠️ Warning:** In `--real` mode, commands like `shutdown`, `lock screen`, and `close app` will **actually execute** on your system. HIGH-risk actions (e.g. `shutdown`) still require explicit confirmation per the safety policy.

---

## CLI Options

```
python run.py [OPTIONS]

Options:
  --host TEXT         HUD server host (default: 127.0.0.1)
  --port INT          HUD server port (default: 8080)
  --no-browser        Don't open the browser HUD automatically
  --skip-diagnostics  Skip pre-flight environment checks
  --minimized         Run in daemon/background mode
  --real              Use real OS backends (live execution)
  --virtual           Use virtual/simulation backends (default, safe)
```

---

## Example Commands

Once JARVIS is running, type at the `[IDLE] JARVIS>` prompt or use the Web HUD:

```
open notepad          → Launches Notepad (real mode) / simulates (virtual)
close notepad         → Closes Notepad via taskkill
set volume 75         → Sets system audio volume to 75%
set brightness 80     → Sets display brightness to 80%
lock screen           → Locks the Windows workstation
open calculator       → Opens Calculator
```

Special commands:

```
confirm               → Authorize a pending HIGH-risk action
reject                → Cancel a pending action
stop                  → Emergency stop — cancels all in-flight actions
exit / quit           → Shut down JARVIS gracefully
```

---

## Running Tests

```bash
# All tests (virtual backends — safe, no OS side-effects)
python -m pytest

# Just the real backend tests
python -m pytest tests/test_real_system_backend.py -v
```

Expected result: **167 passed, 2 skipped** (skipped = platform-specific paths not applicable on current OS).

---

## Project Structure

```
jarvis/
├── core/           State machine, config, logging, errors
├── router/         Intent detection and command routing
├── policy/         Safety policy and risk gating (11_SAFETY_AND_PERMISSIONS.md)
├── execution/
│   ├── action_engine.py
│   └── actions/    Tool implementations (system, application, browser, files, …)
├── perception/     Voice STT/TTS, gesture engine (lazy cv2/mediapipe imports)
├── brain_layer/    Context manager, planner, hybrid brain
├── memory/         Persistent memory store and workflows
├── registry/       Tool registry (ToolDeclaration, ToolRegistry)
├── response/       Response formatter
├── ui/             Tactical Web HUD (HTTP server + static files)
└── packaging/      Installer validator, crash recovery, settings manager

brain/              Binding design spec (Markdown — not Python code)
config/             Default configuration YAML
tests/              130+ unit tests
run.py              Master entry point
pyproject.toml      Package metadata + dependencies
```

---

## Architecture

See [`brain/01_SYSTEM_ARCHITECTURE.md`](brain/01_SYSTEM_ARCHITECTURE.md) for the full system design.

Key design decisions:
- **Virtual-by-default**: Real OS execution is opt-in via `--real` to prevent accidental side-effects.
- **Safety policy first**: All HIGH-risk actions (shutdown, delete file, etc.) require explicit user confirmation before execution, in both Virtual and Real mode.
- **Truthful verification**: Actions report `[VERIFIED: OK]` only after a real post-condition check, not just because the command was issued.
- **Offline-first**: The core pipeline works entirely without network access.
