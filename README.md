# Claude Code Plugins Marketplace

A curated collection of Claude Code plugins for various development workflows. Each plugin extends Claude Code's capabilities with custom slash commands, MCP servers, skills, and agents.

## Quick Start

### Adding the Marketplace

Install this marketplace to access all available plugins:

```bash
# Using GitHub (recommended)
/plugin marketplace add gpambrozio/ClaudeCodePlugins

# Or using local path during development
/plugin marketplace add /path/to/ClaudeCodePlugins
```

### Installing Plugins

Once the marketplace is added, install plugins:

```bash
# List available plugins
/plugin marketplace list

# Install a specific plugin
/plugin install swift-development@claude-code-plugins
```

## Available Plugins

### SwiftDevelopment

Swift and iOS development toolkit with MCP servers and slash commands.

**Features:**
- Comprehensive Swift code analysis
- iOS project scaffolding with Xcode integration
- iOS Simulator control
- Apple documentation access
- Memory management and anti-pattern detection

**Slash Commands:**
- `/analyze` - Comprehensive Swift code analysis with severity levels

**MCP Servers:**
- `XcodeBuildMCP` - Xcode project management and scaffolding
- `ios-simulator` - iOS Simulator control and automation
- `apple-docs` - Apple's official documentation search

[View Plugin Documentation →](./SwiftDevelopment/README.md)

## Repository Structure

```
ClaudeCodePlugins/
├── .claude-plugin/
│   └── marketplace.json     # Marketplace catalog
├── SwiftDevelopment/        # Swift/iOS development plugin
│   ├── .claude-plugin/
│   ├── commands/
│   ├── skills/
│   ├── agents/
│   ├── .mcp.json
│   └── README.md
└── README.md               # This file
```

## Contributing a Plugin

Want to add your plugin to this marketplace?

### 1. Create Your Plugin

Follow the standard Claude Code plugin structure:

```
YourPlugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/               # Optional: slash commands
├── skills/                 # Optional: agent skills
├── agents/                 # Optional: custom agents
├── .mcp.json              # Optional: MCP servers
└── README.md
```

### 2. Add to Repository

1. Fork this repository
2. Add your plugin directory at the root level
3. Update `.claude-plugin/marketplace.json`:

```json
{
  "plugins": [
    {
      "name": "your-plugin",
      "description": "What your plugin does",
      "source": "./YourPlugin",
      "version": "0.1.0",
      "author": {
        "name": "your-name"
      },
      "keywords": ["relevant", "tags"],
      "license": "MIT"
    }
  ]
}
```

4. Submit a pull request

### 3. Plugin Requirements

- Include a comprehensive README.md
- Follow semantic versioning
- Test all commands and MCP servers
- Document prerequisites and dependencies
- Include examples and usage instructions

## Marketplace Management

### For Maintainers

Update the marketplace catalog:

```bash
# Edit .claude-plugin/marketplace.json
# Add/remove plugin entries
# Update versions and metadata
```

After changes, users can refresh:

```bash
/plugin marketplace update claude-code-plugins
```

### Plugin Versioning

When updating a plugin:

1. Update version in plugin's `plugin.json`
2. Update version in marketplace.json entry
3. Update `lastUpdated` timestamp in marketplace.json
4. Document changes in plugin's README

## Development

### Testing Locally

```bash
# Add marketplace from local directory
/plugin marketplace add /path/to/ClaudeCodePlugins

# Test plugin installation
/plugin install swift-development@claude-code-plugins

# Verify plugin works
/plugin list
```

### Creating New Plugins

Use the SwiftDevelopment plugin as a template:

```bash
# Copy structure
cp -r SwiftDevelopment YourNewPlugin

# Update metadata in .claude-plugin/plugin.json
# Customize commands, skills, agents
# Update README.md
```

## Plugin Categories

Plugins in this marketplace are organized by:

- **Language/Framework**: Swift, Python, JavaScript, etc.
- **Development Phase**: Analysis, scaffolding, testing, deployment
- **Integration Type**: MCP servers, slash commands, skills, agents

## Resources

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Plugin Development Guide](https://docs.claude.com/en/docs/claude-code/plugins)
- [MCP Server Documentation](https://docs.claude.com/en/docs/claude-code/mcp)
- [Slash Commands Reference](https://docs.claude.com/en/docs/claude-code/slash-commands)

## License

Individual plugins may have their own licenses. See each plugin's directory for details.

Marketplace structure: MIT

## Support

For issues with:
- **Specific plugins**: Open an issue with the plugin name in the title
- **Marketplace itself**: Open an issue tagged "marketplace"
- **Claude Code**: Report at https://github.com/anthropics/claude-code/issues

---

**Note**: Remember to update your GitHub repository URL in `.claude-plugin/marketplace.json` once you've pushed this to GitHub.
