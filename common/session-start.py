#!/usr/bin/env python3

import sys
import json
import os
import re

from version_tracker import check_for_updates, load_json_file


def derive_config_filename(plugin_name: str) -> str:
    """Derive config filename from plugin name by removing spaces and lowercasing first letter."""
    name_no_spaces = plugin_name.replace(" ", "")
    if name_no_spaces:
        return name_no_spaces[0].lower() + name_no_spaces[1:] + ".json"
    return "plugin.json"


def main():
    try:
        # Get the plugin directory from environment
        plugin_dir = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
        if not plugin_dir:
            sys.exit(0)

        # Load plugin name from plugin.json
        plugin_json_path = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
        plugin_json = load_json_file(plugin_json_path) or {}
        plugin_name = plugin_json.get('name', 'Plugin')

        # Load welcome message from info.json
        info_json_path = os.path.join(plugin_dir, "info.json")
        info_json = load_json_file(info_json_path) or {}
        welcome_message = info_json.get('welcomeMessage', '')

        config_filename = derive_config_filename(plugin_name)
        md_file = os.path.join(plugin_dir, "session-start.md")

        # Read the markdown file
        if os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                additional_context = f.read()
        else:
            additional_context = ""

        # Detect Xcode MCP availability (fail-open: treat as unavailable on error)
        xcode_mcp_likely = False
        try:
            from detect_xcode_mcp import detect_xcode_mcp
            detection = detect_xcode_mcp()
            xcode_mcp_likely = detection.get("xcode_mcp_likely", False)
        except Exception:
            pass

        # Process conditional blocks in markdown (no-op if markers absent)
        if xcode_mcp_likely:
            # Keep IF_XCODE_MCP content, remove IF_NO_XCODE_MCP content
            additional_context = re.sub(
                r'<!-- IF_XCODE_MCP -->\n?', '', additional_context)
            additional_context = re.sub(
                r'<!-- END_XCODE_MCP -->\n?', '', additional_context)
            additional_context = re.sub(
                r'<!-- IF_NO_XCODE_MCP -->.*?<!-- END_NO_XCODE_MCP -->\n?',
                '', additional_context, flags=re.DOTALL)
        else:
            # Keep IF_NO_XCODE_MCP content, remove IF_XCODE_MCP content
            additional_context = re.sub(
                r'<!-- IF_NO_XCODE_MCP -->\n?', '', additional_context)
            additional_context = re.sub(
                r'<!-- END_NO_XCODE_MCP -->\n?', '', additional_context)
            additional_context = re.sub(
                r'<!-- IF_XCODE_MCP -->.*?<!-- END_XCODE_MCP -->\n?',
                '', additional_context, flags=re.DOTALL)

        system_message = f"The {plugin_name} plugin is loaded and ready."
        if xcode_mcp_likely:
            system_message += " Xcode MCP server detected."
        if welcome_message:
            system_message += f" {welcome_message}"

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
