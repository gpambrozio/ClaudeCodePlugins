#!/usr/bin/env python3

import sys
import json
import os
import re

from version_tracker import load_json_file, save_json_file

def allow():
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }
    print(json.dumps(response))
    sys.exit(0)

def deny(message: str):
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message
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

        info_file = os.path.join(plugin_dir, "info.json")
        info_data = load_json_file(info_file) or {}

        # Read JSON from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        if plugin_name and tool_name == "Skill" and tool_input.get("skill", "") in info_data.get('skills', []):
            allow()

        if tool_name == "Bash" and f"{plugin_dir}/skills/" in command:
            allow()

        # Check pre-tool-use rules from info.json
        if tool_name == "Bash" and command:
            rules = info_data.get('pre-tool-use-rules', [])

            for rule in rules:
                rule_name = rule.get('name', '')
                match_pattern = rule.get('match', '')
                not_match_pattern = rule.get('not_match', '')
                decision = rule.get('decision', 'deny')
                message = rule.get('message', 'Command denied by rule')

                if not match_pattern or not re.search(match_pattern, command):
                    continue

                # If not_match is specified and matches, skip this rule
                if not_match_pattern and re.search(not_match_pattern, command):
                    continue

                # Rule matched - apply decision
                if decision == 'allow':
                    allow()

                if decision == 'deny':
                    deny(message)

                # decision == 'deny_once' - check session tracking
                tmpdir = os.environ.get('TMPDIR', '/tmp')
                session_file = os.path.join(tmpdir, f"{plugin_name}.json")

                session_data = load_json_file(session_file) or {}
                session_id = input_data.get("session_id", "")
                session_rules = session_data.get(session_id, [])

                if rule_name in session_rules:
                    # Already seen this rule in this session, allow
                    continue

                # First time seeing this rule in this session - deny and record
                session_rules.append(rule_name)
                session_data[session_id] = session_rules
                save_json_file(session_file, session_data)
                deny(message)

        # If conditions don't match, allow the tool to proceed (no output needed)
        sys.exit(0)

    except Exception as e:
        # On error, allow the tool to proceed (fail open)
        sys.stderr.write(f"Hook error: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
