---
name: xcode-project
description: Discover and inspect Xcode projects and workspaces. Use when finding .xcodeproj/.xcworkspace files, listing available schemes, viewing build settings, or extracting bundle identifiers from apps.
---

> **Xcode MCP**: If `XcodeGlob` / `XcodeLS` / `XcodeListWindows` are in your tool list, prefer those over this skill.

# Xcode Project Discovery

Find and inspect Xcode projects, schemes, build settings, and app metadata.

## Scripts

| Script | Purpose |
|--------|---------|
| `discover-projects.py` | Find .xcodeproj and .xcworkspace files |
| `list-schemes.py` | List available schemes |
| `show-build-settings.py` | Display xcodebuild settings |
| `get-bundle-id.py` | Extract bundle ID from .app or Info.plist |

## Common Usage

```bash
# Find projects in a directory
scripts/discover-projects.py --path <dir> [--max-depth 5]

# List schemes
scripts/list-schemes.py --project <path> | --workspace <path>

# Show build settings
scripts/show-build-settings.py --project <path> --scheme <name> [--configuration Debug]

# Get bundle identifier
scripts/get-bundle-id.py --app <path.app> | --plist <Info.plist>
```

All scripts output JSON with `success` and relevant data.
