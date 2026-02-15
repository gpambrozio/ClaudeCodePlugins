---
name: device-app
description: Manage apps on physical Apple devices (iPhone, iPad, Watch, TV, Vision Pro). Use when listing connected devices, installing apps on physical devices, launching or stopping apps on devices.
---

> This skill has no equivalent in the Xcode MCP server.

# Device App Management

List devices and manage apps on physical Apple devices.

## Scripts

| Script | Purpose |
|--------|---------|
| `list-devices.py` | List connected physical devices |
| `install-app-device.py` | Install .app bundle on device |
| `launch-app-device.py` | Launch app |
| `stop-app-device.py` | Stop running app |

## Common Usage

```bash
# List connected devices
scripts/list-devices.py

# Install app
scripts/install-app-device.py --device-id <udid> --app <path.app>

# Launch app
scripts/launch-app-device.py --device-id <udid> --app <path.app>

# Stop app
scripts/stop-app-device.py --device-id <udid> --app <path.app>
```

Requires: Device trusted, Developer Mode enabled (iOS 16+), proper code signing.
