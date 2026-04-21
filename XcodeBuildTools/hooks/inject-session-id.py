#!/usr/bin/env python3
#
# inject-session-id.py — PreToolUse hook
#
# Prefixes every Bash command with:
#   export PATH="<plugin>/bin:$PATH";
#   export CLAUDE_SESSION_ID='<id>';
#   export SANDBOX_DERIVED_DATA="${TMPDIR:-/tmp}/claude-sandbox/<id>/build";
#   export SANDBOX_PACKAGES="${TMPDIR:-/tmp}/claude-sandbox/<id>/packages";
#   …
#
# Why the PATH prepend: Claude Code appends plugin bin/ directories to
# PATH after the system dirs, so our wrappers at bin/xcodebuild and
# bin/swift sit behind /usr/bin/xcodebuild and /usr/bin/swift and never
# get picked by a bare `xcodebuild`/`swift` call. Prepending here makes
# the wrappers the first match so nested calls from Makefiles, fastlane,
# and other build scripts get sandboxed transparently.
#
# Why the session-id export: the wrappers key the per-session sandbox
# off $CLAUDE_SESSION_ID (seeded by setup-sandbox.sh). $PPID is not stable
# across hook and Bash-tool execution contexts, so we can't use it as a
# session key — the hook stdin payload's session_id is the stable handle.
#
# Why SANDBOX_DERIVED_DATA / SANDBOX_PACKAGES: build scripts and tools
# that want to read build products (tests, bundle inspection, codesign,
# xcresult parsing) or inspect cached SPM checkouts need the paths the
# xcodebuild/swift wrappers will use. Exposing them as env vars means
# scripts don't have to reconstruct the formula. The `${TMPDIR:-/tmp}`
# expansion happens in the Bash tool's shell, so it picks up the tool
# context's TMPDIR rather than the hook's.
#
# Why unconditional (not regex-gated): build scripts invoke xcodebuild
# and swift without those tokens appearing in the outer Bash command, so
# a text match can't catch indirect calls. Environment variables and PATH
# propagate to subprocesses, so setting them on the outer shell is enough
# for any descendant to pick up the wrappers and sandbox.

import json
import os
import re
import shlex
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

        prefix_parts = []

        # Prepend plugin bin/ to PATH so bin/xcodebuild and bin/swift
        # shadow /usr/bin. shlex.quote handles any odd chars in the path.
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        if plugin_root:
            bin_dir = os.path.join(plugin_root, "bin")
            prefix_parts.append(f"export PATH={shlex.quote(bin_dir)}:$PATH;")

        prefix_parts.append(f"export CLAUDE_SESSION_ID='{session_id}';")

        # Double-quoted so ${TMPDIR:-/tmp} expands in the Bash tool's
        # shell. session_id is already validated against [A-Za-z0-9_-]+
        # so safe to embed.
        sandbox_base = f"${{TMPDIR:-/tmp}}/claude-sandbox/{session_id}"
        prefix_parts.append(
            f'export SANDBOX_DERIVED_DATA="{sandbox_base}/build";'
        )
        prefix_parts.append(
            f'export SANDBOX_PACKAGES="{sandbox_base}/packages";'
        )

        new_command = " ".join(prefix_parts) + " " + command

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
