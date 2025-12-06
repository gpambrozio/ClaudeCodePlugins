---
name: xcodebuild-macos
description: Build a macOS app using xcodebuild. Supports native architecture or cross-compilation to arm64/x86_64.
---

# Build macOS App

Build a macOS application.

## Usage

```bash
scripts/xcodebuild-macos.py --project ./MyApp.xcodeproj --scheme MyApp
scripts/xcodebuild-macos.py --workspace ./MyApp.xcworkspace --scheme MyApp
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | One required | Path to .xcodeproj file |
| `--workspace` | One required | Path to .xcworkspace file |
| `--scheme` | Yes | Scheme to build |
| `--configuration` | No | Build configuration (default: Debug) |
| `--arch` | No | Target architecture: arm64, x86_64 |
| `--derived-data` | No | Custom derived data path |

## Examples

```bash
# Debug build
scripts/xcodebuild-macos.py --project ./MyApp.xcodeproj --scheme MyApp

# Release build for Intel
scripts/xcodebuild-macos.py \
  --workspace ./MyApp.xcworkspace \
  --scheme MyApp \
  --configuration Release \
  --arch x86_64
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
  "architecture": "native",
  "app_path": "/path/to/DerivedData/.../MyApp.app",
  "next_steps": [
    "Use launch-mac-app.py to run the app",
    "Or open the app directly with: open /path/to/MyApp.app"
  ]
}
```

## Notes

- Builds for native architecture by default
- Use `--arch arm64` for Apple Silicon only
- Use `--arch x86_64` for Intel/Rosetta 2
