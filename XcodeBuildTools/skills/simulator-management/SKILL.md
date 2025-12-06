---
name: simulator-management
description: Manage iOS Simulators - boot, shutdown, erase, configure location, appearance, and status bar. Use this skill when you need to control simulator state or settings.
---

# Simulator Management

Manage iOS Simulator lifecycle and settings.

## Prerequisites

- macOS with Xcode installed
- At least one iOS Simulator runtime installed

## Scripts

All scripts are in the `scripts/` directory and output JSON.

### boot-simulator.py

Boot an iOS Simulator.

```bash
# Boot by name (uses latest runtime)
scripts/boot-simulator.py --name "iPhone 15"

# Boot by UDID
scripts/boot-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Boot without opening Simulator.app window
scripts/boot-simulator.py --name "iPhone 15" --headless
```

### shutdown-simulator.py

Shutdown a simulator or all simulators.

```bash
# Shutdown specific simulator
scripts/shutdown-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Shutdown all simulators
scripts/shutdown-simulator.py --all
```

### open-simulator.py

Open the Simulator.app window for a booted simulator.

```bash
scripts/open-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Open and bring to front
scripts/open-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" --focus
```

### erase-simulator.py

Erase a simulator (reset to factory settings).

```bash
# Erase specific simulator
scripts/erase-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Erase all simulators
scripts/erase-simulator.py --all

# Erase all simulators of a specific runtime
scripts/erase-simulator.py --runtime "iOS 17"
```

### set-location.py

Set the simulated GPS location.

```bash
# Set to specific coordinates
scripts/set-location.py --udid <UDID> --latitude 37.7749 --longitude -122.4194

# Set to a named location
scripts/set-location.py --udid <UDID> --location "San Francisco"
```

**Common Locations:**
- San Francisco: `--latitude 37.7749 --longitude -122.4194`
- New York: `--latitude 40.7128 --longitude -74.0060`
- London: `--latitude 51.5074 --longitude -0.1278`
- Tokyo: `--latitude 35.6762 --longitude 139.6503`

### reset-location.py

Reset/clear the simulated GPS location.

```bash
scripts/reset-location.py --udid <UDID>
```

### set-appearance.py

Set the simulator appearance (light/dark mode).

```bash
scripts/set-appearance.py --udid <UDID> --mode dark
scripts/set-appearance.py --udid <UDID> --mode light
```

### set-statusbar.py

Override the simulator status bar display.

```bash
# Set a clean status bar for screenshots
scripts/set-statusbar.py --udid <UDID> --time "9:41" --battery 100 --wifi 3 --cellular 4

# Clear overrides
scripts/set-statusbar.py --udid <UDID> --clear
```

**Options:**
- `--time TIME`: Status bar time (e.g., "9:41")
- `--battery LEVEL`: Battery percentage (0-100)
- `--wifi BARS`: WiFi signal bars (0-3)
- `--cellular BARS`: Cellular signal bars (0-4)
- `--clear`: Remove all overrides

## Common Workflows

### Prepare Simulator for Testing
```bash
# 1. Boot simulator
scripts/boot-simulator.py --name "iPhone 15"

# 2. Set location
scripts/set-location.py --udid <UDID> --latitude 37.7749 --longitude -122.4194

# 3. Set appearance
scripts/set-appearance.py --udid <UDID> --mode light
```

### Prepare for Screenshots
```bash
# 1. Boot simulator
scripts/boot-simulator.py --name "iPhone 15 Pro Max"

# 2. Set clean status bar
scripts/set-statusbar.py --udid <UDID> --time "9:41" --battery 100 --wifi 3 --cellular 4

# 3. Take screenshot using simulator-build skill
```

### Clean Up
```bash
# Shutdown all simulators
scripts/shutdown-simulator.py --all

# Or erase all to reset to fresh state
scripts/erase-simulator.py --all
```
