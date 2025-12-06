---
name: swift-package-build
description: Build a Swift Package using `swift build`. Use when you need to compile a Swift Package Manager project with optional configuration, target selection, and architecture settings.
---

# Swift Package Build

Build Swift packages with `swift build`.

## Usage

```bash
scripts/swift-package-build.py --package-path /path/to/package [options]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--package-path` | Yes | Path to the Swift package root directory |
| `--target` | No | Specific target to build |
| `--configuration` | No | Build configuration: `debug` (default) or `release` |
| `--arch` | No | Target architecture (can specify multiple times) |
| `--parse-as-library` | No | Add `-parse-as-library` flag for `@main` support |

## Examples

```bash
# Basic build (debug)
scripts/swift-package-build.py --package-path /path/to/MyPackage

# Release build
scripts/swift-package-build.py --package-path /path/to/MyPackage --configuration release

# Build specific target
scripts/swift-package-build.py --package-path /path/to/MyPackage --target MyLibrary

# Build for specific architecture
scripts/swift-package-build.py --package-path /path/to/MyPackage --arch arm64
```

## Output

```json
{
  "success": true,
  "message": "Build completed successfully",
  "package_path": "/path/to/MyPackage",
  "configuration": "debug",
  "output": "Build succeeded..."
}
```
