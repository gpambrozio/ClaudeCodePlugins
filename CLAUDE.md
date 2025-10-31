# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **Claude Code Plugin Marketplace** repository that distributes plugins to Claude Code users. It contains a marketplace catalog and individual plugin packages that extend Claude Code's capabilities.

## Architecture

### Marketplace Structure

The repository has a two-level architecture:

1. **Marketplace Level** (root):
   - `.claude-plugin/marketplace.json` - The marketplace catalog that lists all available plugins
   - Each plugin is a subdirectory at the root level (e.g., `SwiftDevelopment/`)

2. **Plugin Level** (subdirectories):
   - Each plugin subdirectory is a self-contained Claude Code plugin
   - Contains its own `.claude-plugin/plugin.json` manifest
   - May include: slash commands (`commands/`), skills (`skills/`), agents (`agents/`), and MCP servers (`.mcp.json`)

### Key Schema Requirements

**Critical**: Both marketplace and plugin manifests have strict schema requirements:

- `author` field MUST be an object: `{"name": "Author Name"}` (NOT a string)
- Plugin entries in marketplace.json should NOT include `displayName` field
- Plugin manifests should NOT include `claudeCode` field

## Plugin Installation Flow

Users add the marketplace, then install plugins from it:

```bash
# Add marketplace (GitHub or local path)
/plugin marketplace add gpambrozio/ClaudeCodePlugins
/plugin marketplace add /path/to/ClaudeCodePlugins

# List available plugins
/plugin marketplace list

# Install a plugin from the marketplace
/plugin install SwiftDevelopment@ClaudeCodePlugins
```

## Development Workflow

### Adding a New Plugin

1. Create plugin directory at repository root (e.g., `YourPlugin/`)
2. Create plugin manifest at `YourPlugin/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "your-plugin",
     "version": "0.1.0",
     "description": "What it does",
     "author": {"name": "Your Name"},
     "keywords": ["tag1", "tag2"],
     "license": "MIT"
   }
   ```
3. Add plugin entry to `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "your-plugin",
     "description": "What it does",
     "source": "./YourPlugin",
     "version": "0.1.0",
     "author": {"name": "Your Name"},
     "keywords": ["tag1", "tag2"],
     "license": "MIT"
   }
   ```
4. Create plugin components:
   - `commands/` - Slash commands (`.md` files)
   - `skills/` - Agent skills (directories with `SKILL.md`)
   - `agents/` - Custom agents (`.md` files)
   - `.mcp.json` - MCP server configurations

### Updating Plugins

When updating a plugin:
1. Update version in plugin's `plugin.json`
2. Update version in marketplace catalog entry (`.claude-plugin/marketplace.json`)
3. Update `lastUpdated` timestamp in marketplace.json
4. Document changes in plugin's README.md

### Testing Locally

Test the marketplace and plugins locally before pushing:

```bash
# Add local marketplace
/plugin marketplace add /path/to/ClaudeCodePlugins

# Install plugin from local marketplace
/plugin install SwiftDevelopment@ClaudeCodePlugins

# Verify installation
/plugin list
```

## Plugin Component Guidelines

### Slash Commands
- Filename becomes command name: `analyze.md` → `/analyze`
- Write the command prompt in markdown
- Located in plugin's `commands/` directory

### MCP Servers
- Configured in plugin's `.mcp.json`
- Standard format:
  ```json
  {
    "mcpServers": {
      "ServerName": {
        "command": "npx",
        "args": ["-y", "package-name@latest"]
      }
    }
  }
  ```

### Skills and Agents
- Skills: directories in `skills/` with `SKILL.md`
- Agents: `.md` files in `agents/`
- Currently placeholder directories in SwiftDevelopment plugin

## Git Workflow

The repository uses amend-and-force-push for iterative commits:

```bash
# Make changes
git add <files>
git commit --amend --no-edit
git push --force origin main
```

This keeps a clean commit history during initial development.

## Current Plugins

### SwiftDevelopment
Swift and iOS development toolkit with:
- `/analyze` command - Comprehensive Swift code analysis
- Three MCP servers:
  - `XcodeBuildMCP` - Xcode project scaffolding
  - `ios-simulator` - iOS Simulator control
  - `apple-docs` - Apple documentation search
