---
name: show-build-settings
description: Show xcodebuild build settings for an Xcode project or workspace with a specific scheme. Use to inspect build configuration, product paths, deployment targets, and other build variables.
---

# Show Build Settings

Display Xcode build settings for a project/workspace and scheme.

## Usage

```bash
# For a project
scripts/show-build-settings.py --project /path/to/MyApp.xcodeproj --scheme MyApp

# For a workspace
scripts/show-build-settings.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | One required | Path to .xcodeproj file |
| `--workspace` | One required | Path to .xcworkspace file |
| `--scheme` | Yes | Scheme name |
| `--configuration` | No | Build configuration (Debug, Release) |
| `--key` | No | Show only a specific setting key |

## Examples

```bash
# Show all settings for a scheme
scripts/show-build-settings.py --project ./MyApp.xcodeproj --scheme MyApp

# Show Release configuration settings
scripts/show-build-settings.py --project ./MyApp.xcodeproj --scheme MyApp --configuration Release

# Show only the bundle identifier
scripts/show-build-settings.py --project ./MyApp.xcodeproj --scheme MyApp --key PRODUCT_BUNDLE_IDENTIFIER
```

## Output

```json
{
  "success": true,
  "path": "/path/to/MyApp.xcodeproj",
  "type": "project",
  "scheme": "MyApp",
  "configuration": "Debug",
  "common_settings": {
    "PRODUCT_NAME": "MyApp",
    "PRODUCT_BUNDLE_IDENTIFIER": "com.example.MyApp",
    "BUILT_PRODUCTS_DIR": "/path/to/Build/Products/Debug-iphonesimulator"
  },
  "all_settings": { "...": "..." },
  "settings_count": 150
}
```

## Common Settings

Key settings highlighted in `common_settings`:
- `PRODUCT_NAME`, `PRODUCT_BUNDLE_IDENTIFIER`
- `BUILT_PRODUCTS_DIR`, `TARGET_BUILD_DIR`
- `SWIFT_VERSION`, `IPHONEOS_DEPLOYMENT_TARGET`
- `SDKROOT`, `ARCHS`
