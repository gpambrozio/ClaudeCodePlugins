---
name: install-app-device
description: Install an app on a connected physical Apple device. Use after building an app for device to deploy it for testing.
---

# Install App on Device

Install an app bundle on a physical device.

## Usage

```bash
scripts/install-app-device.py --device-id UDID --app /path/to/MyApp.app
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--device-id` | Yes | Device UDID (from list-devices.py) |
| `--app` | Yes | Path to .app bundle to install |

## Examples

```bash
# Install a built app
scripts/install-app-device.py \
  --device-id 00008110-XXXXXXXXXXXX \
  --app ~/DerivedData/MyApp/Build/Products/Debug-iphoneos/MyApp.app
```

## Output

```json
{
  "success": true,
  "message": "App installed successfully",
  "device_id": "00008110-XXXXXXXXXXXX",
  "app_path": "/path/to/MyApp.app",
  "next_steps": [
    "Use launch-app-device.py to launch the app",
    "Or manually tap the app icon on the device"
  ]
}
```

## Prerequisites

- Device must be connected and trusted
- App must be signed for this device (use development certificate)
- Developer Mode enabled on iOS 16+ devices
- Uses `devicectl` (Xcode 15+) or falls back to `ios-deploy`

## Common Issues

| Issue | Solution |
|-------|----------|
| Signing error | Ensure app is signed with a valid development certificate |
| Device not found | Check connection, run list-devices.py |
| Installation timeout | Large apps may take longer; check device storage |
