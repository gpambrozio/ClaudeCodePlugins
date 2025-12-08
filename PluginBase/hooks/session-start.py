#!/usr/bin/env python3

import sys
import json
import os

from version_tracker import check_for_updates


def main():
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        md_file = os.path.join(script_dir, "session-start.md")

        # Plugin directory is the parent of hooks/
        plugin_dir = os.path.dirname(script_dir)

        # Read the markdown file
        if os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                additional_context = f.read()
        else:
            additional_context = ""

        system_message = "The PluginBase is loaded and ready."

        # Check for version updates
        changelog, _ = check_for_updates(
            plugin_dir=plugin_dir,
            config_filename="pluginBase.json",
            plugin_name="PluginBase"
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
