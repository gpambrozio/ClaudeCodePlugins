---
name: project-discovery
description: Discover Xcode projects, list available schemes, show build settings, and get bundle identifiers. Use this skill when you need to explore or understand an Xcode project structure.
---

# Project Discovery

Discover and analyze Xcode projects and workspaces.

## Prerequisites

- macOS with Xcode installed
- An Xcode project or workspace

## Scripts

All scripts are in the `scripts/` directory and output JSON.

### discover-projects.py

Find Xcode projects and workspaces in a directory.

```bash
# Search current directory
scripts/discover-projects.py

# Search specific directory
scripts/discover-projects.py --path /path/to/code

# Recursive search
scripts/discover-projects.py --path /path/to/code --recursive
```

Output:
```json
{
  "success": true,
  "projects": [
    {
      "type": "workspace",
      "name": "MyApp.xcworkspace",
      "path": "/path/to/MyApp.xcworkspace"
    },
    {
      "type": "project",
      "name": "MyApp.xcodeproj",
      "path": "/path/to/MyApp.xcodeproj"
    }
  ]
}
```

### list-schemes.py

List available build schemes.

```bash
# List schemes for workspace
scripts/list-schemes.py --workspace MyApp.xcworkspace

# List schemes for project
scripts/list-schemes.py --project MyApp.xcodeproj
```

Output:
```json
{
  "success": true,
  "schemes": [
    "MyApp",
    "MyAppTests",
    "MyAppUITests"
  ]
}
```

### show-build-settings.py

Show build settings for a scheme.

```bash
# Show all build settings
scripts/show-build-settings.py --workspace MyApp.xcworkspace --scheme MyApp

# Show specific setting
scripts/show-build-settings.py --workspace MyApp.xcworkspace --scheme MyApp --setting PRODUCT_BUNDLE_IDENTIFIER
```

### get-bundle-id.py

Get the bundle identifier for an app.

```bash
# From workspace/scheme
scripts/get-bundle-id.py --workspace MyApp.xcworkspace --scheme MyApp

# From built app
scripts/get-bundle-id.py --app /path/to/MyApp.app
```

## Typical Workflow

```bash
# 1. Find projects in directory
scripts/discover-projects.py --path /path/to/repo

# 2. List schemes
scripts/list-schemes.py --workspace /path/to/MyApp.xcworkspace

# 3. Get bundle ID for a scheme
scripts/get-bundle-id.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp

# 4. View build settings
scripts/show-build-settings.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp
```
