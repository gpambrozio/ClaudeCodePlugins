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

    def run_node(self, script, extra_env=None, timeout=None):
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
            timeout=timeout,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_mcp_placeholders_expand_before_registration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "plugin"
            worktree = Path(tmpdir) / "worktree"
            directory = Path(tmpdir) / "directory"
            plugin_root.mkdir()
            worktree.mkdir()
            directory.mkdir()
            (plugin_root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "local": {
                                "command": "${CLAUDE_PLUGIN_ROOT}/bin/server",
                                "args": [
                                    "--project=${CLAUDE_PROJECT_DIR}",
                                    "--token=${OPENCODE_TEST_TOKEN}",
                                    "--mode=${OPENCODE_TEST_DEFAULT:-source-default}",
                                ],
                                "environment": {
                                    "PLUGIN_PATH": "${CLAUDE_PLUGIN_ROOT}/resources",
                                    "PROJECT_PATH": "${CLAUDE_PROJECT_DIR}",
                                    "TOKEN": "${OPENCODE_TEST_TOKEN}",
                                    "MODE": "${OPENCODE_TEST_DEFAULT:-source-default}",
                                },
                                "cwd": "${CLAUDE_PROJECT_DIR}/workspace",
                            },
                            "remote": {
                                "url": (
                                    "https://${OPENCODE_TEST_HOST:-mcp.example.test}/"
                                    "${OPENCODE_TEST_TOKEN}?project=${CLAUDE_PROJECT_DIR}"
                                ),
                                "headers": {
                                    "Authorization": "Bearer ${OPENCODE_TEST_TOKEN}",
                                    "X-Plugin-Root": "${CLAUDE_PLUGIN_ROOT}",
                                    "X-Mode": "${OPENCODE_TEST_DEFAULT:-source-default}",
                                },
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_node(
                """
                import { createOpenCodePlugin } from "./common/opencode-plugin.js?test=mcp-placeholders";

                delete process.env.OPENCODE_TEST_DEFAULT;
                delete process.env.OPENCODE_TEST_HOST;

                const server = createOpenCodePlugin(process.env.TEST_PLUGIN_ROOT);
                const worktreeHooks = await server({
                  worktree: process.env.TEST_WORKTREE,
                  directory: process.env.TEST_DIRECTORY,
                });
                const worktreeConfig = {};
                await worktreeHooks.config(worktreeConfig);

                const directoryHooks = await server({
                  directory: process.env.TEST_DIRECTORY,
                });
                const directoryConfig = {};
                await directoryHooks.config(directoryConfig);

                console.log(JSON.stringify({
                  worktree: worktreeConfig.mcp,
                  directoryCommand: directoryConfig.mcp.local.command,
                }));
                """,
                {
                    "TEST_PLUGIN_ROOT": str(plugin_root / ".." / "plugin"),
                    "TEST_WORKTREE": str(worktree),
                    "TEST_DIRECTORY": str(directory),
                    "OPENCODE_TEST_TOKEN": "runtime-token",
                },
            )

        self.assertEqual(
            result["worktree"],
            {
                "local": {
                    "type": "local",
                    "command": [
                        str(plugin_root / "bin" / "server"),
                        f"--project={worktree}",
                        "--token=runtime-token",
                        "--mode=source-default",
                    ],
                    "cwd": str(worktree / "workspace"),
                    "environment": {
                        "PLUGIN_PATH": str(plugin_root / "resources"),
                        "PROJECT_PATH": str(worktree),
                        "TOKEN": "runtime-token",
                        "MODE": "source-default",
                    },
                },
                "remote": {
                    "type": "remote",
                    "url": (
                        f"https://mcp.example.test/runtime-token?project={worktree}"
                    ),
                    "headers": {
                        "Authorization": "Bearer runtime-token",
                        "X-Plugin-Root": str(plugin_root),
                        "X-Mode": "source-default",
                    },
                },
            },
        )
        self.assertEqual(
            result["directoryCommand"],
            [
                str(plugin_root / "bin" / "server"),
                f"--project={directory}",
                "--token=runtime-token",
                "--mode=source-default",
            ],
        )

    def test_mcp_required_placeholder_reports_unset_variable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "plugin"
            plugin_root.mkdir()
            (plugin_root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "local": {
                                "command": "${OPENCODE_TEST_MISSING}/server",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_node(
                """
                import { createOpenCodePlugin } from "./common/opencode-plugin.js?test=mcp-required-placeholder";

                delete process.env.OPENCODE_TEST_MISSING;
                const server = createOpenCodePlugin(process.env.TEST_PLUGIN_ROOT);
                const hooks = await server({ directory: process.cwd() });

                let message = "";
                try {
                  await hooks.config({});
                } catch (error) {
                  message = error.message;
                }

                console.log(JSON.stringify({ message }));
                """,
                {"TEST_PLUGIN_ROOT": str(plugin_root)},
            )

        self.assertIn("OPENCODE_TEST_MISSING", result["message"])
        self.assertIn("unset", result["message"].lower())

    def test_remote_mcp_oauth_preserves_compatible_configuration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "plugin"
            plugin_root.mkdir()
            (plugin_root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "disabled": {
                                "url": "https://disabled.example.test/mcp",
                                "oauth": False,
                            },
                            "configured": {
                                "url": "https://configured.example.test/mcp",
                                "oauth": {
                                    "clientId": "client-id",
                                    "clientSecret": "client-secret",
                                    "callbackPort": 9876,
                                    "redirectUri": "http://127.0.0.1:9876/callback",
                                    "scope": "ignored-singular-scope",
                                    "scopes": "read write",
                                    "authorizationUrl": "https://source-only.example.test",
                                },
                            },
                            "singular": {
                                "url": "https://singular.example.test/mcp",
                                "oauth": {"scope": "already singular"},
                            },
                            "invalidMembers": {
                                "url": "https://invalid-members.example.test/mcp",
                                "oauth": {
                                    "clientId": 123,
                                    "clientSecret": False,
                                    "callbackPort": 4321,
                                    "redirectUri": ["http://invalid.example.test"],
                                    "scope": {"invalid": True},
                                    "scopes": 456,
                                },
                            },
                            "fractionalPort": {
                                "url": "https://fractional-port.example.test/mcp",
                                "oauth": {
                                    "clientId": "kept-fractional",
                                    "callbackPort": 9876.5,
                                },
                            },
                            "stringPort": {
                                "url": "https://string-port.example.test/mcp",
                                "oauth": {
                                    "scope": "kept-string",
                                    "callbackPort": "9876",
                                },
                            },
                            "lowPort": {
                                "url": "https://low-port.example.test/mcp",
                                "oauth": {
                                    "clientSecret": "kept-low",
                                    "callbackPort": 0,
                                },
                            },
                            "highPort": {
                                "url": "https://high-port.example.test/mcp",
                                "oauth": {
                                    "redirectUri": "http://kept-high.example.test",
                                    "callbackPort": 65536,
                                },
                            },
                            "minimumPort": {
                                "url": "https://minimum-port.example.test/mcp",
                                "oauth": {"callbackPort": 1},
                            },
                            "maximumPort": {
                                "url": "https://maximum-port.example.test/mcp",
                                "oauth": {"callbackPort": 65535},
                            },
                            "empty": {
                                "url": "https://empty.example.test/mcp",
                                "oauth": {},
                            },
                            "invalid": {
                                "url": "https://invalid.example.test/mcp",
                                "oauth": True,
                            },
                            "absent": {
                                "url": "https://absent.example.test/mcp",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_node(
                """
                import { createOpenCodePlugin } from "./common/opencode-plugin.js?test=mcp-oauth";

                const server = createOpenCodePlugin(process.env.TEST_PLUGIN_ROOT);
                const hooks = await server({ directory: process.cwd() });
                const config = {};
                await hooks.config(config);

                console.log(JSON.stringify(config.mcp));
                """,
                {"TEST_PLUGIN_ROOT": str(plugin_root)},
            )

        self.assertEqual(
            result,
            {
                "disabled": {
                    "type": "remote",
                    "url": "https://disabled.example.test/mcp",
                    "oauth": False,
                },
                "configured": {
                    "type": "remote",
                    "url": "https://configured.example.test/mcp",
                    "oauth": {
                        "clientId": "client-id",
                        "clientSecret": "client-secret",
                        "callbackPort": 9876,
                        "redirectUri": "http://127.0.0.1:9876/callback",
                        "scope": "read write",
                    },
                },
                "singular": {
                    "type": "remote",
                    "url": "https://singular.example.test/mcp",
                    "oauth": {"scope": "already singular"},
                },
                "invalidMembers": {
                    "type": "remote",
                    "url": "https://invalid-members.example.test/mcp",
                    "oauth": {"callbackPort": 4321},
                },
                "fractionalPort": {
                    "type": "remote",
                    "url": "https://fractional-port.example.test/mcp",
                    "oauth": {"clientId": "kept-fractional"},
                },
                "stringPort": {
                    "type": "remote",
                    "url": "https://string-port.example.test/mcp",
                    "oauth": {"scope": "kept-string"},
                },
                "lowPort": {
                    "type": "remote",
                    "url": "https://low-port.example.test/mcp",
                    "oauth": {"clientSecret": "kept-low"},
                },
                "highPort": {
                    "type": "remote",
                    "url": "https://high-port.example.test/mcp",
                    "oauth": {"redirectUri": "http://kept-high.example.test"},
                },
                "minimumPort": {
                    "type": "remote",
                    "url": "https://minimum-port.example.test/mcp",
                    "oauth": {"callbackPort": 1},
                },
                "maximumPort": {
                    "type": "remote",
                    "url": "https://maximum-port.example.test/mcp",
                    "oauth": {"callbackPort": 65535},
                },
                "empty": {
                    "type": "remote",
                    "url": "https://empty.example.test/mcp",
                    "oauth": {},
                },
                "invalid": {
                    "type": "remote",
                    "url": "https://invalid.example.test/mcp",
                },
                "absent": {
                    "type": "remote",
                    "url": "https://absent.example.test/mcp",
                },
            },
        )

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
                fs.writeFileSync(
                  path.join(stale, "owner.pid"),
                  "999999999\\nopencode\\n\\n00000000-0000-4000-8000-000000000001\\n",
                );

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

    def test_shell_env_sweeps_old_sandboxes_without_valid_owners(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "ownerless-stale-session");
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(stale, old, old);

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=ownerless-stale-sweep"
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

    def test_shell_env_keeps_fresh_sandboxes_without_valid_owners(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const fresh = path.join(sandboxRoot, "ownerless-fresh-session");
                fs.mkdirSync(path.join(fresh, "build"), { recursive: true });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=ownerless-fresh-sweep"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  { env: {} },
                );

                console.log(JSON.stringify({ freshExists: fs.existsSync(fresh) }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["freshExists"])

    def test_shell_env_sweeps_old_truncated_owner_with_live_pid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "truncated-owner-session");
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                fs.writeFileSync(path.join(stale, "owner.pid"), `${process.pid}\\nopencode\\n`);
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(stale, old, old);

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=truncated-owner-sweep"
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

    def test_shell_env_sweeps_old_partial_instance_id_with_live_pid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "partial-instance-session");
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                fs.writeFileSync(
                  path.join(stale, "owner.pid"),
                  `${process.pid}\\nopencode\\n\\na\\n`,
                );
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(stale, old, old);

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=partial-instance-sweep"
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

    def test_shell_env_recovers_an_abandoned_owner_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "abandoned-lock-session");
                const lock = path.join(stale, ".owner.lock");
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                fs.writeFileSync(lock, "00000000-0000-4000-8000-000000000001\\n");
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(lock, old, old);
                fs.utimesSync(stale, old, old);

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=abandoned-owner-lock"
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

    def test_stale_lock_recovery_does_not_steal_a_replacement_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "replacement-lock-session");
                const lock = path.join(stale, ".owner.lock");
                const oldToken = "00000000-0000-4000-8000-000000000001";
                const replacementToken = "00000000-0000-4000-8000-000000000002";
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                fs.writeFileSync(lock, `${oldToken}\\n`);
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(lock, old, old);
                fs.utimesSync(stale, old, old);

                const originalStatSync = fs.statSync;
                let replacementInstalled = false;
                fs.statSync = (filePath, ...args) => {
                  const stat = originalStatSync(filePath, ...args);
                  if (String(filePath) === lock && !replacementInstalled) {
                    replacementInstalled = true;
                    fs.unlinkSync(lock);
                    fs.writeFileSync(lock, `${replacementToken}\\n`);
                  }
                  return stat;
                };

                try {
                  const plugin = (await import(
                    "./XcodeBuildTools/opencode-plugin.js?test=replacement-owner-lock"
                  )).default;
                  const hooks = await plugin.server({});
                  await hooks.config({});
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID: "current-session" },
                    { env: {} },
                  );
                } finally {
                  fs.statSync = originalStatSync;
                }

                console.log(JSON.stringify({
                  replacementInstalled,
                  staleExists: fs.existsSync(stale),
                  lockToken: fs.existsSync(lock) ? fs.readFileSync(lock, "utf8").trim() : "",
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["replacementInstalled"])
        self.assertTrue(result["staleExists"])
        self.assertEqual(
            result["lockToken"], "00000000-0000-4000-8000-000000000002"
        )

    def test_stale_sweep_revalidates_owner_published_after_stat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=owner-publication-race"
                )).default;
                const writer = await plugin.server({});
                await writer.config({});

                const writerInput = { cwd: process.cwd(), sessionID: "writer-session" };
                const writerOutput = { env: {} };
                await writer["shell.env"](writerInput, writerOutput);

                const sandbox = path.dirname(writerOutput.env.SANDBOX_DERIVED_DATA);
                fs.unlinkSync(path.join(sandbox, "owner.pid"));
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(sandbox, old, old);

                const originalStat = fs.promises.stat;
                let ownerPublished = false;
                fs.promises.stat = async (filePath) => {
                  const stat = await originalStat(filePath);
                  if (String(filePath) === sandbox && !ownerPublished) {
                    ownerPublished = true;
                    await writer["shell.env"](writerInput, { env: {} });
                  }
                  return stat;
                };

                try {
                  const sweeper = await plugin.server({});
                  await sweeper.config({});
                  await sweeper["shell.env"](
                    { cwd: process.cwd(), sessionID: "sweeper-session" },
                    { env: {} },
                  );
                } finally {
                  fs.promises.stat = originalStat;
                }

                console.log(JSON.stringify({
                  ownerPublished,
                  sandboxExists: fs.existsSync(sandbox),
                  ownerExists: fs.existsSync(path.join(sandbox, "owner.pid")),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["ownerPublished"])
        self.assertTrue(result["sandboxExists"])
        self.assertTrue(result["ownerExists"])

    def test_stale_sweep_quarantines_before_recursive_removal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=quarantine-before-remove"
                )).default;
                const writer = await plugin.server({});
                await writer.config({});

                const writerInput = { cwd: process.cwd(), sessionID: "writer-session" };
                const initialOutput = { env: {} };
                await writer["shell.env"](writerInput, initialOutput);

                const sandbox = path.dirname(initialOutput.env.SANDBOX_DERIVED_DATA);
                fs.unlinkSync(path.join(sandbox, "owner.pid"));
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(sandbox, old, old);

                const originalRm = fs.promises.rm;
                let cleanupPath = "";
                let writerRepublished = false;
                fs.promises.rm = async (candidate, options) => {
                  if (!cleanupPath) {
                    cleanupPath = String(candidate);
                    const lock = path.join(cleanupPath, ".owner.lock");
                    if (fs.existsSync(lock)) fs.unlinkSync(lock);

                    const republishedOutput = { env: {} };
                    await writer["shell.env"](writerInput, republishedOutput);
                    writerRepublished = Boolean(republishedOutput.env.SANDBOX_DERIVED_DATA);
                  }
                  return originalRm(candidate, options);
                };

                try {
                  const sweeper = await plugin.server({});
                  await sweeper.config({});
                  await sweeper["shell.env"](
                    { cwd: process.cwd(), sessionID: "sweeper-session" },
                    { env: {} },
                  );
                } finally {
                  fs.promises.rm = originalRm;
                }

                console.log(JSON.stringify({
                  cleanupPath,
                  originalSandbox: sandbox,
                  writerRepublished,
                  sandboxExists: fs.existsSync(sandbox),
                  ownerExists: fs.existsSync(path.join(sandbox, "owner.pid")),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertNotEqual(result["cleanupPath"], result["originalSandbox"])
        self.assertTrue(result["writerRepublished"])
        self.assertTrue(result["sandboxExists"])
        self.assertTrue(result["ownerExists"])

    def test_stale_sweep_restores_owner_published_during_quarantine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=publish-during-quarantine"
                )).default;
                const writer = await plugin.server({});
                await writer.config({});

                const writerInput = { cwd: process.cwd(), sessionID: "writer-session" };
                const initialOutput = { env: {} };
                await writer["shell.env"](writerInput, initialOutput);

                const sandbox = path.dirname(initialOutput.env.SANDBOX_DERIVED_DATA);
                const ownerPath = path.join(sandbox, "owner.pid");
                const publishedOwner = fs.readFileSync(ownerPath, "utf8");
                fs.unlinkSync(ownerPath);
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(sandbox, old, old);

                const originalRenameSync = fs.renameSync;
                let replacementPublished = false;
                let quarantinePath = "";
                fs.renameSync = (source, destination) => {
                  if (String(source) === sandbox && !replacementPublished) {
                    quarantinePath = String(destination);
                    const lock = path.join(sandbox, ".owner.lock");
                    if (fs.existsSync(lock)) fs.unlinkSync(lock);
                    fs.writeFileSync(
                      lock,
                      "00000000-0000-4000-8000-000000000002\\n",
                    );
                    fs.writeFileSync(ownerPath, publishedOwner);
                    replacementPublished = true;
                  }
                  return originalRenameSync(source, destination);
                };

                try {
                  const sweeper = await plugin.server({});
                  await sweeper.config({});
                  await sweeper["shell.env"](
                    { cwd: process.cwd(), sessionID: "sweeper-session" },
                    { env: {} },
                  );
                } finally {
                  fs.renameSync = originalRenameSync;
                }

                console.log(JSON.stringify({
                  replacementPublished,
                  sandboxExists: fs.existsSync(sandbox),
                  ownerExists: fs.existsSync(path.join(sandbox, "owner.pid")),
                  quarantineExists: quarantinePath ? fs.existsSync(quarantinePath) : false,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["replacementPublished"], result)
        self.assertTrue(result["sandboxExists"])
        self.assertTrue(result["ownerExists"])
        self.assertFalse(result["quarantineExists"])

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

                const psCall = calls.find(({ command }) => command === "/bin/ps");
                console.log(JSON.stringify({
                  command: psCall?.command,
                  locale: psCall?.options?.env?.LC_ALL,
                  language: psCall?.options?.env?.LANG,
                  timezone: psCall?.options?.env?.TZ,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["command"], "/bin/ps")
        self.assertEqual(result["locale"], "C")
        self.assertEqual(result["language"], "C")
        self.assertEqual(result["timezone"], "UTC")

    def test_process_start_token_times_out_and_continues_shell_setup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import { mock } from "node:test";

                let commandUsed = "";
                let killedWith = "";
                let timeoutMs = 0;
                const spawn = (command) => {
                  commandUsed = command;
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  child.kill = (signal) => {
                    killedWith = signal;
                    return true;
                  };
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const originalSetTimeout = globalThis.setTimeout;
                const originalClearTimeout = globalThis.clearTimeout;
                globalThis.setTimeout = (callback, delay) => {
                  timeoutMs = delay;
                  queueMicrotask(callback);
                  return 1;
                };
                globalThis.clearTimeout = () => {};

                let output;
                try {
                  const plugin = (await import(
                    "./XcodeBuildTools/opencode-plugin.js?test=process-start-timeout"
                  )).default;
                  const hooks = await plugin.server({});
                  await hooks.config({});
                  output = { env: {} };
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID: "current-session" },
                    output,
                  );
                } finally {
                  globalThis.setTimeout = originalSetTimeout;
                  globalThis.clearTimeout = originalClearTimeout;
                }

                console.log(JSON.stringify({
                  commandUsed,
                  killedWith,
                  timeoutMs,
                  sandboxConfigured: Boolean(output.env.SANDBOX_DERIVED_DATA),
                }));
                """,
                {"TMPDIR": tmpdir},
                timeout=2,
            )

        self.assertEqual(result["commandUsed"], "/bin/ps")
        self.assertEqual(result["killedWith"], "SIGTERM")
        self.assertGreater(result["timeoutMs"], 0)
        self.assertTrue(result["sandboxConfigured"])

    def test_process_start_token_bounds_stdout(self):
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
                    child.stdout.emit("data", "x".repeat(10_000));
                    child.emit("close", 0);
                  });
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=bounded-process-start"
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
                  tokenLength: owner.split(/\\r?\\n/)[2].length,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertLessEqual(result["tokenLength"], 256)

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

    def test_owner_marker_update_failure_preserves_previous_owner(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=atomic-owner-write"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const output = { env: {} };
                const input = { cwd: process.cwd(), sessionID: "current-session" };
                await hooks["shell.env"](input, output);

                const sandbox = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                const ownerPath = path.join(sandbox, "owner.pid");
                const originalOwner = fs.readFileSync(ownerPath, "utf8");
                const originalWriteFileSync = fs.writeFileSync;

                fs.writeFileSync = (filePath, ...args) => {
                  if (String(filePath).includes("owner.pid")) {
                    originalWriteFileSync(filePath, "", "utf8");
                    throw new Error("simulated interrupted owner write");
                  }
                  return originalWriteFileSync(filePath, ...args);
                };
                try {
                  await hooks["shell.env"](input, { env: {} });
                } finally {
                  fs.writeFileSync = originalWriteFileSync;
                }

                const finalOwner = fs.readFileSync(ownerPath, "utf8");
                console.log(JSON.stringify({ preserved: finalOwner === originalOwner }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["preserved"])

    def test_owner_lock_release_preserves_a_replacement_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const replacementToken = "00000000-0000-4000-8000-000000000002";
                const originalRenameSync = fs.renameSync;
                let replacementInstalled = false;
                fs.renameSync = (source, destination) => {
                  if (
                    String(source).endsWith(".owner.lock") &&
                    String(destination).includes(".release") &&
                    !replacementInstalled
                  ) {
                    replacementInstalled = true;
                    fs.unlinkSync(source);
                    fs.writeFileSync(source, `${replacementToken}\\n`);
                  }
                  return originalRenameSync(source, destination);
                };

                let output;
                try {
                  const plugin = (await import(
                    "./XcodeBuildTools/opencode-plugin.js?test=owner-lock-release"
                  )).default;
                  const hooks = await plugin.server({});
                  await hooks.config({});
                  output = { env: {} };
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID: "current-session" },
                    output,
                  );
                } finally {
                  fs.renameSync = originalRenameSync;
                }

                const sandbox = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                const lock = path.join(sandbox, ".owner.lock");
                console.log(JSON.stringify({
                  replacementInstalled,
                  lockToken: fs.existsSync(lock) ? fs.readFileSync(lock, "utf8").trim() : "",
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["replacementInstalled"])
        self.assertEqual(
            result["lockToken"], "00000000-0000-4000-8000-000000000002"
        )

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

    def test_failed_session_deletion_is_reclaimed_by_replacement_instance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=failed-session-delete"
                )).default;
                const first = await plugin.server({});
                await first.config({});

                const firstOutput = { env: {} };
                await first["shell.env"](
                  { cwd: process.cwd(), sessionID: "deleted-session" },
                  firstOutput,
                );
                const firstSandbox = path.dirname(firstOutput.env.SANDBOX_DERIVED_DATA);
                const sandboxRoot = path.dirname(firstSandbox);

                const originalRm = fs.promises.rm;
                const originalWriteFileSync = fs.writeFileSync;
                let cleanupRejected = false;
                let markerWriteFailed = false;
                let lateWriterPublished = false;
                fs.promises.rm = async () => {
                  cleanupRejected = true;
                  const lock = path.join(firstSandbox, ".owner.lock");
                  if (fs.existsSync(lock)) fs.unlinkSync(lock);
                  const lateOutput = { env: {} };
                  await first["shell.env"](
                    { cwd: process.cwd(), sessionID: "deleted-session" },
                    lateOutput,
                  );
                  lateWriterPublished = Boolean(lateOutput.env.SANDBOX_DERIVED_DATA);
                  throw new Error("simulated cleanup failure");
                };
                fs.writeFileSync = (filePath, ...args) => {
                  if (String(filePath).endsWith(".cleanup.tmp")) {
                    markerWriteFailed = true;
                    throw new Error("simulated cleanup marker failure");
                  }
                  return originalWriteFileSync(filePath, ...args);
                };
                try {
                  await first.event({
                    event: {
                      type: "session.deleted",
                      properties: { info: { id: "deleted-session" } },
                    },
                  });
                } finally {
                  fs.promises.rm = originalRm;
                  fs.writeFileSync = originalWriteFileSync;
                }

                const replacement = await plugin.server({});
                await replacement.config({});
                const replacementOutput = { env: {} };
                await replacement["shell.env"](
                  { cwd: process.cwd(), sessionID: "replacement-session" },
                  replacementOutput,
                );
                const replacementSandbox = path.dirname(
                  replacementOutput.env.SANDBOX_DERIVED_DATA,
                );
                const remaining = fs.readdirSync(sandboxRoot).filter(
                  (entry) => path.join(sandboxRoot, entry) !== replacementSandbox,
                );

                console.log(JSON.stringify({
                  cleanupRejected,
                  lateWriterPublished,
                  markerWriteFailed,
                  remaining,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["cleanupRejected"])
        self.assertTrue(result["markerWriteFailed"])
        self.assertFalse(result["lateWriterPublished"])
        self.assertEqual(result["remaining"], [])

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

                for (let attempt = 0; attempt < 100; attempt += 1) {
                  if (!sandboxes.some((sandbox) => fs.existsSync(sandbox))) break;
                  await new Promise((resolve) => setTimeout(resolve, 5));
                }

                console.log(JSON.stringify({
                  disposeAvailable,
                  remaining: sandboxes.filter((sandbox) => fs.existsSync(sandbox)),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["disposeAvailable"])
        self.assertEqual(result["remaining"], [])

    def test_plugin_dispose_allows_parent_exit_while_cleanup_is_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import { mock } from "node:test";

                let cleanupStarted = false;
                let cleanupUnrefed = false;
                const spawn = (command) => {
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  child.kill = () => true;

                  if (command === "/bin/rm") {
                    cleanupStarted = true;
                    const activeCleanup = setTimeout(() => {}, 15_000);
                    child.unref = () => {
                      cleanupUnrefed = true;
                      activeCleanup.unref();
                    };
                  } else {
                    child.unref = () => {};
                    queueMicrotask(() => {
                      if (command === "/bin/ps") child.stdout.emit("data", "canonical-start\\n");
                      child.emit("exit", 0);
                      child.emit("close", 0);
                    });
                  }
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=parent-exit-dispose"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  { env: {} },
                );

                await hooks.dispose();

                console.log(JSON.stringify({ cleanupStarted, cleanupUnrefed }));
                """,
                {"TMPDIR": tmpdir},
                timeout=5,
            )

        self.assertTrue(result["cleanupStarted"])
        self.assertTrue(result["cleanupUnrefed"])

    def test_plugin_dispose_starts_detached_cleanup_process(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import { mock } from "node:test";

                const calls = [];
                const spawn = (command, args = [], options = {}) => {
                  const call = { command, args, options, unrefCalled: false };
                  calls.push(call);
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  child.kill = () => true;
                  child.unref = () => { call.unrefCalled = true; };
                  queueMicrotask(() => {
                    if (command === "/bin/ps") {
                      child.stdout.emit("data", "canonical-start\\n");
                    }
                    child.emit("exit", 0);
                    child.emit("close", 0);
                  });
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=detached-dispose"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  { env: {} },
                );
                await hooks.dispose();

                const removal = calls.find(({ command }) => command === "/bin/rm");
                console.log(JSON.stringify({
                  removalStarted: Boolean(removal),
                  args: removal?.args,
                  detached: removal?.options?.detached,
                  stdio: removal?.options?.stdio,
                  unrefCalled: removal?.unrefCalled,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["removalStarted"])
        self.assertEqual(result["args"][0], "-rf")
        self.assertTrue(result["detached"])
        self.assertEqual(result["stdio"], "ignore")
        self.assertTrue(result["unrefCalled"])

    def test_dispose_cleanup_failures_are_reclaimed_by_replacement_instance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import fs from "node:fs";
                import path from "node:path";
                import { mock } from "node:test";

                let activeHooks;
                let activeSessionID = "";
                let cleanupMode = "throw";
                const lateWrites = [];
                const spawn = (command) => {
                  if (command === "/bin/rm" && activeHooks) {
                    const output = { env: {} };
                    lateWrites.push({
                      mode: cleanupMode,
                      output,
                      promise: activeHooks["shell.env"](
                        { cwd: process.cwd(), sessionID: activeSessionID },
                        output,
                      ),
                    });
                  }
                  if (command === "/bin/rm" && cleanupMode === "throw") {
                    throw new Error("simulated spawn failure");
                  }

                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  child.kill = () => true;
                  child.unref = () => {};
                  queueMicrotask(() => {
                    if (command === "/bin/ps") child.stdout.emit("data", "canonical-start\\n");
                    const code = command === "/bin/rm" && cleanupMode === "nonzero" ? 1 : 0;
                    child.emit("exit", code);
                    child.emit("close", code);
                  });
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=failed-dispose-cleanup"
                )).default;
                const results = {};

                for (const mode of ["throw", "nonzero"]) {
                  cleanupMode = mode;
                  const first = await plugin.server({});
                  await first.config({});
                  const firstOutput = { env: {} };
                  await first["shell.env"](
                    { cwd: process.cwd(), sessionID: `${mode}-session` },
                    firstOutput,
                  );
                  const firstSandbox = path.dirname(firstOutput.env.SANDBOX_DERIVED_DATA);
                  activeHooks = first;
                  activeSessionID = `${mode}-session`;

                  const originalRenameSync = fs.renameSync;
                  fs.renameSync = (source, destination) => {
                    if (
                      String(source) === firstSandbox &&
                      String(destination).includes(".quarantine-")
                    ) {
                      const error = new Error("simulated busy sandbox");
                      error.code = "EBUSY";
                      throw error;
                    }
                    return originalRenameSync(source, destination);
                  };
                  try {
                    await first.dispose();
                  } finally {
                    fs.renameSync = originalRenameSync;
                  }
                  await Promise.all(
                    lateWrites.filter((write) => write.mode === mode).map((write) => write.promise),
                  );
                  results[`${mode}LateWriter`] = lateWrites
                    .filter((write) => write.mode === mode)
                    .some((write) => Boolean(write.output.env.SANDBOX_DERIVED_DATA));
                  await new Promise((resolve) => setImmediate(resolve));

                  const replacement = await plugin.server({});
                  await replacement.config({});
                  const replacementOutput = { env: {} };
                  await replacement["shell.env"](
                    { cwd: process.cwd(), sessionID: `${mode}-replacement` },
                    replacementOutput,
                  );
                  const replacementSandbox = path.dirname(
                    replacementOutput.env.SANDBOX_DERIVED_DATA,
                  );
                  const sandboxRoot = path.dirname(firstSandbox);
                  results[mode] = fs.readdirSync(sandboxRoot).filter(
                    (entry) => path.join(sandboxRoot, entry) !== replacementSandbox,
                  );

                  for (const entry of fs.readdirSync(sandboxRoot)) {
                    await fs.promises.rm(path.join(sandboxRoot, entry), {
                      recursive: true,
                      force: true,
                    });
                  }
                }

                console.log(JSON.stringify(results));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["throw"], [])
        self.assertEqual(result["nonzero"], [])
        self.assertFalse(result["throwLateWriter"])
        self.assertFalse(result["nonzeroLateWriter"])

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
                for (let attempt = 0; attempt < 100; attempt += 1) {
                  if (!fs.existsSync(firstSandbox)) break;
                  await new Promise((resolve) => setTimeout(resolve, 5));
                }
                const existsAfterFirstDispose = fs.existsSync(sandbox);
                await second.dispose();
                for (let attempt = 0; attempt < 100; attempt += 1) {
                  if (!fs.existsSync(sandbox)) break;
                  await new Promise((resolve) => setTimeout(resolve, 5));
                }

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
            result = self.run_node(
                """
                import { EventEmitter } from "node:events";
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";
                import { mock } from "node:test";

                const spawn = () => {
                  const child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  queueMicrotask(() => {
                    child.stdout.emit("data", "current-start-time\\n");
                    child.emit("close", 0);
                  });
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const sandboxRoot = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox");
                const stale = path.join(sandboxRoot, "reused-pid-session");
                fs.mkdirSync(path.join(stale, "build"), { recursive: true });
                fs.writeFileSync(
                  path.join(stale, "owner.pid"),
                  `${process.pid}\\nopencode\\nnot-the-current-start-time\\n00000000-0000-4000-8000-000000000001\\n`,
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
                {"TMPDIR": tmpdir},
            )

        self.assertFalse(result["staleExists"])


if __name__ == "__main__":
    unittest.main()
