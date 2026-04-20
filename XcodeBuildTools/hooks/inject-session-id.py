#!/usr/bin/env python3
#
# inject-session-id.py — PreToolUse hook
#
# Prefixes every Bash command with `export CLAUDE_SESSION_ID='<id>';` so
# the sandbox wrappers (bin/xcodebuild-sandbox, bin/swift-sandbox) can
# discover the per-session sandbox directory created by setup-sandbox.sh.
#
# $PPID is not stable across hook and Bash-tool execution contexts, so we
# can't use it as a session key. The hook stdin payload includes a stable
# session_id that we propagate via an environment variable.

import json
import re
import sys


def main():
    try:
        input_data = json.load(sys.stdin)

        if input_data.get("tool_name", "") != "Bash":
            sys.exit(0)

        session_id = input_data.get("session_id", "")
        # Reject anything not matching the expected UUID-ish shape — stops
        # quote-escaping tricks from reaching the shell.
        if not re.match(r"^[A-Za-z0-9_-]+$", session_id):
            sys.exit(0)

        command = input_data.get("tool_input", {}).get("command", "")
        if not command:
            sys.exit(0)

        new_command = f"export CLAUDE_SESSION_ID='{session_id}'; {command}"

        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {"command": new_command},
            }
        }
        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"inject-session-id error: {e}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
