import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "XcodeBuildTools"
ROUTER_PATH = PLUGIN_ROOT / "hooks" / "session-start.py"
COMMON_SESSION_START = PLUGIN_ROOT / "common" / "session-start.py"
APPROVE_PATH = PLUGIN_ROOT / "hooks" / "approve-xcode-mcp.sh"

HEADLESS_STATUS = {
    "openWorkspaces": [],
    "permission": {
        "enabled": True,
        "pendingAgentApprovals": [
            {
                "id": "AGENT-1",
                "status": "pending",
                "subject": {
                    "agent": {
                        "_0": {
                            "name": "claude-code",
                            "trust": {"unsigned": {"path": "/usr/bin/python3"}},
                        }
                    }
                },
            }
        ],
        "pendingFolderApprovals": [
            {
                "id": "FOLDER-OTHER",
                "status": "pending",
                "subject": {
                    "folder": {
                        "_0": {
                            "projectName": "Other",
                            "subtreeRoot": "/nonexistent/other-worktree",
                        }
                    }
                },
            }
        ],
        "unsafeAlwaysAllowAllAgents": False,
    },
    "running": True,
}

# Fake xcrun: `--find mcpbridge` follows FAKE_MCPBRIDGE, `mcp-server status`
# prints FAKE_MCP_STATUS (or fails when it is empty, like Xcode 26).
FAKE_XCRUN = """#!/bin/sh
if [ "$1" = "--find" ]; then
    [ "${FAKE_MCPBRIDGE:-1}" = "1" ] && { echo /fake/mcpbridge; exit 0; }
    exit 1
fi
if [ "$1" = "mcp-server" ] && [ "$2" = "status" ]; then
    [ -n "${FAKE_MCP_STATUS:-}" ] || exit 64
    printf '%s' "$FAKE_MCP_STATUS"
    exit 0
fi
exit 1
"""

FAKE_PGREP = """#!/bin/sh
[ "${FAKE_XCODE_RUNNING:-0}" = "1" ] && exit 0
exit 1
"""

FAKE_OSASCRIPT = """#!/bin/sh
echo "$@" >> "$OSASCRIPT_LOG"
echo timeout
exit 0
"""


