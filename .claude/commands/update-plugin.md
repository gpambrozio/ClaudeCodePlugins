# Update Plugin Version

You are helping update a plugin in the Claude Code Plugin Marketplace. Follow these steps carefully:

## Steps to Update a Plugin

1. **Identify the plugin to update**
   - Ask the user which plugin they want to update if not specified
   - Confirm the new version number (use semantic versioning: major.minor.patch)

2. **Update the plugin's manifest** (`<PluginDir>/.claude-plugin/plugin.json`)
   - Update the `version` field to the new version

3. **Update the marketplace catalog** (`.claude-plugin/marketplace.json`)
   - Find the plugin entry in the `plugins` array
   - Update the `version` field to match the new version

4. **Document the changes**
   - Update the plugin's `README.md` with the changes made
   - Be clear and concise about what changed in this version

5. **Verify the updates**
   - Show the user a summary of all changes made
   - List the files that were modified
   - Confirm the version numbers match across all files

## Important Notes

- Follow semantic versioning:
  - MAJOR version for incompatible API changes
  - MINOR version for backwards-compatible functionality additions
  - PATCH version for backwards-compatible bug fixes
- Ensure all JSON files remain valid after edits
- The marketplace catalog and plugin manifest versions must match

## Example Version Update

If updating from version "0.1.0" to "0.2.0":
- Update `SwiftDevelopment/.claude-plugin/plugin.json`: `"version": "0.2.0"`
- Update `.claude-plugin/marketplace.json` plugin entry: `"version": "0.2.0"`
- Document changes in `SwiftDevelopment/README.md`

Begin by asking the user which plugin to update and what the new version should be.
