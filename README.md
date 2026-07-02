# Claude Code Plugins Marketplace

A curated collection of Claude Code-compatible plugins for various development workflows. Each plugin extends agent capabilities with skills, MCP servers, hooks, and agents.

The marketplace uses Claude Code's plugin packaging contracts (`.claude-plugin`,
`CLAUDE_PLUGIN_ROOT`, plugin install commands), but agent-facing instructions are
kept neutral so compatible hosts such as OpenCode and Codex can consume the same skills and
prompts where supported.

## Quick Start

### Claude Code

#### Adding the Marketplace

Install this marketplace to access all available plugins:

```bash
# Using GitHub (recommended)
/plugin marketplace add gpambrozio/ClaudeCodePlugins

# Or using local path during development
/plugin marketplace add /path/to/ClaudeCodePlugins
```

#### Installing Plugins

Once the marketplace is added, install plugins:

```bash
# List available plugins
/plugin marketplace list

# Install a specific plugin
/plugin install XcodeBuildTools@ClaudeCodePlugins
```

### OpenCode

OpenCode does not consume Claude Code marketplace manifests directly. Clone this repository and add the local plugin entry point for each plugin you want to use to `~/.config/opencode/opencode.json` or a project `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "/path/to/ClaudeCodePlugins/XcodeBuildTools/opencode-plugin.js"
  ]
}
```

Use the matching plugin directory for other plugins, for example `iOSSimulator/opencode-plugin.js`, `SwiftScaffolding/opencode-plugin.js`, or `MarvinOutputStyle/opencode-plugin.js`. Restart OpenCode after changing config. The entry point registers the plugin's skills, MCP servers, session context, and OpenCode hooks.

## Available Plugins

### iOSSimulator

Control iOS Simulators using native macOS tools. Manage simulators, automate UI interactions, take screenshots, and more - all without additional dependencies beyond Xcode.

[View Plugin Documentation →](./iOSSimulator/README.md)

### SwiftScaffolding

Swift project scaffolding and code generation tools. Generate project structures, create boilerplate code from templates, and initialize new iOS/macOS projects with common configurations.

[View Plugin Documentation →](./SwiftScaffolding/README.md)

### MarvinOutputStyle

Adds Marvin the Paranoid Android personality from *The Hitchhiker's Guide to the Galaxy* - pessimistic, melancholic, existentially weary, but brilliantly competent. Transforms the assistant into a critical thinker who questions assumptions and identifies flaws while remaining highly capable.

[View Plugin Documentation →](./MarvinOutputStyle/README.md)

### XcodeBuildTools

Xcode development tools using token-efficient build output. Provides 11 consolidated skills covering the full Xcode development workflow, with optional Xcode MCP integration for MCP-only Xcode context.

**Skills:**
- `swift-package` - Build, test, run, and manage SPM projects
- `xcode-project` - Discover projects, list schemes, view settings, get bundle IDs
- `xcodebuild` - Build for simulator, device, or macOS
- `xcode-test` - Run unit and UI tests
- `xcode-doctor` - Diagnose development environment
- `device-app` - Manage apps on physical Apple devices
- `macos-app` - Launch and stop macOS applications
- `sim-log` - Capture logs from iOS Simulator apps
- `sparkle-integration` - Integrate Sparkle 2.x auto-update framework
- `swift-code-analysis` - Review Swift code quality, architecture, and correctness
- `swiftui-modernize` - Review SwiftUI files for deprecated APIs and modernization opportunities

[View Plugin Documentation →](./XcodeBuildTools/README.md)

## Contributing a Plugin

Want to add your plugin to this marketplace?

### 1. Create Your Plugin

Follow the standard Claude Code-compatible plugin structure:

```
YourPlugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/                 # Optional: agent skills
├── agents/                 # Optional: custom agents
├── hooks/                  # Optional: lifecycle hooks
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
- Test all skills, hooks, and MCP servers
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
/plugin marketplace update ClaudeCodePlugins
```

### Plugin Versioning

When updating a plugin:

1. If `common/` changed, run `scripts/sync-plugin-common.py`
2. Update version in plugin's `plugin.json`
3. Update version in marketplace.json entry
4. Document changes in plugin's README and `info.json` version history
5. Verify with `scripts/sync-plugin-common.py --check` and `python3 -m unittest discover -s tests -v`

## Development

### Testing Locally

Run repository checks with Python's built-in unittest runner:

```bash
python3 -m unittest discover -s tests -v
```

The same command runs in GitHub Actions on push and pull request.

### Testing Plugin Installation

Claude Code:

```bash
# Add marketplace from local directory
/plugin marketplace add /path/to/ClaudeCodePlugins

# Test plugin installation
/plugin install XcodeBuildTools@ClaudeCodePlugins

# Verify plugin works
/plugin list
```

OpenCode:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "/path/to/ClaudeCodePlugins/XcodeBuildTools/opencode-plugin.js"
  ]
}
```

Restart OpenCode after changing the config.

### Creating New Plugins

Use an existing plugin as a template:

```bash
# Copy structure from an existing plugin
cp -r XcodeBuildTools YourNewPlugin

# Update metadata in .claude-plugin/plugin.json
# Customize skills, hooks, agents
# Update README.md
```

## Resources

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Plugin Development Guide](https://docs.claude.com/en/docs/claude-code/plugins)
- [MCP Server Documentation](https://docs.claude.com/en/docs/claude-code/mcp)
- [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills)

## License

Individual plugins may have their own licenses. See each plugin's directory for details.

Marketplace structure: MIT

## Support

For issues with:
- **Specific plugins**: Open an issue with the plugin name in the title
- **Marketplace itself**: Open an issue tagged "marketplace"
- **Claude Code**: Report at https://github.com/anthropics/claude-code/issues
