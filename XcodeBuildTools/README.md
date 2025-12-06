# XcodeBuildTools Plugin

A comprehensive set of skills for Xcode development, providing build, test, and automation capabilities for iOS, macOS, and Swift projects.

## Overview

This plugin reimplements the functionality of [XcodeBuildMCP](https://github.com/cameroncooke/XcodeBuildMCP) as Claude Code skills, allowing you to build, test, and manage Xcode projects without requiring an MCP server.

## Prerequisites

- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3 (pre-installed on macOS)

## Available Skills

### xcode-doctor
Diagnose and validate your Xcode development environment.

### device-build
Build, test, and deploy apps to physical iOS devices.

### simulator-build
Build, test, and run apps on iOS simulators.

### simulator-management
Manage iOS simulators - boot, shutdown, configure location, appearance, and status bar.

### macos-build
Build, test, and run macOS applications.

### project-discovery
Discover Xcode projects, list schemes, and show build settings.

### project-scaffolding
Create new iOS and macOS project templates.

### swift-package
Build, test, run, and manage Swift packages.

### ui-automation
Automate UI interactions - tap, swipe, type, and take screenshots.

### logging
Capture and manage device and simulator logs.

### xcode-clean
Clean build products and derived data.

## Installation

```bash
# Add the marketplace
/plugin marketplace add gpambrozio/ClaudeCodePlugins

# Install the plugin
/plugin install XcodeBuildTools@ClaudeCodePlugins
```

## Usage

Once installed, the skills are automatically available. Claude will use them when you ask for Xcode-related tasks like:

- "Build my iOS app for the simulator"
- "Run tests on my project"
- "Create a new iOS project"
- "List available simulators"
- "Take a screenshot of the simulator"

## Credits

Based on [XcodeBuildMCP](https://github.com/cameroncooke/XcodeBuildMCP) by Cameron Cooke.
