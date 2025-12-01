# iOSSimulator Plugin

Control iOS Simulators using native macOS tools. No additional dependencies required beyond Xcode.

## Features

- **Simulator Management**: List, boot, shutdown simulators
- **App Control**: Install, launch, terminate apps
- **Screenshots**: Capture simulator screen (viewable by Claude!)
- **UI Inspection**: Describe UI elements with accessibility info
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
| `sim-boot.py` | Boot a simulator |
| `sim-shutdown.py` | Shutdown simulator(s) |
| `sim-screenshot.py` | Take a screenshot |
| `sim-describe-ui.py` | Get UI element accessibility info |
| `sim-launch.py` | Launch an app |
| `sim-terminate.py` | Terminate an app |
| `sim-install.py` | Install an app |
| `sim-tap.py` | Tap at screen coordinates |
| `sim-type.py` | Type text |
| `sim-swipe.py` | Swipe gesture |
| `sim-home.py` | Press Home button |
| `sim-shake.py` | Simulate shake gesture |
| `sim-keyboard.py` | Send keyboard shortcuts |
| `sim-openurl.py` | Open URL/deep link |
| `sim-location.py` | Set GPS location |
| `sim-appearance.py` | Set dark/light mode |

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

## License

MIT
