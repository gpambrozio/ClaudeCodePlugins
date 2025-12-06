---
name: simulator-build
description: Build, run, install, and test iOS apps on iOS Simulators. Use this skill when building for simulator, running tests, or deploying to a simulator.
---

# Simulator Build

Build, run, and test iOS apps on iOS Simulators.

## Prerequisites

- macOS with Xcode installed
- At least one iOS Simulator runtime installed

## Scripts

All scripts are in the `scripts/` directory and output JSON.

### list-simulators.py

List available iOS simulators.

```bash
# List all simulators
scripts/list-simulators.py

# List only booted simulators
scripts/list-simulators.py --booted

# Filter by runtime
scripts/list-simulators.py --runtime "iOS 17"
```

Output:
```json
{
  "success": true,
  "simulators": [
    {
      "name": "iPhone 15 Pro",
      "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
      "state": "Booted",
      "runtime": "iOS 17.0",
      "is_available": true
    }
  ]
}
```

### build-simulator.py

Build an Xcode project/workspace for the iOS Simulator.

```bash
# Build with workspace
scripts/build-simulator.py --workspace MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15"

# Build with project and specific simulator UDID
scripts/build-simulator.py --project MyApp.xcodeproj --scheme MyApp --simulator-id <UDID>

# Use latest OS version
scripts/build-simulator.py --workspace MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15" --use-latest-os

# Release configuration
scripts/build-simulator.py --workspace MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15" --configuration Release
```

**Parameters:**
- `--workspace` or `--project`: Path to .xcworkspace or .xcodeproj (mutually exclusive, required)
- `--scheme`: Build scheme name (required)
- `--simulator-name` or `--simulator-id`: Simulator name or UDID (one required)
- `--configuration`: Build configuration (default: Debug)
- `--use-latest-os`: Use latest OS version for simulator name
- `--derived-data`: Custom derived data path
- `--extra-args`: Additional xcodebuild arguments

### build-run-simulator.py

Build and immediately run an app on a simulator.

```bash
scripts/build-run-simulator.py --workspace MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15"
```

This combines building, installing, and launching in one step.

### install-app-simulator.py

Install an app on a simulator.

```bash
scripts/install-app-simulator.py --simulator-id <UDID> --app /path/to/MyApp.app
```

### launch-app-simulator.py

Launch an installed app on a simulator.

```bash
scripts/launch-app-simulator.py --simulator-id <UDID> --bundle-id com.example.myapp

# Launch with console output
scripts/launch-app-simulator.py --simulator-id <UDID> --bundle-id com.example.myapp --console
```

### stop-app-simulator.py

Terminate a running app on a simulator.

```bash
scripts/stop-app-simulator.py --simulator-id <UDID> --bundle-id com.example.myapp
```

### test-simulator.py

Run tests on a simulator.

```bash
# Run all tests
scripts/test-simulator.py --workspace MyApp.xcworkspace --scheme MyAppTests --simulator-name "iPhone 15"

# Run specific tests
scripts/test-simulator.py --workspace MyApp.xcworkspace --scheme MyAppTests --simulator-name "iPhone 15" --only-testing "MyAppTests/LoginTests"
```

### screenshot.py

Take a screenshot of a simulator.

```bash
scripts/screenshot.py --simulator-id <UDID> --output /tmp/screenshot.png

# Auto-generated filename
scripts/screenshot.py --simulator-id <UDID>
```

### record-video.py

Record video of a simulator.

```bash
# Start recording
scripts/record-video.py --simulator-id <UDID> --output /tmp/recording.mp4 --start

# Stop recording
scripts/record-video.py --stop
```

## Choosing a Simulator

When choosing a simulator:

1. Use `list-simulators.py --booted` to see running simulators
2. If none are booted, use the simulator-management skill to boot one
3. Use `--simulator-name` for convenience or `--simulator-id` for precision
4. Use `--use-latest-os` to get the newest OS version for a device name

## Typical Workflow

```bash
# 1. List available simulators
scripts/list-simulators.py

# 2. Build and run (will boot simulator if needed)
scripts/build-run-simulator.py --workspace MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15"

# 3. Take a screenshot
scripts/screenshot.py

# 4. Run tests
scripts/test-simulator.py --workspace MyApp.xcworkspace --scheme MyAppTests --simulator-name "iPhone 15"
```
