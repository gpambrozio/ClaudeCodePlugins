---
name: xcode-doctor
description: Diagnose Xcode development environment health. Use when encountering build errors, setting up a new Mac, troubleshooting missing tools, or verifying Xcode installation.
---

> This skill has no equivalent in the Xcode MCP server.

# Xcode Doctor

Diagnose your development environment.

## Usage

```bash
scripts/xcode-doctor.py
```

## Checks

- Xcode version and developer directory
- Swift compiler availability
- Simulator and device counts
- Tool availability: xcodebuild, xcrun, git, pod, carthage

Output JSON with `health` status (`good` or `issues`) and diagnostic details.
