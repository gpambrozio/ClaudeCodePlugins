---
name: launch-app-device
description: Launch an app on a connected physical Apple device by bundle identifier. Use after installing an app to run it for testing.
---

# Launch App on Device

Launch an installed app on a physical device.

## Usage

```bash
scripts/launch-app-device.py --device-id UDID --bundle-id com.example.MyApp
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--device-id` | Yes | Device UDID (from list-devices.py) |
| `--bundle-id` | Yes | Bundle identifier of the app |
| `--args` | No | Arguments to pass to the app |

## Examples

```bash
# Launch an app
scripts/launch-app-device.py \
  --device-id 00008110-XXXXXXXXXXXX \
  --bundle-id com.example.MyApp

# Launch with arguments
scripts/launch-app-device.py \
  --device-id 00008110-XXXXXXXXXXXX \
  --bundle-id com.example.MyApp \
  --args --debug --config test
```

## Output

```json
{
  "success": true,
  "message": "App launched successfully",
  "device_id": "00008110-XXXXXXXXXXXX",
  "bundle_id": "com.example.MyApp",
  "pid": 12345
}
```

## Prerequisites

- App must be installed on the device (use install-app-device.py first)
- Device must be connected and trusted

## Notes

- Uses `devicectl` (Xcode 15+)
- Returns the process ID (PID) when available
- Use stop-app-device.py to terminate the running app
