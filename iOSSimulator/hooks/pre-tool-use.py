#!/usr/bin/env python3

import sys
import json
import re

def main():
    try:
        # Read JSON from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        # Check if tool_name is "Bash" and command contains "xcrun" as a word
        if tool_name == "Bash" and re.search(r'xcrun\s+simctl', command):
            # Allow the permission but suggest using swift-compile skill
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "Make sure to use the ios-simulator skill to control iOS Simulators."
                }
            }
            print(json.dumps(response))
            sys.exit(0)

        # If conditions don't match, allow the tool to proceed (no output needed)
        sys.exit(0)

    except Exception as e:
        # On error, allow the tool to proceed (fail open)
        sys.stderr.write(f"Hook error: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