def load_router():
    spec = importlib.util.spec_from_file_location("xcodebuildtools_router", ROUTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_executable(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


class FakeToolsMixin:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.bin_dir = root / "bin"
        self.bin_dir.mkdir()
        write_executable(self.bin_dir / "xcrun", FAKE_XCRUN)
        write_executable(self.bin_dir / "pgrep", FAKE_PGREP)
        write_executable(self.bin_dir / "osascript", FAKE_OSASCRIPT)
        self.data_dir = root / "data"
        self.data_dir.mkdir()
        self.project = root / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        (self.project / "App.xcworkspace").mkdir()
        (self.project / "App.xcodeproj").mkdir()
        (self.project / "Pods" / "Pods.xcodeproj").mkdir(parents=True)

    def env(self, **overrides):
        env = {
            key: value for key, value in os.environ.items()
            if key not in {"XCODEBUILDTOOLS_PREFER_MCP", "CLAUDE_PROJECT_DIR"}
        }
        env.update(
            {
                "PATH": f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}",
                "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
                "CLAUDE_PLUGIN_DATA": str(self.data_dir),
                "TMPDIR": self.temp.name,
            }
        )
        env.update(overrides)
        return env

    def opt_in(self, value="1", filename="settings.json"):
        settings_dir = self.project / ".claude"
        settings_dir.mkdir(exist_ok=True)
        (settings_dir / filename).write_text(
            json.dumps({"env": {"XCODEBUILDTOOLS_PREFER_MCP": value}}),
            encoding="utf-8",
        )

    def run_script(self, script, env):
        result = subprocess.run(
            [sys.executable, str(script), "XcodeBuildTools"],
            input=json.dumps({"session_id": "s1", "cwd": str(self.project)}),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)


class McpFirstRoutingTests(FakeToolsMixin, unittest.TestCase):
    def test_not_opted_in_matches_the_shared_session_start_output(self):
        for xcode_running in ("0", "1"):
            with self.subTest(xcode_running=xcode_running):
                env = self.env(FAKE_XCODE_RUNNING=xcode_running)
                routed = self.run_script(ROUTER_PATH, env)
                # Reset the version tracker so both runs start from the same state.
                for entry in self.data_dir.iterdir():
                    entry.unlink()
                shared = self.run_script(COMMON_SESSION_START, env)
                self.assertEqual(routed, shared)
                context = routed["hookSpecificOutput"]["additionalContext"]
                self.assertNotIn("Xcode MCP first", context)
                self.assertIn("**always** use the applicable XcodeBuildTools skill", context)

    def test_opted_in_headless_routes_to_the_mcp_with_workspace_and_approvals(self):
        self.opt_in()
        payload = self.run_script(
            ROUTER_PATH,
            self.env(FAKE_MCP_STATUS=json.dumps(HEADLESS_STATUS)),
        )

        context = payload["hookSpecificOutput"]["additionalContext"]
        workspace = str(self.project.resolve() / "App.xcworkspace")
        self.assertIn(f"Workspace for this checkout: `{workspace}`", context)
        self.assertNotIn("Pods.xcodeproj", context)
        self.assertIn("`workspaceIdentifier`", context)
        self.assertIn("`XcodeCloseWorkspace`", context)
        self.assertIn("`BuildProject`", context)
        self.assertIn("`device-app`", context)
        self.assertIn("sudo xcrun mcp-server allow-folder", context)
        self.assertIn("never run sudo", context)
        # Unsigned agents can only be approved for 24 hours.
        self.assertIn("sudo xcrun mcp-server approve AGENT-1 --for-24-hours", context)
        # Folder requests for other checkouts are not this session's business.
        self.assertNotIn("FOLDER-OTHER", context)
        self.assertNotIn("<!--", context)
        self.assertNotIn("{{", context)
        self.assertNotIn("**always** use the applicable XcodeBuildTools skill", context)
        self.assertIn("Xcode MCP first (headless)", payload["systemMessage"])
        self.assertIn("AGENT-1", payload["systemMessage"])

    def test_opted_in_through_environment_variable(self):
        payload = self.run_script(
            ROUTER_PATH,
            self.env(
                XCODEBUILDTOOLS_PREFER_MCP="true",
                FAKE_MCP_STATUS=json.dumps(HEADLESS_STATUS),
            ),
        )
        self.assertIn("Xcode MCP first", payload["hookSpecificOutput"]["additionalContext"])

    def test_local_settings_can_turn_the_opt_in_off(self):
        self.opt_in("1")
        self.opt_in("0", filename="settings.local.json")
        payload = self.run_script(
            ROUTER_PATH,
            self.env(FAKE_MCP_STATUS=json.dumps(HEADLESS_STATUS)),
        )
        self.assertNotIn("Xcode MCP first", payload["hookSpecificOutput"]["additionalContext"])

    def test_opted_in_headless_disabled_without_xcode_falls_back_with_enable_command(self):
        self.opt_in()
        status = {"openWorkspaces": [], "permission": {"enabled": False}, "running": False}
        payload = self.run_script(
            ROUTER_PATH,
            self.env(FAKE_MCP_STATUS=json.dumps(status), FAKE_XCODE_RUNNING="0"),
        )

        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## Xcode MCP unavailable", context)
        self.assertIn("`sudo xcrun mcp-server enable`", context)
        self.assertIn("**always** use the applicable XcodeBuildTools skill", context)
        self.assertNotIn("<!--", context)
        self.assertNotIn("XcodeBuildTools remains the primary routing surface", context)
        self.assertIn("unavailable", payload["systemMessage"])

    def test_opted_in_without_mcpbridge_falls_back(self):
        self.opt_in()
        payload = self.run_script(ROUTER_PATH, self.env(FAKE_MCPBRIDGE="0"))
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## Xcode MCP unavailable", context)
        self.assertIn("`xcrun --find mcpbridge`", context)

    def test_opted_in_windowed_mode_on_xcode_without_headless_server(self):
        self.opt_in()
        payload = self.run_script(ROUTER_PATH, self.env(FAKE_XCODE_RUNNING="1"))
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Xcode MCP first", context)
        self.assertIn("Windowed mode", context)
        self.assertNotIn("sudo xcrun mcp-server approve", context)
        self.assertIn("Xcode MCP first (windowed)", payload["systemMessage"])


class McpHelperTests(unittest.TestCase):
    def setUp(self):
        self.router = load_router()

    def test_pending_requests_reads_agent_and_folder_requests(self):
        requests = self.router.pending_requests(HEADLESS_STATUS)
        self.assertEqual(
            [
                {"id": "AGENT-1", "kind": "agent", "label": "claude-code", "path": "", "signed": False},
                {
                    "id": "FOLDER-OTHER",
                    "kind": "folder",
                    "label": "Other",
                    "path": "/nonexistent/other-worktree",
                    "signed": True,
                },
            ],
            requests,
        )
        self.assertEqual(
            "sudo xcrun mcp-server approve FOLDER-OTHER --always",
            self.router.approve_command(requests[1]),
        )

    def test_relevant_requests_keeps_folders_that_cover_the_checkout(self):
        requests = [
            {"id": "A", "kind": "agent", "label": "", "path": "", "signed": True},
            {"id": "P", "kind": "folder", "label": "", "path": "/work", "signed": True},
            {"id": "O", "kind": "folder", "label": "", "path": "/elsewhere", "signed": True},
        ]
        kept = self.router.relevant_requests(requests, "/work/tree-1")
        self.assertEqual(["A", "P"], [request["id"] for request in kept])

    def test_find_workspaces_prefers_root_workspace_then_nested_then_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Pods" / "Pods.xcodeproj").mkdir(parents=True)
            (root / "Package.swift").write_text("", encoding="utf-8")
            self.assertEqual([str(root)], self.router.find_workspaces(str(root)))

            (root / "App" / "App.xcodeproj").mkdir(parents=True)
            self.assertEqual(
                [str(root / "App" / "App.xcodeproj")],
                self.router.find_workspaces(str(root)),
            )

            (root / "App.xcworkspace").mkdir()
            self.assertEqual(
                [str(root / "App.xcworkspace")],
                self.router.find_workspaces(str(root)),
            )

    def test_parse_flag(self):
        self.assertTrue(self.router.parse_flag("1"))
        self.assertTrue(self.router.parse_flag(True))
        self.assertFalse(self.router.parse_flag("off"))
        self.assertIsNone(self.router.parse_flag(None))
        self.assertIsNone(self.router.parse_flag("maybe"))


class ApproveHelperTests(FakeToolsMixin, unittest.TestCase):
    def run_helper(self, **env_overrides):
        log = Path(self.temp.name) / "osascript.log"
        env = self.env(FAKE_XCODE_RUNNING="1", OSASCRIPT_LOG=str(log), **env_overrides)
        started = time.monotonic()
        result = subprocess.run(
            ["bash", str(APPROVE_PATH)],
            text=True,
            capture_output=True,
            env=env,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        return calls, time.monotonic() - started

    def test_headless_mode_never_clicks(self):
        calls, _ = self.run_helper(FAKE_MCP_STATUS=json.dumps(HEADLESS_STATUS))
        self.assertEqual("", calls)

    def test_unreadable_headless_state_never_clicks(self):
        calls, _ = self.run_helper(FAKE_MCP_STATUS="not json")
        self.assertEqual("", calls)

    @unittest.skipUnless(Path("/usr/bin/jq").exists(), "needs /usr/bin/jq")
    def test_windowed_mode_still_looks_for_the_allow_dialog(self):
        status = {"permission": {"enabled": False}, "running": False}
        calls, _ = self.run_helper(FAKE_MCP_STATUS=json.dumps(status))
        self.assertIn("System Events", calls)


if __name__ == "__main__":
    unittest.main()
