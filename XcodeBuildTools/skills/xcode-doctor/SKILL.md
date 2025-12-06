---
name: xcode-doctor
description: Diagnose and validate your Xcode development environment. Use this skill to check if Xcode, simulators, and command line tools are properly installed and configured.
---

# Xcode Doctor

Diagnose and validate your Xcode development environment to ensure all tools are properly configured.

## Prerequisites

- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)

## Running the Diagnostic

```bash
scripts/xcode-doctor.py
```

## What It Checks

The doctor script validates:

1. **Xcode Installation**
   - Xcode path and version
   - Command line tools installation
   - Active developer directory

2. **Required Tools**
   - `xcodebuild` availability and version
   - `xcrun` functionality
   - `simctl` for simulator control
   - `devicectl` for device management (iOS 17+/Xcode 15+)

3. **Simulators**
   - Available simulator runtimes
   - Installed simulators

4. **Connected Devices**
   - Physical devices connected via USB or network

## Output Format

The script outputs JSON with the following structure:

```json
{
  "success": true,
  "xcode": {
    "path": "/Applications/Xcode.app",
    "version": "15.0",
    "build": "15A240d"
  },
  "command_line_tools": {
    "installed": true,
    "path": "/Library/Developer/CommandLineTools"
  },
  "tools": {
    "xcodebuild": {"available": true, "version": "15.0"},
    "xcrun": {"available": true},
    "simctl": {"available": true},
    "devicectl": {"available": true}
  },
  "simulators": {
    "runtimes": ["iOS 17.0", "iOS 16.4"],
    "count": 15
  },
  "devices": {
    "connected": 1,
    "list": [{"name": "iPhone 15", "udid": "..."}]
  }
}
```

## Troubleshooting

### Xcode Not Found
```bash
# Install Xcode from the App Store or download from developer.apple.com
# Then accept the license:
sudo xcodebuild -license accept
```

### Command Line Tools Missing
```bash
xcode-select --install
```

### Wrong Xcode Selected
```bash
# List available Xcode installations
ls /Applications | grep Xcode

# Select the correct one
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```
