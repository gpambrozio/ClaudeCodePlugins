import importlib.util
import json
import os
import shutil
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

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASELINE_0_5_11 = FIXTURES / "xcodebuildtools-0.5.11"

# Fake xcrun:
#   `--find mcpbridge` follows FAKE_MCPBRIDGE (default found);
#   `--find mcp-server` follows FAKE_MCP_SERVER (default found; 0 = Xcode 26.x,
#   which answers `xcrun mcp-server` with exit 72 like a missing tool);
#   `mcp-server status` prints FAKE_MCP_STATUS, or with FAKE_MCP_STATUS_MODE
#   `fail` exits 1 and `hang` stalls waiting on a child process whose PID it
#   writes to FAKE_HANG_PID_FILE.
FAKE_XCRUN = """#!/bin/sh
if [ "$1" = "--find" ]; then
    case "$2" in
        mcpbridge) [ "${FAKE_MCPBRIDGE:-1}" = "1" ] && { echo /fake/mcpbridge; exit 0; } ;;
        mcp-server) [ "${FAKE_MCP_SERVER:-1}" = "1" ] && { echo /fake/mcp-server; exit 0; } ;;
    esac
    exit 72
fi
if [ "$1" = "mcp-server" ]; then
    [ "${FAKE_MCP_SERVER:-1}" = "1" ] || exit 72
    if [ "$2" = "status" ]; then
        case "${FAKE_MCP_STATUS_MODE:-}" in
            fail) echo "permission service unavailable" >&2; exit 1 ;;
            hang)
                sleep 20 &
                echo $! > "${FAKE_HANG_PID_FILE:-/dev/null}"
                wait
                ;;
        esac
        printf '%s' "${FAKE_MCP_STATUS:-}"
        exit 0
    fi
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


# Valid JSON whose headless state is still unknown: no boolean permission.enabled.
INVALID_SCHEMA_STATUSES = (
    {},
    {"permission": {}},
    {"permission": "enabled"},
    {"permission": {"enabled": None}},
    {"permission": {"enabled": "false"}},
    [{"permission": {"enabled": False}}],
)


def process_exists(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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

    def hang_pid_file(self):
        return Path(self.temp.name) / "hang.pid"

    def assert_hang_child_exited(self):
        pid = int(self.hang_pid_file().read_text(encoding="utf-8").strip())
        for _ in range(50):
            if not process_exists(pid):
                return
            time.sleep(0.1)
        os.kill(pid, 9)
        self.fail(f"the stalled probe's child process {pid} outlived the timeout")

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
        self.assertIn("`workspace-…` id it returns", context)
        self.assertIn("Unknown workspace identifier", context)
        self.assertIn(".xcscheme", context)
        # Scheme edits that predate the session or belong to the task survive the cleanup.
        self.assertIn("git status --porcelain -- '*.xcscheme'", context)
        self.assertIn("was clean before you opened the workspace", context)
        self.assertIn("never `git restore` it", context)
        self.assertIn("one identifier per test", context)
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

    def test_opted_in_windowed_mode_on_xcode_27_with_headless_off(self):
        self.opt_in()
        status = {"openWorkspaces": [], "permission": {"enabled": False}, "running": False}
        payload = self.run_script(
            ROUTER_PATH,
            self.env(FAKE_MCP_STATUS=json.dumps(status), FAKE_XCODE_RUNNING="1"),
        )
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Xcode MCP first", context)
        self.assertIn("Windowed mode", context)
        self.assertIn("`XcodeOpenWorkspace`", context)
        self.assertNotIn("sudo xcrun mcp-server approve", context)
        self.assertIn("Xcode MCP first (windowed)", payload["systemMessage"])

    def test_opted_in_on_xcode_26_windowed_bridge_falls_back_to_skills(self):
        # Xcode 26.3's bridge has XcodeListWindows/tabIdentifier, not the Xcode 27
        # workspace tools the MCP-first context is written for.
        self.opt_in()
        payload = self.run_script(
            ROUTER_PATH,
            self.env(FAKE_MCP_SERVER="0", FAKE_XCODE_RUNNING="1"),
        )
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## Xcode MCP unavailable", context)
        self.assertIn("older than Xcode 27", context)
        self.assertIn("`tabIdentifier`", context)
        self.assertNotIn("Xcode MCP first", context)
        self.assertNotIn("workspaceIdentifier", context)
        self.assertNotIn("XcodeCloseWorkspace", context)
        # Xcode is running, so the default routing's secondary-MCP section stays, as in 0.5.x.
        self.assertIn("XcodeBuildTools remains the primary routing surface", context)
        self.assertIn("**always** use the applicable XcodeBuildTools skill", context)
        self.assertNotIn("Xcode MCP first (", payload["systemMessage"])
        self.assertIn("unavailable", payload["systemMessage"])

    def test_opted_in_with_failing_status_probe_falls_back(self):
        self.opt_in()
        payload = self.run_script(
            ROUTER_PATH,
            self.env(FAKE_MCP_STATUS_MODE="fail", FAKE_XCODE_RUNNING="1"),
        )
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## Xcode MCP unavailable", context)
        self.assertIn("failed, timed out or printed no boolean", context)
        self.assertNotIn("Windowed mode", context)

    def test_opted_in_with_status_lacking_a_boolean_permission_falls_back(self):
        self.opt_in()
        for status in INVALID_SCHEMA_STATUSES:
            with self.subTest(status=status):
                payload = self.run_script(
                    ROUTER_PATH,
                    self.env(FAKE_MCP_STATUS=json.dumps(status), FAKE_XCODE_RUNNING="1"),
                )
                context = payload["hookSpecificOutput"]["additionalContext"]
                self.assertIn("## Xcode MCP unavailable", context)
                self.assertIn("printed no boolean", context)
                self.assertNotIn("Xcode MCP first (", payload["systemMessage"])

    def test_opted_in_with_stalled_status_probe_falls_back_within_the_timeout(self):
        self.opt_in()
        started = time.monotonic()
        payload = self.run_script(
            ROUTER_PATH,
            self.env(
                FAKE_MCP_STATUS_MODE="hang",
                FAKE_HANG_PID_FILE=str(self.hang_pid_file()),
                FAKE_XCODE_RUNNING="1",
                XCODEBUILDTOOLS_MCP_STATUS_TIMEOUT="1",
            ),
        )
        self.assertLess(time.monotonic() - started, 10)
        self.assert_hang_child_exited()
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## Xcode MCP unavailable", context)
        self.assertIn("failed, timed out or printed no boolean", context)


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

    def test_relevant_requests_leaves_out_a_nested_worktree(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            repo = base / "repo"
            (repo / ".git").mkdir(parents=True)
            (repo / "Sources").mkdir()
            nested = repo / ".worktrees" / "feature"
            (nested / "App").mkdir(parents=True)
            (nested / ".git").write_text("gitdir: ../../.git/worktrees/feature\n", encoding="utf-8")
            link = base / "link"
            link.symlink_to(repo)

            def folder(request_id, path):
                return {"id": request_id, "kind": "folder", "label": "", "path": str(path), "signed": True}

            requests = [
                folder("PARENT", base),
                folder("REPO", repo),
                folder("SOURCES", repo / "Sources"),
                folder("NESTED", nested),
                folder("NESTED-APP", nested / "App"),
                folder("NESTED-VIA-LINK", link / ".worktrees" / "feature"),
            ]

            def kept(root):
                return [request["id"] for request in self.router.relevant_requests(requests, str(root))]

            self.assertEqual(["PARENT", "REPO", "SOURCES"], kept(repo))
            # The same checkout reached through a symlink.
            self.assertEqual(["PARENT", "REPO", "SOURCES"], kept(link))
            # From the nested worktree, folders that contain it cover it; the main checkout's don't.
            self.assertEqual(
                ["PARENT", "REPO", "NESTED", "NESTED-APP", "NESTED-VIA-LINK"],
                kept(nested),
            )

    def test_find_workspaces_prefers_the_root_over_subdirectories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Pods" / "Pods.xcodeproj").mkdir(parents=True)
            (root / "Package.swift").write_text("", encoding="utf-8")
            self.assertEqual([str(root)], self.router.find_workspaces(str(root)))

            # Without a root project, a root package and nested projects are all candidates.
            (root / "App" / "App.xcodeproj").mkdir(parents=True)
            self.assertEqual(
                [str(root), str(root / "App" / "App.xcodeproj")],
                self.router.find_workspaces(str(root)),
            )

            # A nested example workspace never hides the root project.
            (root / "Examples" / "Demo.xcworkspace").mkdir(parents=True)
            (root / "Library.xcodeproj").mkdir()
            self.assertEqual(
                [str(root / "Library.xcodeproj")],
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
        if log.exists():
            log.unlink()
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

    def test_failing_status_probe_never_clicks(self):
        calls, _ = self.run_helper(FAKE_MCP_STATUS_MODE="fail")
        self.assertEqual("", calls)

    def test_stalled_status_probe_never_clicks_and_gives_up(self):
        calls, elapsed = self.run_helper(
            FAKE_MCP_STATUS_MODE="hang",
            FAKE_HANG_PID_FILE=str(self.hang_pid_file()),
            XCODEBUILDTOOLS_MCP_STATUS_TIMEOUT="1",
        )
        self.assertEqual("", calls)
        self.assertLess(elapsed, 10)
        self.assert_hang_child_exited()

    def test_status_lacking_a_boolean_permission_never_clicks(self):
        for status in INVALID_SCHEMA_STATUSES:
            with self.subTest(status=status):
                calls, _ = self.run_helper(FAKE_MCP_STATUS=json.dumps(status))
                self.assertEqual("", calls)

    @unittest.skipUnless(Path("/usr/bin/jq").exists(), "needs /usr/bin/jq")
    def test_windowed_mode_still_looks_for_the_allow_dialog(self):
        status = {"permission": {"enabled": False}, "running": False}
        calls, _ = self.run_helper(FAKE_MCP_STATUS=json.dumps(status))
        self.assertIn("System Events", calls)

    def test_xcode_26_without_the_mcp_server_tool_looks_for_the_allow_dialog(self):
        calls, _ = self.run_helper(FAKE_MCP_SERVER="0")
        self.assertIn("System Events", calls)



# The only intended differences between the default (not opted in) context and
# 0.5.11's: the Build Isolation paragraphs describe the per-worktree sandbox.
KNOWN_DIFFERENCES_FROM_0_5_11 = [
    (
        "Each session gets an isolated build sandbox keyed by its agent session ID.",
        "Builds run in an isolated build sandbox. In Claude Code there is one per worktree "
        "(or project folder), shared by every session in it, so new sessions build warm while "
        "separate worktrees stay separate.",
    ),
    (
        "isolated from Xcode and from other agent sessions.",
        "isolated from Xcode and from other worktrees.",
    ),
]


def expected_default_context(name):
    baseline = (BASELINE_0_5_11 / f"session-start-{name}.md").read_text(encoding="utf-8")
    for old, new in KNOWN_DIFFERENCES_FROM_0_5_11:
        if baseline.count(old) != 1:
            raise AssertionError(f"0.5.11 baseline {name} lacks: {old}")
        baseline = baseline.replace(old, new)
    return baseline


class DefaultContextBaselineTests(FakeToolsMixin, unittest.TestCase):
    """The not-opted-in context of every caller against frozen 0.5.11 output.

    The fixtures are 0.5.11's rendered additionalContext (common/session-start.py
    at tag XcodeBuildTools--v0.5.11, with and without Xcode running).
    """

    CASES = (("0", "no-xcode-mcp"), ("1", "xcode-mcp"))

    def claude_code_context(self, script, xcode_running):
        for entry in self.data_dir.iterdir():
            entry.unlink()
        payload = self.run_script(script, self.env(FAKE_XCODE_RUNNING=xcode_running))
        return payload["hookSpecificOutput"]["additionalContext"]

    def test_session_start_router_matches_0_5_11_with_known_differences(self):
        for xcode_running, name in self.CASES:
            with self.subTest(name=name):
                self.assertEqual(
                    expected_default_context(name),
                    self.claude_code_context(ROUTER_PATH, xcode_running),
                )

    def test_shared_session_start_matches_0_5_11_with_known_differences(self):
        for xcode_running, name in self.CASES:
            with self.subTest(name=name):
                self.assertEqual(
                    expected_default_context(name),
                    self.claude_code_context(COMMON_SESSION_START, xcode_running),
                )

    def test_opencode_context_matches_0_5_11_with_known_differences(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available")
        script = """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const xcodeRunning = process.env.FAKE_XCODE_RUNNING === "1";
            const spawn = (command, args = []) => {
              const child = new EventEmitter();
              child.kill = () => true;
              child.unref = () => {};
              let code = 0;
              if (command === "/usr/bin/pgrep") code = xcodeRunning && args[0] === "-x" ? 0 : 1;
              queueMicrotask(() => child.emit("exit", code));
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              `./XcodeBuildTools/opencode-plugin.js?test=baseline-${process.env.FAKE_XCODE_RUNNING}`
            )).default;
            const hooks = await plugin.server({});
            const config = { mcp: { xcode: { type: "local", command: ["xcrun", "mcpbridge"] } } };
            await hooks.config(config);
            const output = { system: [] };
            await hooks["experimental.chat.system.transform"]({ sessionID: "session-1" }, output);
            console.log(JSON.stringify(output.system[0]));
        """
        for xcode_running, name in self.CASES:
            with self.subTest(name=name):
                result = subprocess.run(
                    [node, "--experimental-test-module-mocks", "--input-type=module", "-e", script],
                    cwd=REPO_ROOT,
                    env={**os.environ, "NODE_NO_WARNINGS": "1", "FAKE_XCODE_RUNNING": xcode_running},
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                system = json.loads(result.stdout)
                expected = expected_default_context(name)
                self.assertTrue(
                    system.endswith("\n\n" + expected),
                    f"OpenCode context differs from the 0.5.11 baseline:\n{system}",
                )


if __name__ == "__main__":
    unittest.main()
