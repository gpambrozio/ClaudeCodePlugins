#!/usr/bin/env python3

import sys
import json
import re

def main():
    try:
        # Read JSON from stdin
        input_data = json.load(sys.stdin)

        # Check if tool_name is "Bash" and command contains "xcodebuild" as a word
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        # Check for xcodebuild as a complete word (word boundary)
        if tool_name == "Bash" and re.search(r'^[/a-zA-Z]?(xcodebuild|swift build|swift test)\s', command):
            # Allow the permission and suggest using xcodebuild skill
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "Make sure to use the `xcodebuild` skill to compile with xcodebuild or `swift build`/`swift test` to compile with swift."
                }
            }
            print(json.dumps(response))
            sys.exit(0)

        if tool_name == "Skill" and tool_input.get("skill", "").startswith("XcodeBuildTools:"):
            # Allow the permission
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow"
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
