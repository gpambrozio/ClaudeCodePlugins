---
name: swift-package-clean
description: Clean Swift Package build artifacts and derived data using `swift package clean`. Use to remove the .build directory and reset the build state.
---

# Swift Package Clean

Clean Swift package build artifacts with `swift package clean`.

## Usage

```bash
scripts/swift-package-clean.py --package-path /path/to/package
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--package-path` | Yes | Path to the Swift package root directory |

## Examples

```bash
# Clean build artifacts
scripts/swift-package-clean.py --package-path /path/to/MyPackage
```

## Output

```json
{
  "success": true,
  "message": "Build artifacts cleaned successfully",
  "package_path": "/path/to/MyPackage",
  "note": "The .build directory and derived data have been removed"
}
```
