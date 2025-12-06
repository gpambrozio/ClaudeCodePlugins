---
name: xcode-clean
description: Clean Xcode build products and derived data. Use this skill to free up disk space or resolve build issues by cleaning caches.
---

# Xcode Clean

Clean Xcode build products, derived data, and caches.

## Prerequisites

- macOS with Xcode installed

## Scripts

All scripts are in the `scripts/` directory and output JSON.

### clean-build.py

Clean build products for a specific project/workspace.

```bash
# Clean with workspace
scripts/clean-build.py --workspace MyApp.xcworkspace --scheme MyApp

# Clean with project
scripts/clean-build.py --project MyApp.xcodeproj --scheme MyApp

# Clean for specific platform
scripts/clean-build.py --workspace MyApp.xcworkspace --scheme MyApp --platform ios-simulator
```

**Parameters:**
- `--workspace` or `--project`: Path to .xcworkspace or .xcodeproj
- `--scheme`: Build scheme name (required)
- `--configuration`: Build configuration (default: Debug)
- `--platform`: Target platform (ios, ios-simulator, macos, watchos, tvos, visionos)

### clean-derived-data.py

Clean Xcode derived data.

```bash
# Clean all derived data
scripts/clean-derived-data.py --all

# Clean derived data for specific project
scripts/clean-derived-data.py --project MyApp

# Just show what would be cleaned
scripts/clean-derived-data.py --all --dry-run
```

**Parameters:**
- `--all`: Clean all derived data
- `--project`: Clean derived data for specific project name
- `--dry-run`: Show what would be cleaned without deleting
- `--older-than`: Only clean data older than N days

### clean-caches.py

Clean various Xcode caches.

```bash
# Clean module cache
scripts/clean-caches.py --module-cache

# Clean package cache (SPM)
scripts/clean-caches.py --package-cache

# Clean all caches
scripts/clean-caches.py --all
```

## Typical Workflow

### Resolve Build Issues
```bash
# 1. Clean the build
scripts/clean-build.py --workspace MyApp.xcworkspace --scheme MyApp

# 2. Clean derived data for project
scripts/clean-derived-data.py --project MyApp

# 3. Rebuild
# (Use simulator-build or device-build skill)
```

### Free Up Disk Space
```bash
# 1. Check what would be cleaned
scripts/clean-derived-data.py --all --dry-run

# 2. Clean old derived data
scripts/clean-derived-data.py --all --older-than 30

# 3. Clean caches
scripts/clean-caches.py --all
```

## Notes

- Derived data is stored in `~/Library/Developer/Xcode/DerivedData/`
- Module cache is in `~/Library/Developer/Xcode/DerivedData/ModuleCache.noindex/`
- SPM cache is in `~/Library/Caches/org.swift.swiftpm/`
- Cleaning derived data requires rebuilding the project
