#!/usr/bin/env python3
"""teardown-sandbox.py — Remove isolated Xcode build environment on session end.

Reads session_id from the SessionEnd hook stdin payload and removes the
matching $TMPDIR/claude-sandbox/<session_id>/ entry.

The entry can be either a real directory (fresh session, no /clear) or
a symlink to an anchor directory (session inherited a prior sandbox
across /clear — see setup-sandbox.sh). Handling differs:

* Real dir: rm -rf the dir. Existing behavior.
* Symlink: unlink just the symlink; separately rm -rf the anchor only
  when no other live symlink in the sandbox root still references it.
  Using rm -rf on the symlink path directly is risky because of trailing-
  slash semantics and because we'd rather walk the references explicitly.

Multi-GB DerivedData trees can take longer than Claude's SessionEnd hook
timeout. When the hook is killed mid-rm, the sandbox is left partially
removed. To survive that, the anchor removal is spawned in a new session
(setsid via Popen's start_new_session) so Claude's process-group SIGTERM
can't reach it. setup-sandbox.sh's owner.pid sweep is the safety net for
anything that still falls through (laptop sleep, hard crash, etc.).
"""

import json
import os
import re
import subprocess
import sys

SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def spawn_rm(path: str) -> None:
    """Fire-and-forget rm -rf in a detached session so SIGTERM can't reach it."""
    subprocess.Popen(
        ["/bin/rm", "-rf", path],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )


def anchor_still_referenced(sandbox_root: str, anchor: str) -> bool:
    """Return True if any live symlink under sandbox_root resolves to anchor."""
    try:
        entries = os.listdir(sandbox_root)
    except OSError:
        return False
    for entry in entries:
        path = os.path.join(sandbox_root, entry)
        if not os.path.islink(path):
            continue
        try:
            if os.path.realpath(path) == anchor:
                return True
        except OSError:
            continue
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    session_id = payload.get("session_id", "")
    if not session_id or not SESSION_ID_RE.match(session_id):
        return

    tmpdir = os.environ.get("TMPDIR", "/tmp")
    sandbox_root = os.path.join(tmpdir, "claude-sandbox")
    sandbox_base = os.path.join(sandbox_root, session_id)

    # Normalize sandbox_root for comparisons against realpath output.
    # macOS' $TMPDIR can include symlinks (/var → /private/var) and
    # bash's ${TMPDIR:-/tmp}/claude-sandbox can produce double slashes
    # when $TMPDIR already ends in `/`. realpath collapses both, so
    # compare realpath(anchor)'s parent against realpath(sandbox_root).
    try:
        sandbox_root_real = os.path.realpath(sandbox_root)
    except OSError:
        sandbox_root_real = sandbox_root

    if os.path.islink(sandbox_base):
        # Inherited sandbox. Resolve anchor before unlinking.
        try:
            anchor = os.path.realpath(sandbox_base)
        except OSError:
            anchor = ""

        try:
            os.unlink(sandbox_base)
        except OSError:
            pass

        # Best-effort anchor GC. Only remove if:
        #   1. We resolved to something that actually is a dir.
        #   2. The anchor lives under our sandbox_root (don't chase
        #      symlinks pointing outside the managed tree).
        #   3. No other live symlink in sandbox_root still references
        #      it (shouldn't happen post-sweep, but defensive).
        # If any check fails, leave anchor GC to the next session's
        # setup-sandbox.sh peer sweep — owner.pid will be stale by then.
        if (
            anchor
            and os.path.isdir(anchor)
            and os.path.dirname(anchor) == sandbox_root_real
            and not anchor_still_referenced(sandbox_root_real, anchor)
        ):
            spawn_rm(anchor)
        return

    if os.path.isdir(sandbox_base):
        spawn_rm(sandbox_base)


if __name__ == "__main__":
    main()
