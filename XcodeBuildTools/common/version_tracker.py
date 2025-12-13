#!/usr/bin/env python3
"""
Version tracking utilities for Claude Code plugins.

Compares a project's last-seen version against a plugin's version history
and returns changelog information for any new versions.
"""

import json
import os


def parse_version(version_str):
    """Parse a version string like '0.1.0' into a tuple of integers."""
    if not version_str:
        return (0, 0, 0)
    try:
        parts = version_str.split('.')
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def get_new_versions(versions_list, last_version):
    """Get all versions newer than last_version, sorted oldest to newest."""
    last_parsed = parse_version(last_version)
    new_versions = []
    for entry in versions_list:
        v = entry.get('version', '')
        if parse_version(v) > last_parsed:
            new_versions.append(entry)
    # Sort by version (oldest first so changes are listed chronologically)
    new_versions.sort(key=lambda x: parse_version(x.get('version', '')))
    return new_versions


def load_json_file(file_path):
    """Load a JSON file, returning empty dict/list on error."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_json_file(file_path, data):
    """Save data to a JSON file, creating parent directories if needed."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except (IOError, OSError):
        return False


def check_for_updates(plugin_dir, config_filename, plugin_name=None):
    """
    Check for plugin updates and return changelog if there are new versions.

    Args:
        plugin_dir: Path to the plugin directory (containing info.json)
        config_filename: Name of the config file to store in .claude/ (e.g., "testPlugin.json")
        plugin_name: Optional name for the changelog header (defaults to "Plugin")

    Returns:
        tuple: (changelog_text, updated) where changelog_text is the markdown
               changelog (empty string if no updates) and updated is a boolean
               indicating whether the config was updated
    """
    project_path = os.environ.get('CLAUDE_PROJECT_DIR', '')
    if not project_path:
        return "", False

    info_file = os.path.join(plugin_dir, "info.json")
    if not os.path.exists(info_file):
        return "", False

    claude_dir = os.path.join(project_path, ".claude")
    config_file = os.path.join(claude_dir, config_filename)

    # Load project config
    config = load_json_file(config_file) or {}
    last_version = config.get('lastVersion', '')

    # Load plugin info and extract versions list
    plugin_info = load_json_file(info_file) or {}
    versions_list = plugin_info.get('versions', [])

    # Find new versions
    new_versions = get_new_versions(versions_list, last_version)

    if not new_versions:
        return "", False

    # Build changelog
    header = plugin_name or "Plugin"
    changelog = f"\n\n## {header} Updates\n"
    for entry in new_versions:
        v = entry.get('version', 'unknown')
        changes = entry.get('changes', 'No description')
        changelog += f"\n### v{v}\n{changes}\n"

    # Update lastVersion
    latest_version = new_versions[-1].get('version', '')
    if latest_version:
        config['lastVersion'] = latest_version
        save_json_file(config_file, config)

    return changelog, True
