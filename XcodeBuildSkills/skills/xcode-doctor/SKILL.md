---
name: xcode-doctor
description: Diagnose the Xcode development environment and check tool availability. Verifies Xcode installation, Swift version, simulators, devices, and common tools.
---

# Xcode Doctor

Diagnose your Xcode development environment.

## Usage

```bash
scripts/xcode-doctor.py
```

## Arguments

This script takes no arguments.

## Checks Performed

| Check | Description |
|-------|-------------|
| Xcode | Version and build number |
| Developer Directory | Active developer tools path |
| Swift | Swift compiler version |
| Simulators | Count of available/booted simulators |
| Devices | Count of connected physical devices |
| Tools | Availability of xcodebuild, xcrun, pod, carthage, git |

## Output

```json
{
  "success": true,
  "system": {
    "os": "Darwin",
    "os_version": "14.0",
    "architecture": "arm64"
  },
  "xcode": {
    "installed": true,
    "version": "15.0",
    "build": "15A240d"
  },
  "developer_dir": {
    "path": "/Applications/Xcode.app/Contents/Developer",
    "valid": true
  },
  "swift": {
    "version": "5.9",
    "installed": true
  },
  "simulators": {
    "total": 25,
    "booted": 1,
    "available": true
  },
  "devices": {
    "connected": 0,
    "available": true
  },
  "tools": {
    "xcodebuild": true,
    "xcrun": true,
    "swift": true,
    "git": true,
    "pod": true,
    "carthage": false
  },
  "health": "good",
  "message": "Development environment is properly configured"
}
```

## Health Status

| Status | Description |
|--------|-------------|
| `good` | All required tools are properly configured |
| `issues` | Problems detected (see `issues` array) |

## Common Issues

- **Xcode not installed**: Install Xcode from the App Store
- **Command Line Tools missing**: Run `xcode-select --install`
- **Wrong developer directory**: Run `sudo xcode-select -s /Applications/Xcode.app`
