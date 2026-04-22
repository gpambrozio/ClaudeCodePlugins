#!/usr/bin/env python3
#
# inject-session-id.py — PreToolUse hook
#
# Prefixes every Bash command with:
#   export PATH="<plugin>/bin:$PATH";
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
# Why SANDBOX_DERIVED_DATA / SANDBOX_PACKAGES: the bin/ wrappers read
# them directly to pick up -derivedDataPath / -clonedSourcePackagesDirPath
# / --cache-path. Build scripts and tools that need to read build
# products (tests, bundle inspection, codesign, xcresult parsing) or
# inspect cached SPM checkouts can use the same vars instead of
# reconstructing the formula. For fresh sandboxes the value defers to
# bash-side `${TMPDIR:-/tmp}` expansion so the tool context's TMPDIR
# applies; for sandboxes inherited across /clear (`${TMPDIR}/claude-
# sandbox/<id>` is a symlink into the original anchor), we resolve the
# symlink here and embed the anchor's real path — SPM and Xcode
# persist whichever path they're given into state files, so handing
# them the anchor keeps those state files pointing at a stable
# directory even if the symlink is later swept.
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

        # If the per-session sandbox is a symlink (the /clear-inherit
        # case — see setup-sandbox.sh), resolve it so the exported paths
        # point at the anchor's real directory instead of the symlink.
        # SPM and Xcode persist whichever absolute path they're given
        # into state files; handing them the anchor keeps those state
        # files pointing at a stable directory even if this session's
        # symlink is swept while the anchor lives on.
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        sandbox_fs_path = os.path.join(tmpdir, "claude-sandbox", session_id)
        anchor = None
        try:
            if os.path.islink(sandbox_fs_path):
                resolved = os.path.realpath(sandbox_fs_path)
                if os.path.isdir(resolved):
                    anchor = resolved
        except OSError:
            pass

        if anchor is not None:
            # Real absolute path from realpath. shlex.quote handles the
            # unlikely case of shell-special chars in $TMPDIR.
            quoted_base = shlex.quote(anchor)
            prefix_parts.append(
                f"export SANDBOX_DERIVED_DATA={quoted_base}/build;"
            )
            prefix_parts.append(
                f"export SANDBOX_PACKAGES={quoted_base}/packages;"
            )
        else:
            # Fresh sandbox (or not yet created). Defer to bash-side
            # ${TMPDIR:-/tmp} expansion so the tool context's TMPDIR
            # applies. session_id is already validated against
            # [A-Za-z0-9_-]+ so safe to embed.
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
