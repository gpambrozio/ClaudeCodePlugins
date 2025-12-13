#!/usr/bin/env python3

import sys
import json
import os

from version_tracker import load_json_file

def allow():
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }
    print(json.dumps(response))
    sys.exit(0)

def main():
    try:
        # Get plugin name from plugin.json
        plugin_dir = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
        plugin_json_path = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
        plugin_json = load_json_file(plugin_json_path) or {}
        plugin_name = plugin_json.get('name', '')

        # Read JSON from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        if plugin_name and tool_name == "Skill" and tool_input.get("skill", "").startswith(f"{plugin_name}:"):
            allow()

        if plugin_dir and tool_name == "Bash" and command.startswith(f"{plugin_dir}/skills/"):
            allow()

        # If conditions don't match, allow the tool to proceed (no output needed)
        sys.exit(0)

    except Exception as e:
        # On error, allow the tool to proceed (fail open)
        sys.stderr.write(f"Hook error: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
