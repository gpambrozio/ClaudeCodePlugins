#!/usr/bin/env python3
"""teardown-sandbox.py — Remove isolated Xcode build environment on session end.

Reads session_id from the SessionEnd hook stdin payload and removes the
matching $TMPDIR/claude-sandbox/<session_id>/ directory.

Multi-GB DerivedData trees can take longer than Claude's SessionEnd hook
timeout. When the hook is killed mid-rm, the sandbox is left partially
removed. To survive that, we spawn rm in a new session (setsid via
Popen's start_new_session) so Claude's process-group SIGTERM can't
reach it. setup-sandbox.sh's owner.pid sweep is the safety net for
anything that still falls through (laptop sleep, hard crash, etc.).
"""

import json
import os
import re
import subprocess
import sys

SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    session_id = payload.get("session_id", "")
    if not session_id or not SESSION_ID_RE.match(session_id):
        return

    tmpdir = os.environ.get("TMPDIR", "/tmp")
    sandbox_base = os.path.join(tmpdir, "claude-sandbox", session_id)
    if not os.path.isdir(sandbox_base):
        return

    subprocess.Popen(
        ["/bin/rm", "-rf", sandbox_base],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
