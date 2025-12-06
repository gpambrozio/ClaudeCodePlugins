---
name: xcodebuild-clean
description: Clean Xcode build products using `xcodebuild clean`. Removes compiled binaries and intermediate build files. Use when you need a fresh build or to resolve build issues.
---

# Xcodebuild Clean

Clean Xcode build products.

## Usage

```bash
# For a project
scripts/xcodebuild-clean.py --project /path/to/MyApp.xcodeproj --scheme MyApp

# For a workspace
scripts/xcodebuild-clean.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | One required | Path to .xcodeproj file |
| `--workspace` | One required | Path to .xcworkspace file |
| `--scheme` | Required for workspace | Scheme to clean |
| `--configuration` | No | Build configuration (Debug, Release) |
| `--derived-data` | No | Custom derived data path |

## Examples

```bash
# Clean a project
scripts/xcodebuild-clean.py --project ./MyApp.xcodeproj --scheme MyApp

# Clean workspace with specific configuration
scripts/xcodebuild-clean.py --workspace ./MyApp.xcworkspace --scheme MyApp --configuration Release

# Clean with custom derived data path
scripts/xcodebuild-clean.py --project ./MyApp.xcodeproj --scheme MyApp --derived-data ./build
```

## Output

```json
{
  "success": true,
  "message": "Clean completed successfully",
  "path": "/path/to/MyApp.xcodeproj",
  "type": "project",
  "scheme": "MyApp",
  "configuration": "all"
}
```

## What Gets Cleaned

- Compiled object files
- Linked binaries
- Intermediate build products
- Build artifacts in derived data

## Notes

- Does not delete source files
- May require re-indexing in Xcode
- Useful for resolving "stale" build issues
