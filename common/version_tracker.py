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


def migrate_config_from_project_dir(config_filename, new_config_file):
    """
    Migrate a config file from the old .claude/ project directory to the new
    CLAUDE_PLUGIN_DATA location, if it exists and hasn't been migrated yet.

    Args:
        config_filename: Name of the config file (e.g., "testPlugin.json")
        new_config_file: Full path to the new config file location

    Returns:
        bool: True if a file was migrated, False otherwise
    """
    if os.path.exists(new_config_file):
        return False

    project_path = os.environ.get('CLAUDE_PROJECT_DIR', '')
    if not project_path:
        return False

    old_config_file = os.path.join(project_path, ".claude", config_filename)
    if not os.path.exists(old_config_file):
        return False

    # Migrate: copy old config to new location, then remove old file
    old_data = load_json_file(old_config_file)
    if old_data is not None:
        if save_json_file(new_config_file, old_data):
            try:
                os.remove(old_config_file)
            except OSError:
                pass
            return True
    return False


def check_for_updates(plugin_dir, config_filename, plugin_name=None):
    """
    Check for plugin updates and return changelog if there are new versions.

    Args:
        plugin_dir: Path to the plugin directory (containing info.json)
        config_filename: Name of the config file to store in CLAUDE_PLUGIN_DATA (e.g., "testPlugin.json")
        plugin_name: Optional name for the changelog header (defaults to "Plugin")

    Returns:
        tuple: (changelog_text, updated) where changelog_text is the markdown
               changelog (empty string if no updates) and updated is a boolean
               indicating whether the config was updated
    """
    data_dir = os.environ.get('CLAUDE_PLUGIN_DATA', '')
    if not data_dir:
        return "", False

    info_file = os.path.join(plugin_dir, "info.json")
    if not os.path.exists(info_file):
        return "", False

    config_file = os.path.join(data_dir, config_filename)

    # Migrate from old .claude/ project directory if needed
    migrate_config_from_project_dir(config_filename, config_file)

    # Load plugin info and extract versions list
    plugin_info = load_json_file(info_file) or {}
    versions_list = plugin_info.get('versions', [])

    # Load project config - check if file exists first
    config_exists = os.path.exists(config_file)
    config = load_json_file(config_file) or {}

    # If no config file exists (first run), just create it with latest version
    # without showing any changelog - the user doesn't need version history
    if not config_exists:
        if versions_list:
            # Find the latest version
            latest = max(versions_list, key=lambda x: parse_version(x.get('version', '')))
            config['lastVersion'] = latest.get('version', '')
            save_json_file(config_file, config)
        return "", False

    last_version = config.get('lastVersion', '')

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
