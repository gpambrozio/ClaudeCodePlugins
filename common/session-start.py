#!/usr/bin/env python3

import sys
import json
import os

from version_tracker import check_for_updates


def derive_config_filename(plugin_name: str) -> str:
    """Derive config filename from plugin name by removing spaces and lowercasing first letter."""
    name_no_spaces = plugin_name.replace(" ", "")
    if name_no_spaces:
        return name_no_spaces[0].lower() + name_no_spaces[1:] + ".json"
    return "plugin.json"


def main():
    # Get plugin name from command line argument
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: session-start.py <plugin_name> [additional_message]\n")
        sys.exit(1)

    plugin_name = sys.argv[1]
    additional_message = sys.argv[2] if len(sys.argv) > 2 else None
    config_filename = derive_config_filename(plugin_name)

    try:
        # Get the directory where this script is located
        plugin_dir = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
        md_file = os.path.join(plugin_dir, "session-start.md")

        # Read the markdown file
        if os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                additional_context = f.read()
        else:
            additional_context = ""

        system_message = f"The {plugin_name} plugin is loaded and ready."
        if additional_message:
            system_message += f" {additional_message}"

        # Check for version updates
        changelog, _ = check_for_updates(
            plugin_dir=plugin_dir,
            config_filename=config_filename,
            plugin_name=plugin_name
        )
        if changelog:
            system_message += changelog

        # Output the JSON structure with the content from the markdown file
        response = {
            "systemMessage": system_message,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": additional_context
            }
        }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # On error, exit silently (fail open)
        sys.stderr.write(f"Hook error: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
