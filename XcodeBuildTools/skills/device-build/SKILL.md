---
name: device-build
description: Build, install, launch, and test iOS apps on physical Apple devices (iPhone, iPad, Apple Watch, Apple TV, Vision Pro). Use this skill when working with physical devices connected via USB or network.
---

# Device Build

Build, install, and manage iOS apps on physical Apple devices.

## Prerequisites

- macOS with Xcode 15+ installed
- Physical device connected via USB or paired over network
- Valid code signing (development certificate and provisioning profile)

## Scripts

All scripts are in the `scripts/` directory and output JSON.

### list-devices.py

List connected physical Apple devices.

```bash
scripts/list-devices.py
```

Output:
```json
{
  "success": true,
  "devices": [
    {
      "name": "iPhone 15 Pro",
      "udid": "00008030-001234567890",
      "model": "iPhone 15 Pro",
      "os_version": "17.0",
      "connection": "USB",
      "paired": true
    }
  ]
}
```

### build-device.py

Build an Xcode project/workspace for a physical device.

```bash
# Build with workspace
scripts/build-device.py --workspace MyApp.xcworkspace --scheme MyApp --device-id <UDID>

# Build with project
scripts/build-device.py --project MyApp.xcodeproj --scheme MyApp --device-id <UDID>

# Specify configuration
scripts/build-device.py --workspace MyApp.xcworkspace --scheme MyApp --device-id <UDID> --configuration Release
```

**Parameters:**
- `--workspace` or `--project`: Path to .xcworkspace or .xcodeproj (mutually exclusive)
- `--scheme`: Build scheme name (required)
- `--device-id`: Device UDID from list-devices.py (required)
- `--configuration`: Build configuration (default: Debug)
- `--derived-data`: Custom derived data path
- `--extra-args`: Additional xcodebuild arguments

### install-app-device.py

Install an app on a connected device.

```bash
scripts/install-app-device.py --device-id <UDID> --app /path/to/MyApp.app
```

**Parameters:**
- `--device-id`: Device UDID (required)
- `--app`: Path to .app bundle (required)

### launch-app-device.py

Launch an installed app on a device.

```bash
scripts/launch-app-device.py --device-id <UDID> --bundle-id com.example.myapp

# Wait for debugger
scripts/launch-app-device.py --device-id <UDID> --bundle-id com.example.myapp --wait-for-debugger
```

**Parameters:**
- `--device-id`: Device UDID (required)
- `--bundle-id`: App bundle identifier (required)
- `--wait-for-debugger`: Pause app startup waiting for debugger

### stop-app-device.py

Terminate a running app on a device.

```bash
scripts/stop-app-device.py --device-id <UDID> --bundle-id com.example.myapp
```

### test-device.py

Run tests on a physical device.

```bash
scripts/test-device.py --workspace MyApp.xcworkspace --scheme MyAppTests --device-id <UDID>

# Run specific test
scripts/test-device.py --workspace MyApp.xcworkspace --scheme MyAppTests --device-id <UDID> --only-testing "MyAppTests/LoginTests/testSuccessfulLogin"
```

**Parameters:**
- `--workspace` or `--project`: Path to .xcworkspace or .xcodeproj
- `--scheme`: Test scheme name (required)
- `--device-id`: Device UDID (required)
- `--only-testing`: Run only specific test(s)
- `--skip-testing`: Skip specific test(s)
- `--configuration`: Build configuration (default: Debug)

## Typical Workflow

```bash
# 1. List connected devices
scripts/list-devices.py

# 2. Build for the device
scripts/build-device.py --workspace MyApp.xcworkspace --scheme MyApp --device-id <UDID>

# 3. Install the app (if not using build-and-run)
scripts/install-app-device.py --device-id <UDID> --app ~/Library/Developer/Xcode/DerivedData/.../MyApp.app

# 4. Launch the app
scripts/launch-app-device.py --device-id <UDID> --bundle-id com.example.myapp

# 5. Run tests
scripts/test-device.py --workspace MyApp.xcworkspace --scheme MyAppTests --device-id <UDID>
```

## Notes

- Building for devices requires valid code signing
- Use `security find-identity -v -p codesigning` to list available signing identities
- Device UDID can be found in Finder or using `list-devices.py`
- The `devicectl` tool (Xcode 15+) is preferred over older methods
