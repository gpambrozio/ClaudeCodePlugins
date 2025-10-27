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
- **3 MCP Servers**: XcodeBuildMCP, ios-simulator, and apple-docs integration
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

## MCP Servers

This plugin includes three integrated MCP servers for comprehensive iOS development:

### XcodeBuildMCP
Xcode project management and scaffolding:
- Scaffold new iOS projects with proper structure
- Configure bundle identifiers and project settings
- Set up device families and orientations
- Generate Xcode project files

**Package**: `xcodebuildmcp@latest`

### ios-simulator
Control iOS Simulator directly from Claude Code:
- Launch apps on simulator
- Take screenshots
- Manage device states
- Streamline mobile development workflows

**Package**: `ios-simulator-mcp`

### apple-docs
Access Apple's official documentation:
- Search Swift API documentation
- Find iOS framework references
- Look up SwiftUI component documentation
- Access best practices and guides

**Package**: `@kimsungwhee/apple-docs-mcp@latest`

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

## License

MIT
