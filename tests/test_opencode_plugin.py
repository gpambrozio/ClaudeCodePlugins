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
            data_home = Path(tmpdir) / "data-home"
            plugin_root.mkdir()
            worktree.mkdir()
            directory.mkdir()
            data_home.mkdir()
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
                    "XDG_DATA_HOME": str(data_home),
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
                        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
                        "CLAUDE_PLUGIN_DATA": str(
                            data_home / "opencode" / "plugin-data" / "plugin"
                        ),
                        "CLAUDE_PROJECT_DIR": str(worktree),
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

    def test_project_directory_distinguishes_non_git_sentinel_from_git_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "plugin"
            data_home = Path(tmpdir) / "data-home"
            plugin_root.mkdir()
            data_home.mkdir()
            (plugin_root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "local": {
                                "command": "node",
                                "args": ["--project=${CLAUDE_PROJECT_DIR}"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_node(
                """
                import { createOpenCodePlugin } from "./common/opencode-plugin.js?test=project-directory-selection";

                const server = createOpenCodePlugin(process.env.TEST_PLUGIN_ROOT);

                async function localMcp(input) {
                  const hooks = await server(input);
                  const config = {};
                  await hooks.config(config);
                  return config.mcp.local;
                }

                console.log(JSON.stringify({
                  nonGit: await localMcp({
                    worktree: "/",
                    directory: "/tmp/non-git-project",
                    project: { vcs: undefined },
                  }),
                  gitRoot: await localMcp({
                    worktree: "/",
                    directory: "/workspace/subdir",
                    project: { vcs: "git" },
                  }),
                  legacyNonGit: await localMcp({
                    worktree: "/",
                    directory: "/tmp/legacy-non-git-project",
                  }),
                  git: await localMcp({
                    worktree: "/tmp/git-worktree",
                    directory: "/tmp/git-directory",
                  }),
                  noWorktree: await localMcp({ directory: "/tmp/directory-only" }),
                }));
                """,
                {
                    "TEST_PLUGIN_ROOT": str(plugin_root),
                    "XDG_DATA_HOME": str(data_home),
                },
            )

        self.assertEqual(
            result["nonGit"]["command"],
            ["node", "--project=/tmp/non-git-project"],
        )
        self.assertEqual(
            result["nonGit"]["environment"]["CLAUDE_PROJECT_DIR"],
            "/tmp/non-git-project",
        )
        self.assertEqual(
            result["gitRoot"]["command"],
            ["node", "--project=/"],
        )
        self.assertEqual(
            result["gitRoot"]["environment"]["CLAUDE_PROJECT_DIR"],
            "/",
        )
        self.assertEqual(
            result["legacyNonGit"]["command"],
            ["node", "--project=/tmp/legacy-non-git-project"],
        )
        self.assertEqual(
            result["legacyNonGit"]["environment"]["CLAUDE_PROJECT_DIR"],
            "/tmp/legacy-non-git-project",
        )
        self.assertEqual(
            result["git"]["command"],
            ["node", "--project=/tmp/git-worktree"],
        )
        self.assertEqual(
            result["git"]["environment"]["CLAUDE_PROJECT_DIR"],
            "/tmp/git-worktree",
        )
        self.assertEqual(
            result["noWorktree"]["command"],
            ["node", "--project=/tmp/directory-only"],
        )
        self.assertEqual(
            result["noWorktree"]["environment"]["CLAUDE_PROJECT_DIR"],
            "/tmp/directory-only",
        )

    def test_local_mcp_receives_plugin_compatibility_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "plugin"
            project_dir = Path(tmpdir) / "project"
            data_home = Path(tmpdir) / "data-home"
            (plugin_root / ".claude-plugin").mkdir(parents=True)
            project_dir.mkdir()
            data_home.mkdir()
            (plugin_root / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "Example Plugin"}),
                encoding="utf-8",
            )
            (plugin_root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "local": {
                                "command": "node",
                                "environment": {
                                    "CUSTOM": "kept",
                                    "CLAUDE_PLUGIN_ROOT": "/wrong/plugin-root",
                                    "CLAUDE_PLUGIN_DATA": "/wrong/plugin-data",
                                    "CLAUDE_PROJECT_DIR": "/wrong/project-dir",
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_node(
                """
                import { createOpenCodePlugin } from "./common/opencode-plugin.js?test=mcp-compatibility-environment";

                const server = createOpenCodePlugin(process.env.TEST_PLUGIN_ROOT);
                const hooks = await server({ directory: process.env.TEST_PROJECT_DIR });
                const config = {};
                await hooks.config(config);

                console.log(JSON.stringify(config.mcp.local.environment));
                """,
                {
                    "TEST_PLUGIN_ROOT": str(plugin_root),
                    "TEST_PROJECT_DIR": str(project_dir),
                    "XDG_DATA_HOME": str(data_home),
                },
            )

            plugin_data = data_home / "opencode" / "plugin-data" / "Example-Plugin"
            self.assertEqual(
                result,
                {
                    "CUSTOM": "kept",
                    "CLAUDE_PLUGIN_ROOT": str(plugin_root),
                    "CLAUDE_PLUGIN_DATA": str(plugin_data),
                    "CLAUDE_PROJECT_DIR": str(project_dir),
                },
            )
            self.assertTrue(plugin_data.is_dir())

    def test_plugin_data_placeholder_is_stable_across_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "plugin"
            first_project = Path(tmpdir) / "first-project"
            second_project = Path(tmpdir) / "second-project"
            data_home = Path(tmpdir) / "data-home"
            (plugin_root / ".claude-plugin").mkdir(parents=True)
            first_project.mkdir()
            second_project.mkdir()
            data_home.mkdir()
            (plugin_root / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "Example Plugin"}),
                encoding="utf-8",
            )
            (plugin_root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "local": {
                                "command": "${CLAUDE_PLUGIN_DATA}/bin/server",
                                "environment": {
                                    "PLUGIN_DATA": "${CLAUDE_PLUGIN_DATA}",
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_node(
                """
                import { createOpenCodePlugin } from "./common/opencode-plugin.js?test=stable-plugin-data";

                delete process.env.CLAUDE_PLUGIN_DATA;
                const server = createOpenCodePlugin(process.env.TEST_PLUGIN_ROOT);

                const firstHooks = await server({ directory: process.env.TEST_FIRST_PROJECT });
                const firstConfig = {};
                await firstHooks.config(firstConfig);

                const secondHooks = await server({ directory: process.env.TEST_SECOND_PROJECT });
                const secondConfig = {};
                await secondHooks.config(secondConfig);

                console.log(JSON.stringify({
                  first: firstConfig.mcp.local,
                  second: secondConfig.mcp.local,
                }));
                """,
                {
                    "TEST_PLUGIN_ROOT": str(plugin_root),
                    "TEST_FIRST_PROJECT": str(first_project),
                    "TEST_SECOND_PROJECT": str(second_project),
                    "XDG_DATA_HOME": str(data_home),
                },
            )

            plugin_data = data_home / "opencode" / "plugin-data" / "Example-Plugin"
            self.assertEqual(
                result["first"]["command"],
                [str(plugin_data / "bin" / "server")],
            )
            self.assertEqual(
                result["second"]["command"],
                [str(plugin_data / "bin" / "server")],
            )
            self.assertEqual(result["first"]["environment"]["PLUGIN_DATA"], str(plugin_data))
            self.assertEqual(result["second"]["environment"]["PLUGIN_DATA"], str(plugin_data))
            self.assertTrue(plugin_data.is_dir())

    def test_mcp_registration_preserves_existing_endpoints_under_other_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "plugin"
            data_home = Path(tmpdir) / "data-home"
            plugin_root.mkdir()
            data_home.mkdir()
            (plugin_root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "pluginRemoteDuplicate": {
                                "url": "https://shared.example.test/mcp",
                            },
                            "pluginLocalDuplicate": {
                                "command": "node",
                                "args": ["server.js", "--shared"],
                                "cwd": "/workspace/shared",
                                "environment": {
                                    "MODE": "workflow",
                                    "WORKFLOW": "workspace",
                                },
                            },
                            "pluginLocalDifferentCwd": {
                                "command": "node",
                                "args": ["server.js", "--shared"],
                                "cwd": "/workspace/other",
                                "environment": {
                                    "MODE": "workflow",
                                    "WORKFLOW": "workspace",
                                },
                            },
                            "pluginLocalDifferentEnvironment": {
                                "command": "node",
                                "args": ["server.js", "--shared"],
                                "cwd": "/workspace/shared",
                                "environment": {
                                    "MODE": "server",
                                    "WORKFLOW": "workspace",
                                },
                            },
                            "pluginRemoteDistinct": {
                                "url": "https://distinct.example.test/mcp",
                            },
                            "pluginLocalDifferentArgs": {
                                "command": "node",
                                "args": ["server.js", "--distinct"],
                                "cwd": "/workspace/shared",
                                "environment": {
                                    "MODE": "workflow",
                                    "WORKFLOW": "workspace",
                                },
                            },
                            "sameName": {
                                "url": "https://plugin.example.test/mcp",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_node(
                """
                import { createOpenCodePlugin } from "./common/opencode-plugin.js?test=mcp-endpoint-deduplication";

                const existingRemote = {
                  type: "remote",
                  url: "https://shared.example.test/mcp",
                  headers: { "X-User": "preserved" },
                };
                const existingLocal = {
                  type: "local",
                  command: ["node", "server.js", "--shared"],
                  cwd: "/workspace/shared",
                  environment: {
                    WORKFLOW: "workspace",
                    CLAUDE_PROJECT_DIR: "/user/project",
                    MODE: "workflow",
                    CLAUDE_PLUGIN_DATA: "/user/plugin-data",
                    CLAUDE_PLUGIN_ROOT: "/user/plugin-root",
                  },
                };
                const existingLocalBefore = JSON.stringify(existingLocal);
                const existingSameName = {
                  type: "remote",
                  url: "https://user.example.test/mcp",
                };
                const config = {
                  mcp: {
                    userRemote: existingRemote,
                    userLocal: existingLocal,
                    sameName: existingSameName,
                  },
                };

                const server = createOpenCodePlugin(process.env.TEST_PLUGIN_ROOT);
                const hooks = await server({ directory: process.cwd() });
                await hooks.config(config);

                console.log(JSON.stringify({
                  keys: Object.keys(config.mcp),
                  existingRemoteUnchanged:
                    config.mcp.userRemote === existingRemote &&
                    JSON.stringify(config.mcp.userRemote) === JSON.stringify({
                      type: "remote",
                      url: "https://shared.example.test/mcp",
                      headers: { "X-User": "preserved" },
                    }),
                  existingLocalUnchanged:
                    config.mcp.userLocal === existingLocal &&
                    JSON.stringify(config.mcp.userLocal) === existingLocalBefore,
                  sameNameUnchanged: config.mcp.sameName === existingSameName,
                  distinctRemote: config.mcp.pluginRemoteDistinct,
                  differentCwd: config.mcp.pluginLocalDifferentCwd,
                  differentEnvironment:
                    config.mcp.pluginLocalDifferentEnvironment,
                  differentArgs: config.mcp.pluginLocalDifferentArgs,
                }));
                """,
                {
                    "TEST_PLUGIN_ROOT": str(plugin_root),
                    "XDG_DATA_HOME": str(data_home),
                },
            )

        self.assertEqual(
            result["keys"],
            [
                "userRemote",
                "userLocal",
                "sameName",
                "pluginLocalDifferentCwd",
                "pluginLocalDifferentEnvironment",
                "pluginRemoteDistinct",
                "pluginLocalDifferentArgs",
            ],
        )
        self.assertTrue(result["existingRemoteUnchanged"])
        self.assertTrue(result["existingLocalUnchanged"])
        self.assertTrue(result["sameNameUnchanged"])
        self.assertEqual(
            result["distinctRemote"],
            {"type": "remote", "url": "https://distinct.example.test/mcp"},
        )
        self.assertEqual(result["differentCwd"]["cwd"], "/workspace/other")
        self.assertEqual(result["differentCwd"]["environment"]["MODE"], "workflow")
        self.assertEqual(result["differentEnvironment"]["cwd"], "/workspace/shared")
        self.assertEqual(
            result["differentEnvironment"]["environment"]["MODE"], "server"
        )
        self.assertEqual(
            result["differentArgs"]["command"],
            ["node", "server.js", "--distinct"],
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
              if (command === "/usr/bin/pgrep" && args[0] === "-f") code = 1;
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
              approvalLaunched: calls.some(([command]) => command.endsWith("approve-xcode-mcp.sh")),
            }));
            """
        )

        self.assertEqual(result["registeredMcp"], ["sosumi"])
        self.assertFalse(result["detected"])
        self.assertFalse(result["approvalLaunched"])

    def test_xcode_mcp_ignores_mcpbridge_in_an_unrelated_command_argument(self):
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
              queueMicrotask(() => child.emit("exit", 0));
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=ignore-mcpbridge-argument"
            )).default;
            const hooks = await plugin.server({});
            const config = {
              mcp: {
                unrelated: {
                  type: "local",
                  command: ["/usr/bin/printf", "--label", "mcpbridge"],
                },
              },
            };
            await hooks.config(config);

            const output = { system: [] };
            await hooks["experimental.chat.system.transform"](
              { sessionID: "session-1" },
              output,
            );

            console.log(JSON.stringify({
              detected: output.system[0].includes("Xcode MCP server detected"),
              approvalLaunched: calls.some(
                ([command]) => command.endsWith("approve-xcode-mcp.sh"),
              ),
            }));
            """
        )

        self.assertFalse(result["detected"])
        self.assertFalse(result["approvalLaunched"])

    def test_xcode_mcp_ignores_mcpbridge_after_a_different_xcrun_tool(self):
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
              queueMicrotask(() => child.emit("exit", 0));
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=ignore-late-xcrun-argument"
            )).default;
            const hooks = await plugin.server({});
            const config = {
              mcp: {
                unrelated: {
                  type: "local",
                  command: ["xcrun", "swift", "--label", "mcpbridge"],
                },
              },
            };
            await hooks.config(config);

            const output = { system: [] };
            await hooks["experimental.chat.system.transform"](
              { sessionID: "session-1" },
              output,
            );

            console.log(JSON.stringify({
              detected: output.system[0].includes("Xcode MCP server detected"),
              approvalLaunched: calls.some(
                ([command]) => command.endsWith("approve-xcode-mcp.sh"),
              ),
            }));
            """
        )

        self.assertFalse(result["detected"])
        self.assertFalse(result["approvalLaunched"])

    def test_xcode_mcp_recognizes_direct_and_option_prefixed_xcrun_tools(self):
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
              queueMicrotask(() => child.emit("exit", 0));
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=xcrun-tool-operands"
            )).default;
            const commands = [
              ["/usr/local/bin/mcpbridge"],
              ["xcrun", "mcpbridge"],
              ["xcrun", "--sdk", "macosx", "--toolchain", "swift", "mcpbridge"],
              ["xcrun", "--sdk=macosx", "--toolchain=swift", "mcpbridge"],
              ["xcrun", "--find", "--", "mcpbridge"],
            ];
            const results = [];

            for (const [index, command] of commands.entries()) {
              const hooks = await plugin.server({});
              const config = { mcp: { xcode: { type: "local", command } } };
              await hooks.config(config);
              const callsBefore = calls.length;
              const output = { system: [] };
              await hooks["experimental.chat.system.transform"](
                { sessionID: `session-${index}` },
                output,
              );
              results.push({
                detected: output.system[0].includes("Xcode MCP server detected"),
                approvalLaunched: calls.slice(callsBefore).some(
                  ([executable]) => executable.endsWith("approve-xcode-mcp.sh"),
                ),
              });
            }

            console.log(JSON.stringify(results));
            """
        )

        self.assertTrue(all(item["detected"] for item in result))
        self.assertTrue(all(item["approvalLaunched"] for item in result))

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
              if (command === "/usr/bin/pgrep" && args[0] === "-x") code = xcodeRunning ? 0 : 1;
              if (command === "/usr/bin/pgrep" && args[0] === "-f") code = 1;
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

    def test_xcode_mcp_detection_force_kills_and_unrefs_a_timed_out_probe(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const signals = [];
            let unrefCalls = 0;
            const spawn = () => {
              const child = new EventEmitter();
              child.kill = (signal) => {
                signals.push(signal);
                return true;
              };
              child.unref = () => {
                unrefCalls += 1;
              };
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const originalSetTimeout = globalThis.setTimeout;
            const originalClearTimeout = globalThis.clearTimeout;
            globalThis.setTimeout = (callback) => {
              queueMicrotask(callback);
              return 1;
            };
            globalThis.clearTimeout = () => {};

            try {
              const plugin = (await import(
                "./XcodeBuildTools/opencode-plugin.js?test=force-kill-detection-timeout"
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
              await hooks["experimental.chat.system.transform"](
                { sessionID: "session-1" },
                { system: [] },
              );
            } finally {
              globalThis.setTimeout = originalSetTimeout;
              globalThis.clearTimeout = originalClearTimeout;
            }

            console.log(JSON.stringify({ signals, unrefCalls }));
            """
        )

        self.assertEqual(result["signals"], ["SIGTERM", "SIGKILL"])
        self.assertEqual(result["unrefCalls"], 1)

    def test_xcode_mcp_detection_rejects_success_reported_after_timeout(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const calls = [];
            const spawn = (command, args = []) => {
              calls.push([command, ...args]);
              const child = new EventEmitter();
              child.kill = (signal) => {
                if (signal === "SIGTERM") {
                  queueMicrotask(() => child.emit("exit", 0));
                }
                return true;
              };
              child.unref = () => {};
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const originalSetTimeout = globalThis.setTimeout;
            const originalClearTimeout = globalThis.clearTimeout;
            globalThis.setTimeout = (callback) => {
              queueMicrotask(callback);
              return 1;
            };
            globalThis.clearTimeout = () => {};

            let output;
            try {
              const plugin = (await import(
                "./XcodeBuildTools/opencode-plugin.js?test=timeout-cannot-succeed"
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
              output = { system: [] };
              await hooks["experimental.chat.system.transform"](
                { sessionID: "session-1" },
                output,
              );
            } finally {
              globalThis.setTimeout = originalSetTimeout;
              globalThis.clearTimeout = originalClearTimeout;
            }

            console.log(JSON.stringify({
              detected: output.system[0].includes("Xcode MCP server detected"),
              approvalLaunched: calls.some(
                ([command]) => command.endsWith("approve-xcode-mcp.sh"),
              ),
            }));
            """
        )

        self.assertFalse(result["detected"])
        self.assertFalse(result["approvalLaunched"])

    def test_xcode_mcp_probes_and_approval_use_fixed_system_paths(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import path from "node:path";
            import { mock } from "node:test";

            process.env.PATH = "/tmp/untrusted-path";
            const calls = [];
            const spawn = (command, args = [], options = {}) => {
              calls.push({ command, args, options });
              const child = new EventEmitter();
              child.pid = 4100 + calls.length;
              child.kill = () => true;
              child.unref = () => {};

              if (!command.endsWith("approve-xcode-mcp.sh")) {
                const code = command === "/usr/bin/pgrep" && args[0] === "-f" ? 1 : 0;
                queueMicrotask(() => child.emit("exit", code));
              }
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=fixed-system-paths"
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
            await hooks["experimental.chat.system.transform"](
              { sessionID: "session-1" },
              { system: [] },
            );

            const approval = calls.find(({ command }) =>
              command.endsWith("approve-xcode-mcp.sh")
            );
            console.log(JSON.stringify({
              probes: calls
                .filter(({ command }) => !command.endsWith("approve-xcode-mcp.sh"))
                .map(({ command, args }) => [command, ...args]),
              approval: approval && {
                command: approval.command,
                args: approval.args,
                cwd: approval.options.cwd,
                detached: approval.options.detached,
                path: approval.options.env.PATH,
                pluginRoot: approval.options.env.CLAUDE_PLUGIN_ROOT,
                absolute: path.isAbsolute(approval.command),
                underPluginRoot:
                  path.relative(approval.options.cwd, approval.command) ===
                  path.join("hooks", "approve-xcode-mcp.sh"),
              },
            }));
            """
        )

        self.assertEqual(
            result["probes"],
            [
                ["/usr/bin/xcrun", "--find", "mcpbridge"],
                ["/usr/bin/pgrep", "-x", "Xcode"],
                ["/usr/bin/pgrep", "-f", "mcpbridge"],
            ],
        )
        self.assertEqual(result["approval"]["args"], [])
        self.assertTrue(result["approval"]["absolute"])
        self.assertTrue(result["approval"]["underPluginRoot"])
        self.assertTrue(result["approval"]["detached"])
        self.assertEqual(result["approval"]["path"], "/usr/bin:/bin:/usr/sbin:/sbin")
        self.assertEqual(result["approval"]["cwd"], result["approval"]["pluginRoot"])

    def test_session_deletion_while_xcode_probe_is_pending_cancels_approval(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const calls = [];
            let releaseProbe;
            let markProbeStarted;
            const probeStarted = new Promise((resolve) => {
              markProbeStarted = resolve;
            });
            const spawn = (command, args = []) => {
              calls.push([command, ...args]);
              const child = new EventEmitter();
              child.pid = 4200 + calls.length;
              child.kill = () => true;
              child.unref = () => {};

              if (command.endsWith("xcrun")) {
                releaseProbe = () => child.emit("exit", 0);
                markProbeStarted();
              } else {
                queueMicrotask(() => child.emit("exit", 0));
              }
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=delete-during-xcode-probe"
            )).default;
            const hooks = await plugin.server({});
            await hooks.config({
              mcp: {
                xcode: {
                  type: "local",
                  command: ["xcrun", "mcpbridge"],
                },
              },
            });

            const firstOutput = { system: [] };
            const transform = hooks["experimental.chat.system.transform"](
              { sessionID: "deleted-session" },
              firstOutput,
            );
            await probeStarted;
            await hooks.event({
              event: {
                type: "session.deleted",
                properties: { info: { id: "deleted-session" } },
              },
            });
            releaseProbe();
            await transform;

            const callsAfterCompletion = calls.length;
            const secondOutput = { system: [] };
            await hooks["experimental.chat.system.transform"](
              { sessionID: "deleted-session" },
              secondOutput,
            );

            console.log(JSON.stringify({
              calls,
              callsAfterCompletion,
              callsAfterRepeat: calls.length,
              firstDetected: firstOutput.system[0].includes("Xcode MCP server detected"),
              secondDetected: secondOutput.system[0].includes("Xcode MCP server detected"),
              approvalLaunches: calls.filter(([command]) =>
                command.endsWith("approve-xcode-mcp.sh") ||
                command.endsWith("run-background.sh")
              ).length,
            }));
            """
        )

        self.assertEqual(result["callsAfterCompletion"], 1)
        self.assertEqual(result["callsAfterRepeat"], 1)
        self.assertFalse(result["firstDetected"])
        self.assertFalse(result["secondDetected"])
        self.assertEqual(result["approvalLaunches"], 0)

    def test_dispose_while_xcode_probe_is_pending_cancels_approval(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const calls = [];
            let releaseProbe;
            let markProbeStarted;
            const probeStarted = new Promise((resolve) => {
              markProbeStarted = resolve;
            });
            const spawn = (command, args = []) => {
              calls.push([command, ...args]);
              const child = new EventEmitter();
              child.pid = 4300 + calls.length;
              child.kill = () => true;
              child.unref = () => {};

              if (command.endsWith("xcrun")) {
                releaseProbe = () => child.emit("exit", 0);
                markProbeStarted();
              } else {
                queueMicrotask(() => child.emit("exit", 0));
              }
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const plugin = (await import(
              "./XcodeBuildTools/opencode-plugin.js?test=dispose-during-xcode-probe"
            )).default;
            const hooks = await plugin.server({});
            await hooks.config({
              mcp: {
                xcode: {
                  type: "local",
                  command: ["xcrun", "mcpbridge"],
                },
              },
            });

            const firstOutput = { system: [] };
            const transform = hooks["experimental.chat.system.transform"](
              { sessionID: "disposed-session" },
              firstOutput,
            );
            await probeStarted;
            await hooks.dispose();
            releaseProbe();
            await transform;

            const callsAfterCompletion = calls.length;
            const secondOutput = { system: [] };
            await hooks["experimental.chat.system.transform"](
              { sessionID: "disposed-session" },
              secondOutput,
            );

            console.log(JSON.stringify({
              callsAfterCompletion,
              callsAfterRepeat: calls.length,
              firstDetected: firstOutput.system[0].includes("Xcode MCP server detected"),
              secondDetected: secondOutput.system[0].includes("Xcode MCP server detected"),
              approvalLaunches: calls.filter(([command]) =>
                command.endsWith("approve-xcode-mcp.sh") ||
                command.endsWith("run-background.sh")
              ).length,
            }));
            """
        )

        self.assertEqual(result["callsAfterCompletion"], 1)
        self.assertEqual(result["callsAfterRepeat"], 1)
        self.assertFalse(result["firstDetected"])
        self.assertFalse(result["secondDetected"])
        self.assertEqual(result["approvalLaunches"], 0)

    def test_xcode_approval_process_groups_are_bounded_on_delete_and_dispose(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            const calls = [];
            const helpers = [];
            let nextPid = 4400;
            const spawn = (command, args = [], options = {}) => {
              calls.push([command, args, options]);
              const child = new EventEmitter();
              child.pid = nextPid++;
              child.kill = () => true;
              child.unref = () => {};

              if (
                command.endsWith("approve-xcode-mcp.sh") ||
                command.endsWith("run-background.sh")
              ) {
                helpers.push(child);
              } else {
                const code = command.endsWith("pgrep") && args[0] === "-f" ? 1 : 0;
                queueMicrotask(() => child.emit("exit", code));
              }
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const groupSignals = [];
            const graceDelays = [];
            const pendingGraceTimers = new Set();
            const originalKill = process.kill;
            const originalSetTimeout = globalThis.setTimeout;
            const originalClearTimeout = globalThis.clearTimeout;
            process.kill = (pid, signal) => {
              if (signal === 0) return true;
              groupSignals.push([pid, signal]);
              if (signal === "SIGTERM") {
                helpers.find((helper) => helper.pid === -pid)?.emit("exit", 0);
              }
              return true;
            };
            globalThis.setTimeout = (callback, delay, ...args) => {
              if (delay !== 250) return originalSetTimeout(callback, delay, ...args);
              graceDelays.push(delay);
              const timer = { active: true };
              pendingGraceTimers.add(timer);
              queueMicrotask(() => {
                if (!timer.active) return;
                timer.active = false;
                pendingGraceTimers.delete(timer);
                callback(...args);
              });
              return timer;
            };
            globalThis.clearTimeout = (timer) => {
              if (timer && typeof timer === "object" && "active" in timer) {
                timer.active = false;
                pendingGraceTimers.delete(timer);
                return;
              }
              originalClearTimeout(timer);
            };

            try {
              const plugin = (await import(
                "./XcodeBuildTools/opencode-plugin.js?test=approval-lifecycle"
              )).default;
              const serverConfig = {
                mcp: {
                  xcode: {
                    type: "local",
                    command: ["xcrun", "mcpbridge"],
                  },
                },
              };

              const deletedHooks = await plugin.server({});
              await deletedHooks.config(structuredClone(serverConfig));
              await deletedHooks["experimental.chat.system.transform"](
                { sessionID: "deleted-session" },
                { system: [] },
              );
              await deletedHooks.event({
                event: {
                  type: "session.deleted",
                  properties: { info: { id: "deleted-session" } },
                },
              });

              const disposedHooks = await plugin.server({});
              await disposedHooks.config(structuredClone(serverConfig));
              await disposedHooks["experimental.chat.system.transform"](
                { sessionID: "disposed-session" },
                { system: [] },
              );
              await disposedHooks.dispose();
            } finally {
              process.kill = originalKill;
              globalThis.setTimeout = originalSetTimeout;
              globalThis.clearTimeout = originalClearTimeout;
            }

            console.log(JSON.stringify({
              helperPids: helpers.map(({ pid }) => pid),
              groupSignals,
              graceDelays,
              pendingGraceTimers: pendingGraceTimers.size,
              listenerCounts: helpers.map((helper) => ({
                error: helper.listenerCount("error"),
                exit: helper.listenerCount("exit"),
              })),
            }));
            """
        )

        self.assertEqual(len(result["helperPids"]), 2)
        expected_signals = []
        for pid in result["helperPids"]:
            expected_signals.extend([[-pid, "SIGTERM"], [-pid, "SIGKILL"]])
        self.assertEqual(result["groupSignals"], expected_signals)
        self.assertEqual(result["graceDelays"], [250, 250])
        self.assertEqual(result["pendingGraceTimers"], 0)
        self.assertEqual(
            result["listenerCounts"],
            [{"error": 0, "exit": 0}, {"error": 0, "exit": 0}],
        )

    def test_dispose_awaits_session_deletion_approval_group_termination(self):
        result = self.run_node(
            """
            import { EventEmitter } from "node:events";
            import { mock } from "node:test";

            let helper;
            let nextPid = 4500;
            const spawn = (command, args = []) => {
              const child = new EventEmitter();
              child.pid = nextPid++;
              child.kill = () => true;
              child.unref = () => {};

              if (command.endsWith("approve-xcode-mcp.sh")) {
                helper = child;
              } else {
                const code = command.endsWith("pgrep") && args[0] === "-f" ? 1 : 0;
                queueMicrotask(() => child.emit("exit", code));
              }
              return child;
            };
            mock.module("node:child_process", { namedExports: { spawn } });

            const groupSignals = [];
            const graceTimers = [];
            const originalKill = process.kill;
            const originalSetTimeout = globalThis.setTimeout;
            const originalClearTimeout = globalThis.clearTimeout;
            process.kill = (pid, signal) => {
              if (signal === 0) return true;
              groupSignals.push([pid, signal]);
              if (signal === "SIGTERM") helper.emit("exit", 0);
              return true;
            };
            globalThis.setTimeout = (callback, delay, ...args) => {
              if (delay !== 250) return originalSetTimeout(callback, delay, ...args);
              const timer = { active: true, callback: () => callback(...args) };
              graceTimers.push(timer);
              return timer;
            };
            globalThis.clearTimeout = (timer) => {
              if (timer && typeof timer === "object" && "active" in timer) {
                timer.active = false;
                return;
              }
              originalClearTimeout(timer);
            };

            let disposeResolved = false;
            let resolvedBeforeEscalation;
            try {
              const plugin = (await import(
                "./XcodeBuildTools/opencode-plugin.js?test=concurrent-approval-cleanup"
              )).default;
              const hooks = await plugin.server({});
              await hooks.config({
                mcp: {
                  xcode: {
                    type: "local",
                    command: ["xcrun", "mcpbridge"],
                  },
                },
              });
              await hooks["experimental.chat.system.transform"](
                { sessionID: "shared-session" },
                { system: [] },
              );

              const deletion = hooks.event({
                event: {
                  type: "session.deleted",
                  properties: { info: { id: "shared-session" } },
                },
              });
              const disposal = hooks.dispose().then(() => {
                disposeResolved = true;
              });
              await new Promise((resolve) => setImmediate(resolve));
              resolvedBeforeEscalation = disposeResolved;

              for (const timer of graceTimers) {
                if (!timer.active) continue;
                timer.active = false;
                timer.callback();
              }
              await Promise.all([deletion, disposal]);
            } finally {
              process.kill = originalKill;
              globalThis.setTimeout = originalSetTimeout;
              globalThis.clearTimeout = originalClearTimeout;
            }

            console.log(JSON.stringify({
              resolvedBeforeEscalation,
              disposeResolved,
              groupSignals,
              graceTimerCount: graceTimers.length,
              listeners: {
                error: helper.listenerCount("error"),
                exit: helper.listenerCount("exit"),
              },
            }));
            """
        )

        self.assertFalse(result["resolvedBeforeEscalation"])
        self.assertTrue(result["disposeResolved"])
        self.assertEqual(result["graceTimerCount"], 1)
        self.assertEqual(
            result["groupSignals"],
            [[-4503, "SIGTERM"], [-4503, "SIGKILL"]],
        )
        self.assertEqual(result["listeners"], {"error": 0, "exit": 0})

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
              if (command === "/usr/bin/pgrep" && args[0] === "-f") code = 1;
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
              approvalLaunches: calls.filter(([command]) => command.endsWith("approve-xcode-mcp.sh")).length,
            }));
            """
        )

        self.assertEqual(result["approvalLaunches"], 2)

    def test_shell_env_rejects_a_symlinked_sandbox_root_without_touching_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const victim = path.join(os.tmpdir(), "victim");
                const documents = path.join(victim, "Documents");
                const keep = path.join(documents, "keep.txt");
                const sandboxRoot = path.join(
                  os.tmpdir(),
                  "opencode-xcodebuildtools-sandbox",
                );
                fs.mkdirSync(documents, { recursive: true });
                fs.writeFileSync(keep, "preserve me\\n", "utf8");
                const old = new Date(Date.now() - 61_000);
                fs.utimesSync(documents, old, old);
                fs.symlinkSync(victim, sandboxRoot, "dir");

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=symlinked-sandbox-root"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});
                const output = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  output,
                );

                console.log(JSON.stringify({
                  keepExists: fs.existsSync(keep),
                  victimEntries: fs.readdirSync(victim).sort(),
                  rootStillSymlink: fs.lstatSync(sandboxRoot).isSymbolicLink(),
                  derivedDataConfigured: Object.hasOwn(
                    output.env,
                    "SANDBOX_DERIVED_DATA",
                  ),
                  packagesConfigured: Object.hasOwn(
                    output.env,
                    "SANDBOX_PACKAGES",
                  ),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["keepExists"])
        self.assertEqual(result["victimEntries"], ["Documents"])
        self.assertTrue(result["rootStillSymlink"])
        self.assertFalse(result["derivedDataConfigured"])
        self.assertFalse(result["packagesConfigured"])

    def test_shell_env_secures_an_existing_current_user_sandbox_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import os from "node:os";
                import path from "node:path";

                const sandboxRoot = path.join(
                  os.tmpdir(),
                  "opencode-xcodebuildtools-sandbox",
                );
                fs.mkdirSync(sandboxRoot, { mode: 0o755 });
                fs.chmodSync(sandboxRoot, 0o755);

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=secure-existing-sandbox-root"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});
                const output = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "current-session" },
                  output,
                );

                console.log(JSON.stringify({
                  rootMode: fs.statSync(sandboxRoot).mode & 0o777,
                  rootIsDirectory: fs.lstatSync(sandboxRoot).isDirectory(),
                  derivedDataExists: fs.statSync(
                    output.env.SANDBOX_DERIVED_DATA,
                  ).isDirectory(),
                  packagesExist: fs.statSync(
                    output.env.SANDBOX_PACKAGES,
                  ).isDirectory(),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["rootMode"], 0o700)
        self.assertTrue(result["rootIsDirectory"])
        self.assertTrue(result["derivedDataExists"])
        self.assertTrue(result["packagesExist"])

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
                import fs from "node:fs";
                import path from "node:path";
                import { mock } from "node:test";

                let commandUsed = "";
                const signals = [];
                const timeoutDelays = [];
                const clearedTimers = [];
                let nextTimer = 0;
                let unrefCalls = 0;
                let stdoutDestroyCalls = 0;
                let child;
                const spawn = (command) => {
                  commandUsed = command;
                  child = new EventEmitter();
                  child.stdout = new EventEmitter();
                  child.stdout.setEncoding = () => {};
                  child.stdout.destroy = () => {
                    stdoutDestroyCalls += 1;
                  };
                  child.kill = (signal) => {
                    signals.push(signal);
                    if (signal === "SIGKILL") {
                      queueMicrotask(() => {
                        child.stdout.emit("data", "late-start-token\\n");
                        child.emit("close", 0);
                      });
                    }
                    return true;
                  };
                  child.unref = () => {
                    unrefCalls += 1;
                  };
                  return child;
                };
                mock.module("node:child_process", { namedExports: { spawn } });

                const originalSetTimeout = globalThis.setTimeout;
                const originalClearTimeout = globalThis.clearTimeout;
                globalThis.setTimeout = (callback, delay) => {
                  timeoutDelays.push(delay);
                  queueMicrotask(callback);
                  nextTimer += 1;
                  return nextTimer;
                };
                globalThis.clearTimeout = (timer) => {
                  clearedTimers.push(timer);
                };

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

                const sandbox = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                const owner = fs.readFileSync(path.join(sandbox, "owner.pid"), "utf8");

                console.log(JSON.stringify({
                  commandUsed,
                  signals,
                  timeoutDelays,
                  clearedTimers,
                  unrefCalls,
                  stdoutDestroyCalls,
                  stdoutDataListeners: child.stdout.listenerCount("data"),
                  childErrorListeners: child.listenerCount("error"),
                  childCloseListeners: child.listenerCount("close"),
                  processStartToken: owner.split(/\\r?\\n/)[2],
                  sandboxConfigured: Boolean(output.env.SANDBOX_DERIVED_DATA),
                }));
                """,
                {"TMPDIR": tmpdir},
                timeout=2,
            )

        self.assertEqual(result["commandUsed"], "/bin/ps")
        self.assertEqual(result["signals"], ["SIGTERM", "SIGKILL"])
        self.assertEqual(result["timeoutDelays"], [5_000, 250])
        self.assertEqual(result["clearedTimers"], [1, 2])
        self.assertEqual(result["unrefCalls"], 1)
        self.assertEqual(result["stdoutDestroyCalls"], 1)
        self.assertEqual(result["stdoutDataListeners"], 0)
        self.assertEqual(result["childErrorListeners"], 0)
        self.assertEqual(result["childCloseListeners"], 0)
        self.assertEqual(result["processStartToken"], "")
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

    def test_subagent_sandbox_is_reused_after_idle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-reuse"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-1", parentID: "main-1" } },
                  },
                });
                const first = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-1" },
                  first,
                );
                const firstSandbox = path.dirname(first.env.SANDBOX_DERIVED_DATA);

                await hooks.event({
                  event: {
                    type: "session.idle",
                    properties: { sessionID: "child-1" },
                  },
                });

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-2", parentID: "main-1" } },
                  },
                });
                const second = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-2" },
                  second,
                );
                const secondSandbox = path.dirname(second.env.SANDBOX_DERIVED_DATA);

                const root = path.dirname(firstSandbox);
                const entries = fs
                  .readdirSync(root)
                  .filter((name) => !name.startsWith("."));

                console.log(JSON.stringify({
                  firstSandbox,
                  secondSandbox,
                  entries,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["firstSandbox"], result["secondSandbox"])
        self.assertEqual(len(result["entries"]), 1)

    def test_parallel_subagents_get_distinct_sandboxes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-parallel"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const sandboxes = [];
                for (const sessionID of ["child-1", "child-2"]) {
                  await hooks.event({
                    event: {
                      type: "session.updated",
                      properties: { info: { id: sessionID, parentID: "main-1" } },
                    },
                  });
                  const output = { env: {} };
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID },
                    output,
                  );
                  sandboxes.push(path.dirname(output.env.SANDBOX_DERIVED_DATA));
                }

                console.log(JSON.stringify({ sandboxes }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertNotEqual(result["sandboxes"][0], result["sandboxes"][1])

    def test_main_session_idle_does_not_release_its_sandbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-main-idle"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "main-1" } },
                  },
                });
                const main = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "main-1" },
                  main,
                );
                const mainSandbox = path.dirname(main.env.SANDBOX_DERIVED_DATA);

                await hooks.event({
                  event: {
                    type: "session.idle",
                    properties: { sessionID: "main-1" },
                  },
                });

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-1", parentID: "main-1" } },
                  },
                });
                const child = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-1" },
                  child,
                );
                const childSandbox = path.dirname(child.env.SANDBOX_DERIVED_DATA);

                console.log(JSON.stringify({ mainSandbox, childSandbox }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertNotEqual(result["mainSandbox"], result["childSandbox"])

    def test_returning_subagent_prefers_its_previous_sandbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-prefer"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const leases = {};
                for (const sessionID of ["child-1", "child-2"]) {
                  await hooks.event({
                    event: {
                      type: "session.updated",
                      properties: { info: { id: sessionID, parentID: "main-1" } },
                    },
                  });
                  const output = { env: {} };
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID },
                    output,
                  );
                  leases[sessionID] = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                }

                // Release child-2 first, then child-1, so child-1's sandbox
                // sits on top of the LIFO stack when child-2 returns.
                for (const sessionID of ["child-2", "child-1"]) {
                  await hooks.event({
                    event: {
                      type: "session.idle",
                      properties: { sessionID },
                    },
                  });
                }

                const returning = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-2" },
                  returning,
                );
                const returningSandbox = path.dirname(
                  returning.env.SANDBOX_DERIVED_DATA,
                );

                console.log(JSON.stringify({
                  previous: leases["child-2"],
                  returningSandbox,
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertEqual(result["previous"], result["returningSandbox"])

    def test_invalid_pool_entries_are_discarded_on_lease(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-discard"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-1", parentID: "main-1" } },
                  },
                });
                const first = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-1" },
                  first,
                );
                const firstSandbox = path.dirname(first.env.SANDBOX_DERIVED_DATA);

                await hooks.event({
                  event: {
                    type: "session.idle",
                    properties: { sessionID: "child-1" },
                  },
                });

                // Replace the pooled directory behind the pool's back: same
                // path, new inode. Identity revalidation must reject it and
                // the next lease must fall through to a fresh directory.
                fs.rmSync(firstSandbox, { recursive: true, force: true });
                fs.mkdirSync(firstSandbox, { mode: 0o700 });

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-2", parentID: "main-1" } },
                  },
                });
                const second = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-2" },
                  second,
                );
                const secondSandbox = path.dirname(second.env.SANDBOX_DERIVED_DATA);

                console.log(JSON.stringify({ firstSandbox, secondSandbox }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertNotEqual(result["firstSandbox"], result["secondSandbox"])

    def test_main_session_deletion_drains_the_free_pool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-drain"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                const leases = {};
                for (const sessionID of ["child-1", "child-2"]) {
                  await hooks.event({
                    event: {
                      type: "session.updated",
                      properties: { info: { id: sessionID, parentID: "main-1" } },
                    },
                  });
                  const output = { env: {} };
                  await hooks["shell.env"](
                    { cwd: process.cwd(), sessionID },
                    output,
                  );
                  leases[sessionID] = path.dirname(output.env.SANDBOX_DERIVED_DATA);
                }

                // child-1 finishes (its sandbox is pooled); child-2 stays live.
                await hooks.event({
                  event: {
                    type: "session.idle",
                    properties: { sessionID: "child-1" },
                  },
                });

                await hooks.event({
                  event: {
                    type: "session.deleted",
                    properties: { info: { id: "main-1" } },
                  },
                });

                console.log(JSON.stringify({
                  pooledExists: fs.existsSync(leases["child-1"]),
                  leasedExists: fs.existsSync(leases["child-2"]),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertFalse(result["pooledExists"])
        self.assertTrue(result["leasedExists"])

    def test_deleting_a_finished_subagent_keeps_the_reused_sandbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-no-double-free"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-1", parentID: "main-1" } },
                  },
                });
                const first = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-1" },
                  first,
                );

                await hooks.event({
                  event: {
                    type: "session.idle",
                    properties: { sessionID: "child-1" },
                  },
                });

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-2", parentID: "main-1" } },
                  },
                });
                const second = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-2" },
                  second,
                );
                const reused = path.dirname(second.env.SANDBOX_DERIVED_DATA);

                // Deleting the finished child must not touch the sandbox that
                // child-2 is now leasing.
                await hooks.event({
                  event: {
                    type: "session.deleted",
                    properties: { info: { id: "child-1", parentID: "main-1" } },
                  },
                });

                console.log(JSON.stringify({
                  reusedExists: fs.existsSync(reused),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertTrue(result["reusedExists"])

    def test_plugin_dispose_removes_pooled_sandboxes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_node(
                """
                import fs from "node:fs";
                import path from "node:path";

                const plugin = (await import(
                  "./XcodeBuildTools/opencode-plugin.js?test=pool-dispose"
                )).default;
                const hooks = await plugin.server({});
                await hooks.config({});

                await hooks.event({
                  event: {
                    type: "session.updated",
                    properties: { info: { id: "child-1", parentID: "main-1" } },
                  },
                });
                const output = { env: {} };
                await hooks["shell.env"](
                  { cwd: process.cwd(), sessionID: "child-1" },
                  output,
                );
                const sandbox = path.dirname(output.env.SANDBOX_DERIVED_DATA);

                // Release to the pool, then dispose: the pooled sandbox must
                // be cleaned up even though no session owns it anymore.
                await hooks.event({
                  event: {
                    type: "session.idle",
                    properties: { sessionID: "child-1" },
                  },
                });
                await hooks.dispose();

                for (let attempt = 0; attempt < 100; attempt += 1) {
                  if (!fs.existsSync(sandbox)) break;
                  await new Promise((resolve) => setTimeout(resolve, 5));
                }

                console.log(JSON.stringify({
                  sandboxExists: fs.existsSync(sandbox),
                }));
                """,
                {"TMPDIR": tmpdir},
            )

        self.assertFalse(result["sandboxExists"])


if __name__ == "__main__":
    unittest.main()
