import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_DIR = REPO_ROOT / "common"
SESSION_START_PATH = COMMON_DIR / "session-start.py"
PRE_TOOL_USE_PATH = COMMON_DIR / "pre-tool-use.py"
RUN_BACKGROUND_PATH = REPO_ROOT / "XcodeBuildTools" / "hooks" / "run-background.sh"
DEFAULT_PLUGIN_ROOT = REPO_ROOT / "XcodeBuildTools"
PLUGIN_ROOT_ENV = "XCODEBUILDTOOLS_TEST_PLUGIN_ROOT"


def load_session_start_module():
    if str(COMMON_DIR) not in sys.path:
        sys.path.insert(0, str(COMMON_DIR))

    spec = importlib.util.spec_from_file_location(
        "session_start_under_test",
        SESSION_START_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SessionStartTests(unittest.TestCase):
    def render_session_start(self, xcode_mcp_likely=False, plugin_root=None):
        module = load_session_start_module()
        fake_detector = types.ModuleType("detect_xcode_mcp")
        fake_detector.detect_xcode_mcp = lambda: {
            "xcode_mcp_likely": xcode_mcp_likely,
        }

        plugin_root = (
            plugin_root
            or os.environ.get(PLUGIN_ROOT_ENV)
            or str(DEFAULT_PLUGIN_ROOT)
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as data_dir:
            with patch.dict(
                os.environ,
                {
                    "CLAUDE_PLUGIN_ROOT": plugin_root,
                    "CLAUDE_PLUGIN_DATA": data_dir,
                },
                clear=False,
            ):
                with patch.dict(sys.modules, {"detect_xcode_mcp": fake_detector}):
                    with contextlib.redirect_stdout(stdout):
                        with contextlib.redirect_stderr(stderr):
                            with self.assertRaises(SystemExit) as exit_context:
                                module.main()

        self.assertEqual(exit_context.exception.code, 0, stderr.getvalue())
        return json.loads(stdout.getvalue())

    def test_mcp_available_context_keeps_xcodebuildtools_as_primary_route(self):
        payload = self.render_session_start(xcode_mcp_likely=True)

        self.assertIn("Xcode MCP server detected.", payload["systemMessage"])
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn(
            "XcodeBuildTools remains the primary routing surface",
            context,
        )
        self.assertIn(
            "Do not bypass an applicable XcodeBuildTools skill",
            context,
        )
        self.assertIn("Use raw Xcode MCP tools only when:", context)
        self.assertNotIn("Before using an XcodeBuildTools skill", context)
        self.assertNotIn("Prefer Xcode MCP tools when available", context)
        self.assertNotIn("How to delegate", context)
        self.assertNotIn(
            "The `sosumi` MCP server provides quick access",
            context,
        )

    def test_mcp_unavailable_context_omits_mcp_routing_block(self):
        payload = self.render_session_start(xcode_mcp_likely=False)

        self.assertNotIn("Xcode MCP server detected.", payload["systemMessage"])
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn(
            "The `sosumi` MCP server provides quick access",
            context,
        )
        self.assertNotIn(
            "XcodeBuildTools remains the primary routing surface",
            context,
        )

    def test_marvin_output_style_emits_personality_context_and_welcome(self):
        payload = self.render_session_start(
            plugin_root=str(REPO_ROOT / "MarvinOutputStyle"),
        )

        self.assertIn(
            "The MarvinOutputStyle plugin is loaded and ready.",
            payload["systemMessage"],
        )
        self.assertIn("Prepare for pessimism", payload["systemMessage"])
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Marvin the Paranoid Android Personality", context)
        self.assertIn("Core Characteristics", context)

    def test_swift_scaffolding_emits_welcome_without_extra_context(self):
        payload = self.render_session_start(
            plugin_root=str(REPO_ROOT / "SwiftScaffolding"),
        )

        self.assertIn(
            "The SwiftScaffolding plugin is loaded and ready.",
            payload["systemMessage"],
        )
        self.assertIn(
            "You can scaffold Swift projects",
            payload["systemMessage"],
        )
        self.assertEqual(
            payload["hookSpecificOutput"]["additionalContext"],
            "",
        )

    def test_ios_simulator_loads_without_extra_context(self):
        payload = self.render_session_start(
            plugin_root=str(REPO_ROOT / "iOSSimulator"),
        )

        self.assertEqual(
            payload["systemMessage"],
            "The iOSSimulator plugin is loaded and ready.",
        )
        self.assertEqual(
            payload["hookSpecificOutput"]["additionalContext"],
            "",
        )

    def test_plugin_base_emits_template_context(self):
        payload = self.render_session_start(
            plugin_root=str(REPO_ROOT / "PluginBase"),
        )

        self.assertEqual(
            payload["systemMessage"],
            "The PluginBase plugin is loaded and ready.",
        )
        self.assertIn(
            "Customize if needed.",
            payload["hookSpecificOutput"]["additionalContext"],
        )


class BackgroundHookTests(unittest.TestCase):
    def test_run_background_preserves_original_hook_owner_pid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            plugin_root = tmp_path / "Plugin"
            hooks_dir = plugin_root / "hooks"
            hooks_dir.mkdir(parents=True)

            target = hooks_dir / "capture-owner.sh"
            owner_pid_file = tmp_path / "owner-pid.txt"
            payload_file = tmp_path / "payload.json"
            target.write_text(
                "\n".join(
                    [
                        "#!/bin/bash",
                        "set -euo pipefail",
                        'printf "%s" "${CLAUDE_HOOK_OWNER_PID:-}" > "$OWNER_PID_FILE"',
                        'cat > "$PAYLOAD_FILE"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            target.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "CLAUDE_PLUGIN_ROOT": str(plugin_root),
                    "OWNER_PID_FILE": str(owner_pid_file),
                    "PAYLOAD_FILE": str(payload_file),
                    "TMPDIR": tmpdir,
                }
            )

            result = subprocess.run(
                [str(RUN_BACKGROUND_PATH), "hooks/capture-owner.sh"],
                input='{"session_id":"session-1"}',
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            for _ in range(50):
                if owner_pid_file.exists() and payload_file.exists():
                    break
                time.sleep(0.02)

            self.assertEqual(owner_pid_file.read_text(encoding="utf-8"), str(os.getpid()))
            self.assertEqual(payload_file.read_text(encoding="utf-8"), '{"session_id":"session-1"}')


class PreToolUseTests(unittest.TestCase):
    def run_hook(self, plugin_name, payload, tmpdir):
        env = {
            "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT / plugin_name),
            "TMPDIR": str(tmpdir),
        }
        result = subprocess.run(
            [sys.executable, str(PRE_TOOL_USE_PATH)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_xcodebuild_rule_denies_once_then_allows_same_session(self):
        payload = {
            "session_id": "session-1",
            "tool_name": "Bash",
            "tool_input": {"command": "xcodebuild -scheme App build"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            first = self.run_hook("XcodeBuildTools", payload, tmpdir)
            second = self.run_hook("XcodeBuildTools", payload, tmpdir)

        decision = json.loads(first)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("xcodebuild", decision["permissionDecisionReason"])
        self.assertIn("skill", decision["permissionDecisionReason"])
        self.assertEqual(second, "")

    def test_xcodebuild_rule_allows_xcsift_wrapped_command(self):
        payload = {
            "session_id": "session-1",
            "tool_name": "Bash",
            "tool_input": {"command": "xcodebuild -scheme App build | xcsift"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output = self.run_hook("XcodeBuildTools", payload, tmpdir)

        decision = json.loads(output)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "allow")

    def test_ios_simulator_rule_allows_device_listing_but_denies_other_simctl(self):
        list_payload = {
            "session_id": "session-1",
            "tool_name": "Bash",
            "tool_input": {"command": "xcrun simctl list devices available"},
        }
        boot_payload = {
            "session_id": "session-1",
            "tool_name": "Bash",
            "tool_input": {"command": "xcrun simctl boot ABCD-1234"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            list_output = self.run_hook("iOSSimulator", list_payload, tmpdir)
            boot_output = self.run_hook("iOSSimulator", boot_payload, tmpdir)

        self.assertEqual(list_output, "")
        decision = json.loads(boot_output)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("ios-simulator skill", decision["permissionDecisionReason"])

    def test_plugin_skill_invocations_are_allowed(self):
        payload = {
            "session_id": "session-1",
            "tool_name": "Skill",
            "tool_input": {"skill": "XcodeBuildTools:xcodebuild"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output = self.run_hook("XcodeBuildTools", payload, tmpdir)

        decision = json.loads(output)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "allow")


if __name__ == "__main__":
    unittest.main()
