---
name: stop-app-device
description: Stop a running app on a connected physical Apple device. Use to terminate an app that was launched for testing.
---

# Stop App on Device

Terminate a running app on a physical device.

## Usage

```bash
scripts/stop-app-device.py --device-id UDID --bundle-id com.example.MyApp
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--device-id` | Yes | Device UDID (from list-devices.py) |
| `--bundle-id` | Yes | Bundle identifier of the app to stop |

## Examples

```bash
# Stop an app
scripts/stop-app-device.py \
  --device-id 00008110-XXXXXXXXXXXX \
  --bundle-id com.example.MyApp
```

## Output

```json
{
  "success": true,
  "message": "App terminated successfully",
  "device_id": "00008110-XXXXXXXXXXXX",
  "bundle_id": "com.example.MyApp"
}
```

## Notes

- Uses `devicectl` (Xcode 15+)
- Returns success even if the app wasn't running
- Device must be connected
