import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class OpenCodePluginRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if not cls.node:
            raise unittest.SkipTest("node is not available")

    def run_node(self, script, extra_env=None):
        env = os.environ.copy()
        env["NODE_NO_WARNINGS"] = "1"
        if extra_env:
            env.update(extra_env)

        result = subprocess.run(
            [
                self.node,
                "--experimental-test-module-mocks",
                "--input-type=module",
                "-e",
                textwrap.dedent(script),
            ],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_xcode_mcp_requires_explicit_mcpbridge_configuration(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const calls = [];
            const spawn = (command, args = []) => {
              calls.push([command, ...args]);
              const child = new EventEmitter();
              child.kill = () => true;
              child.unref = () => {};

              let code = 0;
              if (command === "pgrep" && args[0] === "-f") code = 1;
              queueMicrotask(() => child.emit("exit", code));
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=requires-config"
            )).default;
            const hooks = await plugin.server({});
            const config = {};
            await hooks.config(config);

            const output = { system: [] };
            await hooks["experimental.chat.system.transform"](
              { sessionID: "session-1" },
              output,
            );

            console.log(JSON.stringify({
              registeredMcp: Object.keys(config.mcp ?? {}),
              detected: output.system[0].includes("Xcode MCP server detected"),
              approvalLaunched: calls.some(([command]) => command.endsWith("run-background.sh")),
            }));
            """
        )

        self.assertEqual(result["registeredMcp"], ["sosumi"])
        self.assertFalse(result["detected"])
        self.assertFalse(result["approvalLaunched"])

    def test_xcode_mcp_detection_refreshes_after_cache_ttl(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            let now = 1_000;
            let xcodeRunning = false;
            Date.now = () => now;

            const spawn = (command, args = []) => {
              const child = new EventEmitter();
              child.kill = () => true;
              child.unref = () => {};

              let code = 0;
              if (command === "pgrep" && args[0] === "-x") code = xcodeRunning ? 0 : 1;
              if (command === "pgrep" && args[0] === "-f") code = 1;
              queueMicrotask(() => child.emit("exit", code));
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=cache-ttl"
            )).default;
            const hooks = await plugin.server({});
            const config = {
              mcp: {
                xcode: {
                  type: "local",
                  command: ["xcrun", "mcpbridge"],
                },
              },
            };
            await hooks.config(config);

            const first = { system: [] };
            await hooks["experimental.chat.system.transform"](
              { sessionID: "session-1" },
              first,
            );

            now += 31_000;
            xcodeRunning = true;

            const second = { system: [] };
            await hooks["experimental.chat.system.transform"](
              { sessionID: "session-1" },
              second,
            );

            console.log(JSON.stringify({
              firstDetected: first.system[0].includes("Xcode MCP server detected"),
              secondDetected: second.system[0].includes("Xcode MCP server detected"),
            }));
            """
        )

        self.assertFalse(result["firstDetected"])
        self.assertTrue(result["secondDetected"])

    def test_xcode_mcp_approval_runs_once_per_session(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const calls = [];
            const spawn = (command, args = []) => {
              calls.push([command, ...args]);
              const child = new EventEmitter();
              child.kill = () => true;
              child.unref = () => {};

              let code = 0;
              if (command === "pgrep" && args[0] === "-f") code = 1;
              queueMicrotask(() => child.emit("exit", code));
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=approval-per-session"
            )).default;
            const hooks = await plugin.server({});
            const config = {
              mcp: {
                xcode: {
                  type: "local",
                  command: ["xcrun", "mcpbridge"],
                },
              },
            };
            await hooks.config(config);

            for (const sessionID of ["session-1", "session-1", "session-2"]) {
              await hooks["experimental.chat.system.transform"](
                { sessionID },
                { system: [] },
              );
            }

            console.log(JSON.stringify({
              approvalLaunches: calls.filter(([command]) => command.endsWith("run-background.sh")).length,
            }));
            """
        )

        self.assertEqual(result["approvalLaunches"], 2)

    def test_shell_env_sweeps_sandboxes_owned_by_dead_processes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "stale-session");
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                fs.writeFileSync(path.join(stale, "owner.pid"), "999999999\\nopencode\\n");

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=stale-sweep"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  { env: {} },
                );

                console.log(JSON.stringify({ staleExists: fs.existsSync(stale) }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertFalse(result["staleExists"])

    def test_process_start_token_uses_canonical_locale_and_timezone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import { mock } from "node:test";

                const calls = [];
                const spawn = (command, args = [], options = {}) => {
                  calls.push({ command, args, options });
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  queueMicrotask(() => {
                    child.stdout.emit("data", "Mon Jan  1 00:00:00 2024\\n");
                    child.emit("exit", 0);
                    child.emit("close", 0);
                  });
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=canonical-process-start"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  { env: {} },
                );

                const psCall = calls.find(({ command }) => command === "ps");
                console.log(JSON.stringify({
                  locale: psCall?.options?.env?.LC_ALL,
                  language: psCall?.options?.env?.LANG,
                  timezone: psCall?.options?.env?.TZ,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["locale"], "C")
        self.assertEqual(result["language"], "C")
        self.assertEqual(result["timezone"], "UTC")

    def test_process_start_token_waits_for_stdout_to_close(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import fs from "node:fs";
                import path from "node:path";
                import { mock } from "node:test";

                const spawn = () => {
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  queueMicrotask(() => {
                    child.emit("exit", 0);
                    queueMicrotask(() => {
                      child.stdout.emit("data", "canonical-start\\n");
                      child.emit("close", 0);
                    });
                  });
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=wait-for-process-stdout"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const output = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  output,
                );

                const sandbox = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                const owner = fs.readFileSync(path.join(sandbox, "owner.pid"), "utf8");
                console.log(JSON.stringify({
                  token: owner.split(/\\r?\\n/)[2],
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["token"], "canonical-start")

    def test_process_start_token_retries_after_a_transient_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import fs from "node:fs";
                import path from "node:path";
                import { mock } from "node:test";

                let psCalls = 0;
                const spawn = (command) => {
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  queueMicrotask(() => {
                    psCalls += 1;
                    if (psCalls === 1) {
                      child.emit("exit", 1);
                      child.emit("close", 1);
                      return;
                    }
                    child.stdout.emit("data", "canonical-start\\n");
                    child.emit("exit", 0);
                    child.emit("close", 0);
                  });
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=retry-process-start"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const output = { env: {} };
                for (let attempt = 0; attempt < 2; attempt += 1) {
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID: "current-session" },
                    output,
                  );
                }

                const sandbox = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                const owner = fs.readFileSync(path.join(sandbox, "owner.pid"), "utf8");
                console.log(JSON.stringify({
                  psCalls,
                  token: owner.split(/\\r?\\n/)[2],
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["psCalls"], 2)
        self.assertEqual(result["token"], "canonical-start")

    def test_session_deletion_removes_its_owned_sandbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=session-delete"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const output = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "deleted-session" },
                  output,
                );
                const sandbox = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                const eventAvailable = typeof hooks.event === "function";
                if (eventAvailable) {
                  await hooks.event({
                    event: {
                      type: "session.deleted",
                      properties: { info: { id: "deleted-session" } },
                    },
                  });
                }

                console.log(JSON.stringify({
                  eventAvailable,
                  sandboxExists: fs.existsSync(sandbox),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["eventAvailable"])
        self.assertFalse(result["sandboxExists"])

    def test_session_deletion_during_shell_setup_does_not_leave_a_sandbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";
                import { mock } from "node:test";

                let releasePs;
                let markPsStarted;
                const psStarted = new Promise((resolve) => {
                  markPsStarted = resolve;
                });
                const spawn = () => {
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  releasePs = () => {
                    child.stdout.emit("data", "canonical-start\\n");
                    child.emit("exit", 0);
                    child.emit("close", 0);
                  };
                  markPsStarted();
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=delete-during-setup"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const setup = hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "deleted-session" },
                  { env: {} },
                );
                await psStarted;
                await hooks.event({
                  event: {
                    type: "session.deleted",
                    properties: { info: { id: "deleted-session" } },
                  },
                });
                releasePs();
                await setup;

                const sandboxRoot = path.join(
                  os.tmpdir(),
                  "opencode-xcodebuildtools-sandbox",
                );
                const remaining = fs.existsSync(sandboxRoot)
                  ? fs.readdirSync(sandboxRoot)
                  : [];
                console.log(JSON.stringify({ remaining }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["remaining"], [])

    def test_plugin_dispose_removes_all_owned_sandboxes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=dispose"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const sandboxes = [];
                for (const sessionID of ["session-1", "session-2"]) {
                  const output = { env: {} };
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID },
                    output,
                  );
                  sandboxes.push(path.dirname(output.env.SANDBOX_DERIVED_DATA));
                }

                const disposeAvailable = typeof hooks.dispose === "function";
                if (disposeAvailable) await hooks.dispose();

                console.log(JSON.stringify({
                  disposeAvailable,
                  remaining: sandboxes.filter((sandbox) => fs.existsSync(sandbox)),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["disposeAvailable"])
        self.assertEqual(result["remaining"], [])

    def test_disposing_replaced_instance_does_not_remove_new_owner_sandbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=instance-ownership"
                )).default;
                const first = await plugin.server({});
                const second = await plugin.server({});
                await first.config({});
                await second.config({});

                const firstOutput = { env: {} };
                await first["shell.env"](
                  { cwd: process.cwd(), sessionID: "shared-session" },
                  firstOutput,
                );

                const secondOutput = { env: {} };
                await second["shell.env"](
                  { cwd: process.cwd(), sessionID: "shared-session" },
                  secondOutput,
                );
                const firstSandbox = path.dirname(firstOutput.env.SANDBOX_DERIVED_DATA);
                const sandbox = path.dirname(secondOutput.env.SANDBOX_DERIVED_DATA);

                await first.dispose();
                const existsAfterFirstDispose = fs.existsSync(sandbox);
                await second.dispose();

                console.log(JSON.stringify({
                  distinctSandboxes: firstSandbox !== sandbox,
                  existsAfterFirstDispose,
                  existsAfterSecondDispose: fs.existsSync(sandbox),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["distinctSandboxes"])
        self.assertTrue(result["existsAfterFirstDispose"])
        self.assertFalse(result["existsAfterSecondDispose"])

    def test_sweep_removes_sandbox_when_pid_was_reused(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir()
            ps = bin_dir / "ps"
            ps.write_text("#!/bin/sh\nprintf '%s\\n' current-start-time\n", encoding="utf-8")
            ps.chmod(0o755)

            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "reused-pid-session");
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                fs.writeFileSync(
                  path.join(stale, "owner.pid"),
                  `${process.pid}\\nopencode\\nnot-the-current-start-time\\nstale-instance\\n`,
                );

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=reused-pid"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  { env: {} },
                );

                console.log(JSON.stringify({ staleExists: fs.existsSync(stale) }));
                """,
                {
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                    "TMPDIR": tmpdir,
                },
            )

        self.assertFalse(result["staleExists"])


if __name__ == "__main__":
    unittest.main()
