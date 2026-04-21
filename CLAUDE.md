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

**IMPORTANT**: The plugin `name` field MUST match the folder name exactly. This ensures consistency and easier maintenance.

1. Create plugin directory at repository root (e.g., `YourPlugin/`)
2. Create plugin manifest at `YourPlugin/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "YourPlugin",
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
     "name": "YourPlugin",
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
4. Document changes in plugin's README.md and the `versions` array in the plugin's `info.json`
5. Commit and push the version bump
6. Tag the release (see "Tagging Plugin Releases" below)

### Tagging Plugin Releases

Every version bump must be tagged so Claude Code can resolve it for plugin dependencies (https://code.claude.com/docs/en/plugin-dependencies#tag-plugin-releases-for-version-resolution).

- **Tag format**: `{PluginName}--v{version}` — e.g. `XcodeBuildTools--v0.5.6`. `{PluginName}` must match the plugin's folder name and the `name` in `plugin.json` exactly; `{version}` must match the `version` in `plugin.json` at the tagged commit.
- **What to tag**: the commit that contains the updated `plugin.json` version. For direct pushes to `main`, that's the bump commit itself. For PRs, tag after the PR merges — use the merge commit on `main` (or the squash commit) that carries the new version.
- **Push the tag**: `git push origin {PluginName}--v{version}`. Tags are not pushed by default, so this is a separate step from `git push`.
- **One tag per bumped plugin**: changes under `common/` affect every plugin; if you bump multiple plugins in one PR, create and push one tag per bumped plugin.
- **Verify**: `git tag -l '{PluginName}*' --sort=-v:refname` should show the new tag; `git show {tag}:{PluginName}/.claude-plugin/plugin.json` should print the matching version.

The `/update-plugin` skill automates these steps end-to-end.

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

### Hooks
- Configured in plugin's `hooks/hooks.json`
- Both Python scripts and markdown content files go in `hooks/` directory
- Standard pattern (SessionStart example):

**hooks/hooks.json:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.py"
          }
        ]
      }
    ]
  }
}
```

**hooks/session-start.py:**
```python
#!/usr/bin/env python3
import sys, json, os

def main():
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Look for the markdown file in the same directory
        md_file = os.path.join(script_dir, "session-start.md")

        if not os.path.exists(md_file):
            sys.exit(0)

        with open(md_file, 'r', encoding='utf-8') as f:
            additional_context = f.read()

        response = {
            "systemMessage": "Plugin loaded message",
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": additional_context
            }
        }
        print(json.dumps(response))
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Hook error: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**hooks/session-start.md:**
- Contains the actual instructions/context in markdown format
- Easier to edit than embedding in scripts
- See `SwiftDevelopment/hooks/session-start.md` or `MarvinOutputStyle/hooks/session-start.md` for examples

### Skills and Agents
- Skills: directories in `skills/` with `SKILL.md`
- Agents: `.md` files in `agents/`
- Currently placeholder directories in SwiftDevelopment plugin

## Git Workflow

### Normal commits

Commits usually land on `main` directly or via a PR merge. Amend-and-force-push (`git commit --amend --no-edit && git push --force origin main`) is only appropriate for WIP that hasn't been tagged or referenced elsewhere — never amend a commit that a release tag points at.

### Release tagging is mandatory

Any commit that bumps a plugin's `version` in `plugin.json` must be followed by a `{PluginName}--v{version}` tag pushed to `origin`. See "Tagging Plugin Releases" above. This applies to:

- **Direct pushes to `main`**: tag the bump commit immediately after `git push`.
- **Merged PRs**: after the PR lands on `main`, tag the resulting merge/squash commit. Do not tag inside the PR branch — tags should live on `main`.
- **Missed tags**: if a version bump was pushed without a tag, add the tag retroactively pointing at the historical bump commit (`git tag {tag} <sha> && git push origin {tag}`) rather than bumping the version again.
