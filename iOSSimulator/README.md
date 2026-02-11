# iOSSimulator Plugin

Control iOS Simulators using native macOS tools. No additional dependencies required beyond Xcode.

## Features

- **Simulator Management**: List, boot, shutdown simulators
- **App Control**: Install, launch, terminate apps
- **Screenshots & Recording**: Capture screenshots and record video
- **UI Automation**: Tap, swipe, type text, shake
- **System Features**: Set location, appearance (dark/light), open URLs

## Installation

```bash
# Add the marketplace
/plugin marketplace add gpambrozio/ClaudeCodePlugins

# Install this plugin
/plugin install iOSSimulator@ClaudeCodePlugins
```

## Prerequisites

- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3 (pre-installed on macOS)
- [uv](https://docs.astral.sh/uv/) (optional, for `sim-describe-ui.py`)

## Quick Start

```bash
# List available simulators
python3 scripts/sim-list.py

# Boot iPhone 15 simulator
python3 scripts/sim-boot.py --name "iPhone 15"

# Take a screenshot
python3 scripts/sim-screenshot.py --output /tmp/screen.png

# Tap at coordinates
python3 scripts/sim-tap.py --x 200 --y 400

# Type text
python3 scripts/sim-type.py --text "Hello!"
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `sim-list.py` | List available simulators |
| `sim-boot.py` | Boot a simulator (with readiness verification) |
| `sim-shutdown.py` | Shutdown simulator(s) |
| `sim-create.py` | Create new simulator devices |
| `sim-delete.py` | Delete simulator devices |
| `sim-erase.py` | Factory reset (preserves UUID) |
| `sim-screenshot.py` | Take a screenshot |
| `sim-record-video.py` | Record simulator screen video |
| `sim-describe-ui.py` | UI hierarchy + element finding (requires uv) |
| `sim-screen-map.py` | Token-efficient screen overview |
| `sim-launch.py` | Launch an app |
| `sim-terminate.py` | Terminate an app |
| `sim-install.py` | Install an app |
| `sim-tap.py` | Tap at screen coordinates |
| `sim-type.py` | Type text (with --clear support) |
| `sim-swipe.py` | Swipe, long-press, drag, pull-to-refresh |
| `sim-home.py` | Press Home button |
| `sim-shake.py` | Simulate shake gesture |
| `sim-keyboard.py` | Shortcuts, combos, hardware buttons |
| `sim-openurl.py` | Open URL/deep link |
| `sim-location.py` | Set GPS location |
| `sim-appearance.py` | Set dark/light mode |
| `sim-statusbar.py` | Override status bar for screenshots |
| `sim-clipboard.py` | Clipboard get/set |
| `sim-privacy.py` | App permission management |
| `sim-push.py` | Send push notifications |
| `sim-logs.py` | Stream and filter logs |
| `sim-visual-diff.py` | Screenshot comparison (requires Pillow) |
| `sim-device-info.py` | Device details and screen dimensions |

## How It Works

This plugin uses native macOS tools:
- `xcrun simctl` - Apple's official simulator control CLI
- `Quartz` (Python) - For sending mouse/keyboard events
- `osascript` - AppleScript for System Events

No additional dependencies like `idb` are required.

## Screenshot-Based UI Automation

Claude can view screenshots! The recommended workflow:

1. Take a screenshot with `sim-screenshot.py`
2. Claude views the image to understand the UI
3. Claude identifies element positions visually
4. Use `sim-tap.py` to interact at those coordinates
5. Repeat for complex workflows

## Changelog

### 0.5.0
- **10 new scripts:** sim-create, sim-delete, sim-erase, sim-privacy, sim-push, sim-logs, sim-clipboard, sim-visual-diff, sim-screen-map, sim-describe-ui element finding
- **Improved sim-boot:** readiness verification with --no-wait and --timeout
- **Improved sim-swipe:** long-press, pull-to-refresh, drag gestures, auto screen size detection
- **Improved sim-keyboard:** --clear, --dismiss, --combo for key combinations, hardware buttons (volume, ringer)
- **Improved sim-type:** --clear to clear text before typing
- **Restructured SKILL.md:** progressive disclosure with references/ directory for detailed docs and JSON schemas

### 0.4.7
- Improved skill matching to support `PluginName:skill` prefix format in addition to skills array

### 0.4.6
- Added skills array to info.json; improved skill matching in pre-tool-use hook

### 0.4.5
- Improved skill/bash command matching in common infrastructure (using `in` instead of `startswith`)

### 0.4.4
- Added `not_match` exclusion to allow `xcrun simctl list devices` without triggering deny rule

### 0.4.3
- Updated pre-tool-use hook with configurable rules support (allow/deny/deny_once)

### 0.4.2
- Version tracker now silently initializes on first run instead of showing entire version history

### 0.4.1
- Fixed hooks path to use plugin-local common directory (plugins cannot reference external files)

### 0.4.0
- Centralized hooks to common/hooks.json
- Made session-start.py and pre-tool-use.py self-configuring from plugin.json

### 0.3.0
- Added version tracking with automatic changelog notifications on plugin updates
- Refactored session hooks to use shared infrastructure

### 0.2.0
- Added `sim-record-video.py` for recording simulator screen video
- Added `sim-statusbar.py` for overriding status bar (perfect for App Store screenshots with "9:41" time)

### 0.1.0
- Initial release with simulator control, screenshots, and UI automation

## License

MIT
