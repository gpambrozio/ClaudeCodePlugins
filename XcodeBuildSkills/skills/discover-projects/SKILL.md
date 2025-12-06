---
name: discover-projects
description: Discover Xcode projects (.xcodeproj) and workspaces (.xcworkspace) in a directory. Use when you need to find Xcode projects in a codebase or directory tree.
---

# Discover Projects

Find Xcode projects and workspaces in a directory tree.

## Usage

```bash
scripts/discover-projects.py --path /path/to/scan [--max-depth N]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--path` | Yes | Root directory to scan for Xcode projects |
| `--max-depth` | No | Maximum directory depth (default: 5) |

## Examples

```bash
# Scan current directory
scripts/discover-projects.py --path .

# Scan with limited depth
scripts/discover-projects.py --path /Users/me/Projects --max-depth 3
```

## Output

```json
{
  "success": true,
  "scan_path": "/path/to/scan",
  "max_depth": 5,
  "projects": {
    "count": 2,
    "paths": [
      "/path/to/MyApp.xcodeproj",
      "/path/to/MyFramework.xcodeproj"
    ]
  },
  "workspaces": {
    "count": 1,
    "paths": [
      "/path/to/MyApp.xcworkspace"
    ]
  },
  "message": "Found 2 project(s) and 1 workspace(s)"
}
```

## Skipped Directories

The following directories are automatically skipped:
- build, Build, DerivedData
- Pods, Carthage, vendor
- .git, .svn, .hg
- node_modules, .build
- Hidden directories (starting with .)
