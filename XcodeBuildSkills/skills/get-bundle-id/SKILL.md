---
name: get-bundle-id
description: Get the bundle identifier and metadata from an app bundle (.app) or Info.plist file. Use to retrieve CFBundleIdentifier, version, and other app metadata.
---

# Get Bundle ID

Extract bundle identifier and metadata from an app bundle or plist.

## Usage

```bash
# From an app bundle
scripts/get-bundle-id.py --app /path/to/MyApp.app

# From an Info.plist
scripts/get-bundle-id.py --plist /path/to/Info.plist
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--app` | One required | Path to .app bundle |
| `--plist` | One required | Path to Info.plist file |

## Examples

```bash
# Get bundle ID from built app
scripts/get-bundle-id.py --app ~/Library/Developer/Xcode/DerivedData/MyApp/Build/Products/Debug-iphonesimulator/MyApp.app

# Get bundle ID from project's Info.plist
scripts/get-bundle-id.py --plist ./MyApp/Info.plist
```

## Output

```json
{
  "success": true,
  "bundle_id": "com.example.MyApp",
  "bundle_name": "MyApp",
  "bundle_display_name": "My App",
  "bundle_version": "1",
  "bundle_short_version": "1.0.0",
  "minimum_os_version": "15.0",
  "app_path": "/path/to/MyApp.app",
  "plist_path": "/path/to/MyApp.app/Info.plist"
}
```

## Extracted Fields

| Field | Plist Key |
|-------|-----------|
| `bundle_id` | CFBundleIdentifier |
| `bundle_name` | CFBundleName |
| `bundle_display_name` | CFBundleDisplayName |
| `bundle_version` | CFBundleVersion |
| `bundle_short_version` | CFBundleShortVersionString |
| `minimum_os_version` | MinimumOSVersion / LSMinimumSystemVersion |
