---
name: xcode-build
description: Build, test, and manage Xcode projects and workspaces. Use this skill whenever you need to discover projects, list schemes, build for simulators or devices, run tests, or diagnose environment issues. Works with xcodebuild command-line tool.
---

# Xcode Build Management

Build, test, and manage Xcode projects and workspaces using command-line tools. This skill provides scripts for common Xcode operations without requiring an MCP server.

## Prerequisites

- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3 (pre-installed on macOS)

## Running the Scripts

- All scripts are executable with proper shebang - no need to prefix with `python3`
- All scripts are in the `scripts/` directory
- All scripts output JSON with a `success` boolean field
- All scripts have proper docstrings explaining arguments

## Quick Start Workflow

```bash
# 1. Diagnose your environment
scripts/xc-doctor.py

# 2. Find Xcode projects in current directory
scripts/xc-discover.py

# 3. List schemes in a workspace
scripts/xc-schemes.py --workspace MyApp.xcworkspace

# 4. Build for iOS Simulator
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'platform=iOS Simulator,name=iPhone 15'

# 5. Run tests
scripts/xc-test.py --workspace MyApp.xcworkspace --scheme MyAppTests \
    --destination 'platform=iOS Simulator,name=iPhone 15'
```

## Script Reference

All scripts are in `scripts/` and output JSON.

### Environment & Discovery

#### xc-doctor.py
Diagnose your Xcode development environment.

```bash
# Basic diagnostics
scripts/xc-doctor.py

# Verbose (includes CocoaPods, Homebrew)
scripts/xc-doctor.py --verbose
```

**Checks:** Xcode version, Swift version, simulators, connected devices, DerivedData size.

#### xc-discover.py
Find Xcode projects and workspaces in a directory.

```bash
# Search current directory
scripts/xc-discover.py

# Search specific path
scripts/xc-discover.py --path /path/to/code

# Limit depth
scripts/xc-discover.py --path ~/Projects --max-depth 3
```

#### xc-schemes.py
List available schemes in a project or workspace.

```bash
# From workspace
scripts/xc-schemes.py --workspace MyApp.xcworkspace

# From project
scripts/xc-schemes.py --project MyApp.xcodeproj
```

#### xc-settings.py
Show build settings for a scheme.

```bash
# Key settings only
scripts/xc-settings.py --workspace MyApp.xcworkspace --scheme MyApp

# All settings as JSON
scripts/xc-settings.py --workspace MyApp.xcworkspace --scheme MyApp --json

# Filter by pattern
scripts/xc-settings.py --workspace MyApp.xcworkspace --scheme MyApp --filter "BUNDLE"
```

### Building

#### xc-build.py
Build a project or workspace for any destination.

```bash
# Build for iOS Simulator
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'platform=iOS Simulator,name=iPhone 15'

# Build for specific simulator by UUID
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'id=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'

# Build for macOS
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'platform=macOS'

# Build for physical device
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'platform=iOS,id=DEVICE-UDID'

# Clean build with Release configuration
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'platform=iOS Simulator,name=iPhone 15' \
    --configuration Release --clean

# Generic build (any simulator)
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'generic/platform=iOS Simulator'
```

**Destination Formats:**
| Target | Destination Format |
|--------|-------------------|
| Named Simulator | `platform=iOS Simulator,name=iPhone 15` |
| Simulator by UUID | `id=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` |
| Physical Device | `platform=iOS,id=DEVICE-UDID` |
| macOS | `platform=macOS` |
| Any iOS Simulator | `generic/platform=iOS Simulator` |
| Any iOS Device | `generic/platform=iOS` |

### Testing

#### xc-test.py
Run tests for a project or workspace.

```bash
# Run all tests
scripts/xc-test.py --workspace MyApp.xcworkspace --scheme MyAppTests \
    --destination 'platform=iOS Simulator,name=iPhone 15'

# Run specific test
scripts/xc-test.py --workspace MyApp.xcworkspace --scheme MyAppTests \
    --destination 'platform=iOS Simulator,name=iPhone 15' \
    --only-testing 'MyAppTests/LoginTests/testLogin'

# Skip specific tests
scripts/xc-test.py --workspace MyApp.xcworkspace --scheme MyAppTests \
    --destination 'platform=iOS Simulator,name=iPhone 15' \
    --skip-testing 'MyAppTests/SlowTests'

# Parallel tests with retry
scripts/xc-test.py --workspace MyApp.xcworkspace --scheme MyAppTests \
    --destination 'platform=iOS Simulator,name=iPhone 15' \
    --parallel --retry-count 2
```

### Device Management

#### xc-devices.py
List connected physical Apple devices.

```bash
# List all devices
scripts/xc-devices.py

# List only available (paired) devices
scripts/xc-devices.py --available

# Raw JSON output
scripts/xc-devices.py --json-raw
```

#### xc-device-install.py
Install an app on a physical device.

```bash
scripts/xc-device-install.py --device DEVICE-UDID --app /path/to/MyApp.app
```

#### xc-device-launch.py
Launch an app on a physical device.

```bash
scripts/xc-device-launch.py --device DEVICE-UDID --bundle-id com.example.MyApp
```

