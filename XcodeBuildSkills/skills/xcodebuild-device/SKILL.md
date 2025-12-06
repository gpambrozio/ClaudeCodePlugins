---
name: xcodebuild-device
description: Build an iOS/tvOS/watchOS app for a physical device using xcodebuild. Requires proper code signing with a development certificate.
---

# Build for Device

Build an app for a physical iOS/tvOS/watchOS device.

## Usage

```bash
# Build for a specific device
scripts/xcodebuild-device.py --project ./MyApp.xcodeproj --scheme MyApp --device-id UDID

# Build for generic iOS device
scripts/xcodebuild-device.py --workspace ./MyApp.xcworkspace --scheme MyApp
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | One required | Path to .xcodeproj file |
| `--workspace` | One required | Path to .xcworkspace file |
| `--scheme` | Yes | Scheme to build |
| `--device-id` | No | Device UDID |
| `--configuration` | No | Build configuration (default: Debug) |
| `--derived-data` | No | Custom derived data path |

## Examples

```bash
# Build for a connected device
scripts/xcodebuild-device.py \
  --workspace ./MyApp.xcworkspace \
  --scheme MyApp \
  --device-id 00008110-XXXXXXXXXXXX

# Release build
scripts/xcodebuild-device.py \
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
  "device_id": "00008110-XXXXXXXXXXXX",
  "app_path": "/path/to/DerivedData/.../MyApp.app",
  "next_steps": [
    "Use install-app-device.py to install on the device",
    "Use launch-app-device.py to run the app"
  ]
}
```

## Code Signing Requirements

- Valid Apple Developer account
- Development certificate installed
- Device registered in provisioning profile
- Automatic or manual code signing configured in Xcode

## Notes

- Device builds take longer due to optimizations for ARM
- The app must be signed to run on a physical device
