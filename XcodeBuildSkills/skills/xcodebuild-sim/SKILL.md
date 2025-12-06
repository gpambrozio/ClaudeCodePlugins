---
name: xcodebuild-sim
description: Build an iOS/tvOS/watchOS app for the simulator using xcodebuild. Supports projects and workspaces with configurable simulator destination.
---

# Build for Simulator

Build an app for iOS/tvOS/watchOS simulator.

## Usage

```bash
# With simulator ID
scripts/xcodebuild-sim.py --project ./MyApp.xcodeproj --scheme MyApp --simulator-id UDID

# With simulator name
scripts/xcodebuild-sim.py --workspace ./MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15"
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | One required | Path to .xcodeproj file |
| `--workspace` | One required | Path to .xcworkspace file |
| `--scheme` | Yes | Scheme to build |
| `--simulator-id` | No | Simulator UDID |
| `--simulator-name` | No | Simulator name (e.g., "iPhone 15") |
| `--configuration` | No | Build configuration (default: Debug) |
| `--derived-data` | No | Custom derived data path |

## Examples

```bash
# Build for a specific simulator
scripts/xcodebuild-sim.py \
  --workspace ./MyApp.xcworkspace \
  --scheme MyApp \
  --simulator-name "iPhone 15 Pro"

# Release build
scripts/xcodebuild-sim.py \
  --project ./MyApp.xcodeproj \
  --scheme MyApp \
  --configuration Release
```

## Output

```json
{
  "success": true,
  "message": "Build completed successfully",
  "path": "/path/to/MyApp.xcodeproj",
  "type": "project",
  "scheme": "MyApp",
  "configuration": "Debug",
  "simulator_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "app_path": "/path/to/DerivedData/.../MyApp.app"
}
```

## Notes

- If no simulator is specified, builds for "generic iOS Simulator"
- Automatically skips macro/package plugin validation for faster builds
- The app can be installed using the iOSSimulator plugin's sim-install.py
