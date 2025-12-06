---
name: list-devices
description: List connected physical Apple devices (iPhone, iPad, Apple Watch, Apple TV, Vision Pro) with their UUIDs, names, and connection status. Use to discover available physical devices for building and testing.
---

# List Devices

List connected physical Apple devices.

## Usage

```bash
scripts/list-devices.py
```

## Arguments

This script takes no arguments.

## Output

```json
{
  "success": true,
  "count": 2,
  "connected_count": 1,
  "devices": [
    {
      "udid": "00008110-XXXXXXXXXXXX",
      "name": "My iPhone",
      "platform": "iOS",
      "os_version": "17.4",
      "model": "iPhone 15 Pro",
      "architecture": "arm64e",
      "connected": true,
      "paired": true,
      "developer_mode": true
    }
  ],
  "message": "Found 2 device(s), 1 connected"
}
```

## Notes

- Uses `devicectl` on Xcode 15+, falls back to `xctrace` for older Xcode
- Devices must be trusted (accept the dialog on the device)
- iOS 16+ requires Developer Mode enabled (Settings > Privacy & Security > Developer Mode)
- Wi-Fi debugging requires the device to be on the same network

## Device States

| Field | Description |
|-------|-------------|
| `connected` | Device is actively connected (USB or Wi-Fi) |
| `paired` | Device has been paired with this Mac |
| `developer_mode` | Developer Mode is enabled (iOS 16+) |