#### xc-device-stop.py
Stop a running app on a physical device.

```bash
scripts/xc-device-stop.py --device DEVICE-UDID --bundle-id com.example.MyApp
```

### Cleaning

#### xc-clean.py
Clean build products and DerivedData.

```bash
# Clean a specific scheme
scripts/xc-clean.py --workspace MyApp.xcworkspace --scheme MyApp

# View DerivedData info
scripts/xc-clean.py --derived-data

# Clean ALL DerivedData
scripts/xc-clean.py --derived-data --all
```

## Common Workflows

### Build and Install on Simulator

```bash
# 1. Find a simulator
# (Use iOSSimulator plugin's sim-list.py if available)
xcrun simctl list devices available | grep iPhone

# 2. Build for that simulator
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'platform=iOS Simulator,name=iPhone 15'

# 3. Install and launch
# (Use iOSSimulator plugin's sim-install.py and sim-launch.py)
```

### Build and Deploy to Physical Device

```bash
# 1. List connected devices
scripts/xc-devices.py

# 2. Build for the device
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'platform=iOS,id=DEVICE-UDID' \
    --configuration Release

# 3. Install the app
scripts/xc-device-install.py --device DEVICE-UDID \
    --app ~/Library/Developer/Xcode/DerivedData/MyApp-xxx/Build/Products/Release-iphoneos/MyApp.app

# 4. Launch the app
scripts/xc-device-launch.py --device DEVICE-UDID --bundle-id com.example.MyApp
```

### Continuous Integration Build

```bash
# Clean, build, and test in one flow
scripts/xc-build.py --workspace MyApp.xcworkspace --scheme MyApp \
    --destination 'generic/platform=iOS Simulator' \
    --configuration Release --clean

scripts/xc-test.py --workspace MyApp.xcworkspace --scheme MyAppTests \
    --destination 'platform=iOS Simulator,name=iPhone 15' \
    --parallel
```

## JSON Output Schemas

All scripts output JSON to stdout. Every response includes a `success` boolean.

### Standard Success Response
```json
{
  "success": true,
  "message": "Description of what was done"
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": "Description of what went wrong",
  "hint": "Helpful suggestion if available"
}
```

### xc-doctor.py
```json
{
  "success": true,
  "message": "Environment check complete: healthy",
  "status": "healthy",
  "diagnostics": {
    "system": { "os": "macOS", "os_version": "14.0" },
    "xcode": { "installed": true, "version": "15.0" },
    "swift": { "installed": true, "version": "Swift version 5.9" },
    "simulators": { "available": true, "count": 25 },
    "devices": { "available": true, "connected_count": 1 }
  }
}
```

### xc-discover.py
```json
{
  "success": true,
  "message": "Found 1 workspace(s) and 2 project(s)",
  "workspaces": ["/path/to/MyApp.xcworkspace"],
  "projects": ["/path/to/MyApp.xcodeproj", "/path/to/MyFramework.xcodeproj"]
}
```

### xc-build.py (success)
```json
{
  "success": true,
  "message": "Build succeeded",
  "scheme": "MyApp",
  "configuration": "Debug",
  "warning_count": 0
}
```

### xc-build.py (failure)
```json
{
  "success": false,
  "error": "Build failed",
  "scheme": "MyApp",
  "error_count": 2,
  "errors": [
    {
      "file": "/path/to/File.swift",
      "line": 42,
      "column": 10,
      "message": "Cannot find 'foo' in scope"
    }
  ]
}
```

### xc-test.py (success)
```json
{
  "success": true,
  "message": "Tests passed: 42 passed, 0 failed, 0 skipped",
  "passed_count": 42,
  "failed_count": 0,
  "skipped_count": 0,
  "execution_time": 12.5
}
```

### xc-devices.py
```json
{
  "success": true,
  "message": "Found 1 device(s)",
  "devices": [
    {
      "name": "iPhone 15 Pro",
      "udid": "00008120-XXXXXXXXXXXX",
      "platform": "iOS",
      "os_version": "17.0",
      "model": "iPhone 15 Pro",
      "connection": "USB"
    }
  ]
}
```

## Troubleshooting

### "xcodebuild: error: The scheme 'X' is not configured for building"
- Run `xc-schemes.py` to list available schemes
- Check that the scheme is shared (Manage Schemes in Xcode)

### "Unable to find a destination matching the provided specification"
- List simulators with `xcrun simctl list devices available`
- Use exact device name or UUID in destination

### Build signing errors
- For simulator builds: Signing is usually not required
- For device builds: Configure signing in Xcode, or use:
  ```bash
  --extra-args CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO
  ```

### Test timeout
- Tests have a 30-minute timeout by default
- Long-running tests may need configuration adjustment

### DerivedData taking too much space
```bash
# Check size
scripts/xc-clean.py --derived-data

# Clean all
scripts/xc-clean.py --derived-data --all
```

## Integration with Other Plugins

This plugin works well with:

- **iOSSimulator**: Use for simulator management (boot, screenshot, UI automation)
- **SwiftDevelopment**: Use xcsift for filtered build output

When building for simulator, use iOSSimulator's `sim-list.py` to find UUIDs, then pass to `xc-build.py`.
