---
name: update-plugin
description: Use when updating, versioning, tagging, or releasing a plugin in this Claude Code-compatible plugin marketplace.
---

# Update Plugin

Use this workflow when preparing a plugin update in this marketplace.

## Workflow

1. Inspect the diff.
   - If `common/` changed, every plugin is affected.
   - Run `scripts/sync-plugin-common.py` before editing versions so each plugin package has current copied helpers.
   - If `common/hooks.json` changed, propagate the hook shape to each plugin's `hooks/hooks.json` while preserving plugin-specific command names.
2. Identify the plugin or plugins to update.
   - Ask only if the changed plugin is unclear from the diff.
   - Suggest a semantic version bump from the change scope.
3. Update version metadata.
   - Update `<PluginDir>/.claude-plugin/plugin.json`.
   - Update the matching entry in `.claude-plugin/marketplace.json`.
4. Document the change.
   - Update the plugin README changelog.
   - Add a matching entry to the plugin `info.json` `versions` array.
   - If skills were added, removed, or renamed, update the plugin `info.json` `skills` array.
   - If legacy command prompts are present, migrate them to skills before release.
5. Verify.
   - Run `scripts/sync-plugin-common.py --check`.
   - Run `python3 -m unittest discover -s tests -v`.
   - Confirm plugin manifest, marketplace, README, and `info.json` versions match.
6. Commit and tag after the commit lands.
   - Tag format: `{PluginName}--v{version}`.
   - Push the tag with `git push origin {PluginName}--v{version}`.
   - If multiple plugins were bumped, create and push one tag per plugin.

## Notes

- The installed plugin package must be self-contained. Do not edit copied `*/common/` files by hand; edit root `common/` and rerun `scripts/sync-plugin-common.py`.
- JSON files must remain valid.
- Plugin names must match folder names exactly.
