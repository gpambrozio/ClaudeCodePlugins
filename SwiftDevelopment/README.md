# SwiftDevelopment Plugin

A Claude Code plugin for Swift and iOS development workflows, providing MCP servers and slash commands to streamline your development process.

## Installation

1. Link this plugin to your Claude Code plugins directory:
   ```bash
   claude plugins add /path/to/ClaudeCodePlugins/SwiftDevelopment
   ```

2. Verify installation:
   ```bash
   claude plugins list
   ```

## Features

This plugin provides:
- **Code Analysis**: Comprehensive Swift code analysis with `/analyze` command
- **Swift Compilation**: Token-efficient xcodebuild and swift command wrappers with xcsift
- **1 MCP Server**: Sosumi AI integration for Swift development assistance
- **Extensible Structure**: Ready for custom skills and agents

## Slash Commands

### `/analyze`

Performs comprehensive analysis of Swift code in your project:
- Architecture pattern detection
- Anti-pattern identification
- Memory management issues (retain cycles, strong references)
- SwiftUI best practices violations
- Unused imports and dead code
- Force unwrapping and optional handling
- Protocol conformance opportunities

Provides a summary of findings with file locations and severity levels (critical, warning, suggestion).

## Skills

### swift-compile

Provides guidance for using `xcodebuild` and `swift` commands with [xcsift](https://github.com/ldomaradzki/xcsift) to parse output into JSON format, dramatically reducing verbosity for AI coding agents.

**Usage**: Claude will pipe xcodebuild and swift commands through xcsift when building or testing Swift projects. The skill:
- Guides proper use of `xcodebuild` and `swift` commands
- Pipes compiler output through xcsift for structured JSON parsing
- Reports errors and warnings concisely
- Provides xcsift installation script if needed

**Examples**:
```bash
# Build a workspace
xcodebuild \
  -workspace Project.xcworkspace \
  -scheme ProjectScheme \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  build 2>&1 | xcsift --warnings

# Test a Swift package
cd PackageFolder
swift test 2>&1 | xcsift --warnings
```

## MCP Servers

This plugin includes an integrated MCP server for Swift development:

### sosumi

Sosumi AI provides Swift documentation through an HTTP-based MCP server.

**Type**: HTTP-based MCP server
**URL**: `https://sosumi.ai/mcp`

### Adding More MCP Servers

To add additional MCP servers, edit `.mcp.json`:
```json
{
  "mcpServers": {
    "your-server": {
      "command": "npx",
      "args": ["-y", "your-package@latest"]
    }
  }
}
```

## Development

### Adding New Commands

1. Create a new `.md` file in `commands/`
2. Write the command prompt in markdown
3. The filename becomes the command name (e.g., `my-command.md` → `/my-command`)

### Adding Skills

1. Create a new directory in `skills/` with your skill name
2. Add a `SKILL.md` file with the skill definition
3. Skills are automatically available to Claude agents

### Adding Agents

1. Create a new `.md` file in `agents/`
2. Define the agent's behavior and tools
3. Agents can be invoked for specialized tasks

## Contributing

When adding new features:
- Update this README
- Follow Swift naming conventions
- Test commands in real projects
- Document any new MCP server requirements

## Changelog

### 0.3.1
- Fixed hooks path to use plugin-local common directory (plugins cannot reference external files)

### 0.3.0
- Centralized hooks to common/hooks.json
- Made session-start.py and pre-tool-use.py self-configuring from plugin.json

### 0.2.0
- Added version tracking with automatic changelog notifications on plugin updates
- Refactored session hooks to use shared infrastructure

### 0.1.11 (2025-12-06)
- Added `--format toon` flag documentation to swift-compile skill for token-optimized output
- Updated all xcsift examples to use the recommended `--format toon --warnings` pattern

### 0.1.10 (2025-12-01)
- Changed destination parameter from device names to device UUIDs for more reliable simulator targeting
- Clarified documentation about using `tee` to redirect output to temporary file for later inspection
- Simplified destination parameter examples throughout skill documentation

### 0.1.9 (2025-11-24)
- Added `tee` to xcsift pipeline to preserve full output in temporary file for debugging
- Made xcsift update command explicit in skill documentation
- Updated all code examples to include the `tee` pattern

### 0.1.8 (2025-11-16)
- Removed wrapper scripts (swift.sh and xcodebuild.sh) - now use xcodebuild/swift directly with xcsift
- Updated swift-compile skill to pipe commands through xcsift instead of using wrapper scripts
- Changed pre-tool-use hook to allow (with reminder) rather than deny xcodebuild/swift commands
- Simplified compilation workflow with direct tool usage

### 0.1.7 (2025-11-08)
- Reduced verbosity in xcsift installation script - now only outputs on errors

### 0.1.6 (2025-11-08)
- Improved swift-compile skill instructions

### 0.1.5 (2025-11-05)
- Replaced ios-simulator and apple-docs MCP servers with Sosumi AI HTTP-based MCP server
- Further refined pre-tool-use hook regex to only block xcodebuild commands (removed overly broad swift pattern)

### 0.1.4 (2025-11-01)
- Fixed pre-tool-use hook regex that was too broad and causing false positives
- Resolved issue where hook incorrectly triggered when tools searched for Swift files

### 0.1.3 (2025-10-31)
- Converted hook scripts from Bash to Python for better cross-platform compatibility
- Improved error handling in session-start and pre-tool-use hooks
- Enhanced code maintainability with consistent Python implementation

## License

MIT
