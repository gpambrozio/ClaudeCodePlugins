# XcodeBuildSkills

Comprehensive Xcode development skills for Claude Code, reimplementing tools from [XcodeBuildMCP](https://github.com/cameroncooke/XcodeBuildMCP) as executable Python scripts.

## Installation

```bash
# Add the marketplace
/plugin marketplace add gpambrozio/ClaudeCodePlugins

# Install the plugin
/plugin install XcodeBuildSkills@ClaudeCodePlugins
```

## Skills Overview

This plugin provides 27 skills organized into categories:

### Swift Package Management

| Skill | Description |
|-------|-------------|
| `swift-package-build` | Build Swift packages with `swift build` |
| `swift-package-test` | Run tests with `swift test` |
| `swift-package-run` | Run executables with `swift run` |
| `swift-package-clean` | Clean build artifacts |
| `swift-package-list` | List running Swift package processes |
| `swift-package-stop` | Stop running processes |

### Project Discovery

| Skill | Description |
|-------|-------------|
| `discover-projects` | Find .xcodeproj and .xcworkspace files |
| `list-schemes` | List available Xcode schemes |
| `show-build-settings` | Display xcodebuild settings |
| `get-bundle-id` | Extract bundle identifier from apps |

### Device Management

| Skill | Description |
|-------|-------------|
| `list-devices` | List connected physical Apple devices |
| `install-app-device` | Install apps on physical devices |
| `launch-app-device` | Launch apps on devices |
| `stop-app-device` | Stop apps on devices |

### Simulator Management

| Skill | Description |
|-------|-------------|
| `erase-simulator` | Factory reset a simulator |
| `record-sim-video` | Record video from simulator |
| `sim-statusbar` | Override status bar for screenshots |
| `start-sim-log` | Start capturing simulator logs |
| `stop-sim-log` | Stop log capture |

### macOS App Management

| Skill | Description |
|-------|-------------|
| `launch-mac-app` | Launch macOS applications |
| `stop-mac-app` | Terminate macOS applications |

### Xcodebuild Wrappers

| Skill | Description |
|-------|-------------|
| `xcodebuild-sim` | Build for iOS/tvOS/watchOS simulator |
| `xcodebuild-device` | Build for physical devices |
| `xcodebuild-macos` | Build macOS applications |
| `xcode-test` | Run unit and UI tests |
| `xcodebuild-clean` | Clean build products |

### Utilities

| Skill | Description |
|-------|-------------|
| `xcode-doctor` | Diagnose Xcode development environment |

## Usage

Each skill is implemented as an executable Python script in the `scripts/` directory of its skill folder. All scripts:

- Have proper shebangs (`#!/usr/bin/env python3`)
- Are directly executable without `python` prefix
- Output JSON for structured parsing
- Include `--help` for usage information

### Example: Diagnose Environment

```bash
skills/xcode-doctor/scripts/xcode-doctor.py
```

Output:
```json
{
  "success": true,
  "xcode": {"installed": true, "version": "15.0"},
  "swift": {"version": "5.9", "installed": true},
  "simulators": {"total": 25, "booted": 1},
  "health": "good"
}
```

### Example: Build Swift Package

```bash
skills/swift-package-build/scripts/swift-package-build.py \
  --package-path /path/to/MyPackage \
  --configuration release
```

### Example: List Devices

```bash
skills/list-devices/scripts/list-devices.py
```

## Requirements

- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3 (pre-installed on macOS)

## Relationship to Other Plugins

This plugin complements:

- **iOSSimulator** - Provides basic simulator control and UI automation
- **SwiftDevelopment** - Provides swift-compile skill with xcsift integration

XcodeBuildSkills adds additional capabilities like device management, log capture, video recording, and comprehensive xcodebuild wrappers.

## License

MIT
