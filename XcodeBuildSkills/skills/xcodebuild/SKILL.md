---
name: xcodebuild
description: Build Xcode projects for simulator, device, or macOS using xcodebuild. Use when compiling iOS/tvOS/watchOS apps for simulator or physical device, building macOS apps, or cleaning build products.
---

# Xcodebuild

Build Xcode projects and workspaces for various destinations.

## Scripts

| Script | Purpose |
|--------|---------|
| `xcodebuild-sim.py` | Build for iOS/tvOS/watchOS simulator |
| `xcodebuild-device.py` | Build for physical device (requires signing) |
| `xcodebuild-macos.py` | Build macOS app |
| `xcodebuild-clean.py` | Clean build products |

## Common Usage

```bash
# Build for simulator
scripts/xcodebuild-sim.py --project <path> | --workspace <path> --scheme <name> \
  [--simulator-name "iPhone 15"] [--configuration Debug]

# Build for device (requires code signing)
scripts/xcodebuild-device.py --project <path> | --workspace <path> --scheme <name> \
  [--device-id <udid>] [--configuration Debug]

# Build macOS app
scripts/xcodebuild-macos.py --project <path> | --workspace <path> --scheme <name> \
  [--arch arm64|x86_64] [--configuration Debug]

# Clean
scripts/xcodebuild-clean.py --project <path> | --workspace <path> --scheme <name>
```

All scripts output JSON with `success`, `app_path`, and build details.
