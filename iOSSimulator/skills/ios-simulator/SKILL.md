---
name: ios-simulator
version: 1.0.0
description: This skill should be used when the user asks to "control an iOS Simulator", "automate iOS Simulator UI", "take a simulator screenshot", "boot a simulator", "interact with a simulator", "send push notifications to simulator", "manage simulator permissions", "record simulator video", "visual regression test", or any task involving iOS Simulator management, UI automation, or testing through scripted commands.
---

# iOS Simulator Control

Control iOS Simulators using native macOS tools. No additional dependencies required beyond Xcode Command Line Tools.

## Prerequisites

- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3 (pre-installed on macOS)

## Running the Scripts

- All scripts are executable with proper shebang lines (no `python3` prefix needed)
- All scripts are in the `scripts/` directory and output JSON
- All scripts accept `--udid` to target a specific simulator (defaults to booted)
- Run any script with `--help` for full argument documentation

## Quick Start Workflow

```bash
# 1. List available simulators
scripts/sim-list.py

# 2. Boot a simulator
scripts/sim-boot.py --name "iPhone 15"

# 3. Take a screenshot (view with Read tool to see UI)
scripts/sim-screenshot.py --output /tmp/screen.png

# 4. Tap at coordinates identified from the screenshot
scripts/sim-tap.py --x 200 --y 400

# 5. Type text into a focused field
scripts/sim-type.py --text "Hello, World!"
```

### Alternative: Find Elements by Text

Instead of guessing coordinates from screenshots, find elements programmatically:

```bash
# Find a button by label and get its center coordinates
scripts/sim-describe-ui.py --find-text "Login" --find-type AXButton --index 0

# Tap using the center coordinates from the result
scripts/sim-tap.py --x 195 --y 422
```

## Choosing a Simulator

When a specific simulator is requested, use `scripts/sim-list.py` to find and boot it.

When no simulator is specified, follow this logic:
- If one or more simulators are booted, use the most recent model with the latest OS
- If none are booted, boot the most recent model with the latest OS

## Script Reference

All scripts are in `scripts/` and output JSON. For detailed usage with all options and examples, consult **`references/script-details.md`**.

### Simulator Management

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-list.py` | List simulators | `--booted` for running only |
| `sim-boot.py` | Boot a simulator | `--name "iPhone 15"` |
| `sim-shutdown.py` | Shutdown simulator(s) | `--all` for all |
| `sim-create.py` | Create new simulator | `--device "iPhone 15 Pro"` |
| `sim-delete.py` | Delete simulator | `--udid <udid>` or `--unavailable` |
| `sim-erase.py` | Factory reset (keeps UUID) | `--name "iPhone 15"` |

### App Management

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-launch.py` | Launch app | `--bundle-id com.apple.Preferences` |
| `sim-terminate.py` | Terminate app | `--bundle-id <id>` |
| `sim-install.py` | Install .app/.ipa | `--app /path/to/MyApp.app` |

### Screenshots & Recording

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-screenshot.py` | Capture screen | `--output /tmp/screen.png` |
| `sim-record-video.py` | Record video | `--output /tmp/demo.mp4 --duration 30` |

After taking a screenshot, use the Read tool to view the image and identify coordinates.

### UI Inspection

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-describe-ui.py` | Accessibility tree / find elements | `--find-text "Login"` |
| `sim-screen-map.py` | Token-efficient screen overview | `--verbose --hints` |

`sim-describe-ui.py` requires `uv` for dependency management.

### UI Automation

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-tap.py` | Tap at coordinates | `--x 200 --y 400` |
| `sim-type.py` | Type text | `--text "Hello"` or `--clear --text "new"` |
| `sim-swipe.py` | Swipe / long-press / drag | `--up`, `--long-press --x 200 --y 400` |
| `sim-home.py` | Press Home button | (no args) |
| `sim-shake.py` | Shake gesture | (no args) |
| `sim-keyboard.py` | Shortcuts / combos / hardware | `--combo cmd+a`, `--clear`, `volume-up` |

### System Features

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-openurl.py` | Open URL / deep link | `--url "https://apple.com"` |
| `sim-location.py` | Set GPS location | `--lat 37.7749 --lon -122.4194` |
| `sim-appearance.py` | Light/dark mode | `dark` or `light` |
| `sim-statusbar.py` | Override status bar | `--time "9:41" --battery 100` |
| `sim-device-info.py` | Device details & screen size | (no args) |
| `sim-clipboard.py` | Clipboard get/set | `--set "text"` or `--get` |

### Privacy, Notifications & Logs

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-privacy.py` | App permissions | `--grant camera --bundle-id <id>` |
| `sim-push.py` | Push notifications | `--bundle-id <id> --title "Hi" --body "..."` |
| `sim-logs.py` | Stream/filter logs | `--bundle-id <id> --duration 10s` |

### Testing & Analysis

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-visual-diff.py` | Screenshot comparison | `baseline.png current.png --threshold 1.0` |

## Coordinate System

iOS uses a **point-based** coordinate system independent of screen resolution:

- **Points**: Logical coordinates used by `sim-tap.py`, `sim-swipe.py`, `sim-describe-ui.py`
- **Pixels**: Physical screen pixels in screenshots
- **Scale Factor**: Multiplier (1x, 2x, 3x Retina). `pixels = points x scale`
- **Origin**: (0, 0) is the top-left corner; X increases right, Y increases down

To convert screenshot pixel coordinates to tap coordinates, divide by the scale factor from `sim-screenshot.py` output (`screen.scale`).

## Additional Resources

### Reference Files

For detailed documentation, consult:
- **`references/script-details.md`** — Full per-script documentation with all options and examples
- **`references/json-schemas.md`** — JSON output schemas for every script, error categories
- **`references/troubleshooting.md`** — Common issues and solutions
