# SwiftScaffolding Plugin

Swift project scaffolding and code generation tools.

## Features

- **Project Scaffolding**: Generate Swift project structures
- **Code Generation**: Create boilerplate code from templates
- **Project Setup**: Initialize new Swift/iOS projects with common configurations

## Installation

```bash
# Add the marketplace
/plugin marketplace add gpambrozio/ClaudeCodePlugins

# Install this plugin
/plugin install SwiftScaffolding@ClaudeCodePlugins
```

## Prerequisites

- macOS with Xcode installed
- Swift toolchain

## Usage

Use the `/scaffolding` command to scaffold Swift projects.

## Changelog

### 0.3.0
- Centralized hooks to common/hooks.json
- Made session-start.py self-configuring from plugin.json

### 0.2.0
- Added version tracking with automatic changelog notifications on plugin updates
- Refactored session hooks to use shared infrastructure

### 0.1.0
- Initial release with scaffolding command

## License

MIT
