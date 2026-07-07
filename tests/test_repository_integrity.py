import json
import py_compile
import re
import shutil
import shlex
import subprocess
import sys
import unittest
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_COMMON_SCRIPT = REPO_ROOT / "scripts" / "sync-plugin-common.py"
OPENCODE_GUARDRAIL_REGISTRATION_CLAIM = re.compile(
    r"\bentry point(?: that)? register(?:s|ed)?\b"
    r"[^.\n]*\b(?:pre-tool-use\s+)?command\s+guardrails\b",
    re.IGNORECASE,
)


def load_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def registered_guardrail_claim_has_rules(info, *current_texts):
    has_claim = any(
        isinstance(text, str)
        and OPENCODE_GUARDRAIL_REGISTRATION_CLAIM.search(text)
        for text in current_texts
    )
    if not has_claim:
        return True

    rules = info.get("pre-tool-use-rules") if info else None
    return isinstance(rules, list) and bool(rules)


def plugin_dirs():
    return sorted(
        path.parent.parent
        for path in REPO_ROOT.glob("*/.claude-plugin/plugin.json")
    )


def load_sync_common_module():
    spec = importlib.util.spec_from_file_location(
        "sync_plugin_common_under_test",
        SYNC_COMMON_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepositoryIntegrityTests(unittest.TestCase):
    def test_marketplace_entries_match_local_plugin_manifests(self):
        marketplace = load_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")

        for entry in marketplace["plugins"]:
            source = entry.get("source")
            if not isinstance(source, str) or not source.startswith("./"):
                continue

            plugin_dir = REPO_ROOT / source.removeprefix("./")
            manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")

            with self.subTest(plugin=entry["name"]):
                self.assertEqual(entry["name"], plugin_dir.name)
                self.assertEqual(manifest["name"], plugin_dir.name)
                self.assertEqual(entry["version"], manifest["version"])
                self.assertIsInstance(entry.get("description"), str)
                self.assertTrue(entry["description"])
                self.assertIsInstance(manifest.get("description"), str)
                self.assertTrue(manifest["description"])
                self.assertIsInstance(entry.get("author"), dict)
                self.assertIsInstance(manifest.get("author"), dict)
                self.assertIn("name", entry["author"])
                self.assertIn("name", manifest["author"])
                self.assertNotIn("displayName", entry)
                self.assertNotIn("claudeCode", manifest)

    def test_plugin_info_tracks_current_manifest_version(self):
        for plugin_dir in plugin_dirs():
            info_path = plugin_dir / "info.json"
            if not info_path.exists():
                continue

            manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
            info = load_json(info_path)
            versions = info.get("versions", [])

            with self.subTest(plugin=plugin_dir.name):
                self.assertTrue(versions, "info.json should include version history")
                self.assertIn(
                    manifest["version"],
                    [entry.get("version") for entry in versions],
                )

    def test_plugin_readmes_track_current_manifest_version(self):
        for plugin_dir in plugin_dirs():
            readme_path = plugin_dir / "README.md"
            if not readme_path.exists():
                continue

            manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
            readme = readme_path.read_text(encoding="utf-8")

            with self.subTest(plugin=plugin_dir.name):
                self.assertIn(f"### {manifest['version']}", readme)

    def test_current_registered_guardrail_claims_have_rules(self):
        for plugin_dir in plugin_dirs():
            info_path = plugin_dir / "info.json"
            readme_path = plugin_dir / "README.md"
            if not info_path.exists() and not readme_path.exists():
                continue

            manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
            current_version = manifest["version"]
            info = None
            current_texts = []
            if info_path.exists():
                info = load_json(info_path)
                current_info = next(
                    (
                        entry
                        for entry in info.get("versions", [])
                        if entry.get("version") == current_version
                    ),
                    None,
                )
                self.assertIsNotNone(
                    current_info,
                    f"{plugin_dir.name} info.json should describe version {current_version}",
                )
                current_texts.append(current_info.get("changes", ""))

            if readme_path.exists():
                readme = readme_path.read_text(encoding="utf-8")
                current_prose, separator, changelog = readme.partition("\n## Changelog\n")
                self.assertTrue(
                    separator,
                    f"{plugin_dir.name} README should include a Changelog section",
                )
                changelog_match = re.search(
                    rf"(?ms)^###\s+{re.escape(current_version)}\s*$\n"
                    r"(?P<section>.*?)(?=^###\s+|\Z)",
                    changelog,
                )
                self.assertIsNotNone(
                    changelog_match,
                    f"{plugin_dir.name} README should describe version {current_version}",
                )
                current_texts.extend(
                    (current_prose, changelog_match.group("section"))
                )

            with self.subTest(plugin=plugin_dir.name):
                self.assertTrue(
                    registered_guardrail_claim_has_rules(
                        info,
                        *current_texts,
                    ),
                    "registered command guardrails require nonempty pre-tool-use-rules",
                )

    def test_only_templated_registration_claim_requires_rules(self):
        original_claim = (
            "The OpenCode entry point registers the scaffolding skill, "
            "session context, and command guardrails."
        )
        original_info_claim = (
            "Added an opencode-plugin.js entry point that registers skills, "
            "session-start context, and pre-tool-use command guardrails."
        )
        current_claim = (
            "The OpenCode entry point registers the scaffolding skill "
            "and session context."
        )

        cases = (
            ("original", {}, original_claim, False),
            ("original-info", {}, original_info_claim, False),
            (
                "configured",
                {"pre-tool-use-rules": [{}]},
                original_claim,
                True,
            ),
            ("current", {}, current_claim, True),
            ("non-template", {}, "Added command guardrails.", True),
        )

        for name, info, claim, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(
                    expected,
                    registered_guardrail_claim_has_rules(
                        info,
                        claim,
                    ),
                )

    def test_known_registered_guardrail_plugins_have_rules(self):
        for plugin_name in ("iOSSimulator", "XcodeBuildTools"):
            plugin_dir = REPO_ROOT / plugin_name
            manifest = load_json(plugin_dir / ".claude-plugin" / "plugin.json")
            info = load_json(plugin_dir / "info.json")
            current_info = next(
                entry
                for entry in info["versions"]
                if entry["version"] == manifest["version"]
            )

            with self.subTest(plugin=plugin_name):
                self.assertRegex(
                    current_info["changes"],
                    OPENCODE_GUARDRAIL_REGISTRATION_CLAIM,
                )
                self.assertTrue(
                    registered_guardrail_claim_has_rules(
                        info,
                        current_info["changes"],
                    )
                )

    def test_info_skill_list_matches_skill_directories(self):
        for plugin_dir in plugin_dirs():
            info_path = plugin_dir / "info.json"
            if not info_path.exists():
                continue

            info = load_json(info_path)
            listed_skills = sorted(info.get("skills", []))
            skills_dir = plugin_dir / "skills"
            discovered_skills = sorted(
                path.name
                for path in skills_dir.iterdir()
                if path.is_dir() and (path / "SKILL.md").exists()
            ) if skills_dir.exists() else []

            with self.subTest(plugin=plugin_dir.name):
                self.assertEqual(listed_skills, discovered_skills)

    def test_skill_frontmatter_names_match_directory_names(self):
        skill_paths = sorted(REPO_ROOT.glob("*/skills/*/SKILL.md"))
        skill_paths.extend(sorted((REPO_ROOT / ".claude" / "skills").glob("*/SKILL.md")))

        for skill_path in skill_paths:
            text = skill_path.read_text(encoding="utf-8")
            match = re.match(r"---\n(?P<frontmatter>.*?)\n---", text, re.DOTALL)

            with self.subTest(skill=str(skill_path.relative_to(REPO_ROOT))):
                self.assertIsNotNone(match, "SKILL.md should start with frontmatter")
                frontmatter = match.group("frontmatter")
                self.assertIn(f"name: {skill_path.parent.name}", frontmatter)
                self.assertRegex(frontmatter, r"(?m)^description: .+")

    def test_swiftui_modernize_skill_preserves_command_metadata(self):
        skill_path = REPO_ROOT / "XcodeBuildTools" / "skills" / "swiftui-modernize" / "SKILL.md"
        frontmatter, _ = self.split_frontmatter(skill_path.read_text(encoding="utf-8"))

        self.assertIn(
            "allowed-tools: mcp__plugin_XcodeBuildTools_sosumi__searchAppleDocumentation, "
            "mcp__plugin_XcodeBuildTools_sosumi__fetchAppleDocumentation",
            frontmatter,
        )
        self.assertIn("argument-hint: <file-path>", frontmatter)

    def test_hook_commands_reference_existing_plugin_files(self):
        hooks_paths = list(REPO_ROOT.glob("*/hooks/hooks.json"))

        for hooks_path in hooks_paths:
            plugin_dir = hooks_path.parent.parent
            hooks_config = load_json(hooks_path)
            commands = self.hook_commands(hooks_config)

            for command in commands:
                if not command.startswith("${CLAUDE_PLUGIN_ROOT}/"):
                    continue

                rendered = command.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_dir))
                executable = Path(shlex.split(rendered)[0])

                with self.subTest(hook=str(hooks_path.relative_to(REPO_ROOT)), command=command):
                    self.assertTrue(executable.exists(), f"{executable} does not exist")

    def test_common_helpers_do_not_include_template_hook_configs(self):
        self.assertFalse(
            (REPO_ROOT / "common" / "hooks.json").exists(),
            "shared common helpers should not include a generic hooks.json template",
        )

        for plugin_dir in plugin_dirs():
            with self.subTest(plugin=plugin_dir.name):
                self.assertFalse(
                    (plugin_dir / "common" / "hooks.json").exists(),
                    "plugin common copies should not include a generated hooks.json template",
                )

    def test_plugin_packages_are_self_contained(self):
        for plugin_dir in plugin_dirs():
            for path in plugin_dir.rglob("*"):
                if path.is_symlink():
                    target = path.resolve()
                    with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                        self.assertTrue(
                            target == plugin_dir.resolve()
                            or target.is_relative_to(plugin_dir.resolve()),
                            "plugin packages must not depend on symlinks that escape the plugin directory",
                        )

    def test_plugin_common_copies_match_shared_sources(self):
        sync_common = load_sync_common_module()
        common_files = sorted(
            path.name
            for path in (REPO_ROOT / "common").iterdir()
            if path.is_file()
        )

        for plugin_dir in plugin_dirs():
            common_dir = plugin_dir / "common"
            if not common_dir.exists():
                continue

            for common_file in common_files:
                plugin_file = common_dir / common_file
                shared_file = REPO_ROOT / "common" / common_file

                with self.subTest(plugin=plugin_dir.name, common_file=common_file):
                    self.assertEqual(
                        sync_common.generated_bytes(shared_file, REPO_ROOT),
                        plugin_file.read_bytes(),
                    )

    def test_common_js_helpers_use_javascript_comment_headers(self):
        sync_common = load_sync_common_module()
        source = REPO_ROOT / "common" / "opencode-plugin.js"

        self.assertTrue(source.exists())
        self.assertTrue(sync_common.generated_bytes(source, REPO_ROOT).startswith(b"// Generated from"))

    def test_opencode_plugin_entrypoints_exist_for_local_plugins(self):
        for plugin_dir in plugin_dirs():
            entrypoint = plugin_dir / "opencode-plugin.js"
            expected = (
                'import { createOpenCodePlugin } from "./common/opencode-plugin.js";\n\n'
                "export default {\n"
                f'  id: "{plugin_dir.name}",\n'
                '  server: createOpenCodePlugin(new URL(".", import.meta.url)),\n'
                "};\n"
            )

            with self.subTest(plugin=plugin_dir.name):
                self.assertTrue(entrypoint.exists())
                self.assertEqual(expected, entrypoint.read_text(encoding="utf-8"))

    def test_node_is_available_for_opencode_runtime_checks(self):
        self.assertIsNotNone(
            shutil.which("node"),
            "Node.js is required for OpenCode runtime, syntax, and export checks",
        )

    def test_opencode_plugin_javascript_syntax(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available")

        script_paths = [REPO_ROOT / "common" / "opencode-plugin.js"]
        script_paths.extend(plugin_dir / "opencode-plugin.js" for plugin_dir in plugin_dirs())

        for script_path in script_paths:
            result = subprocess.run(
                [node, "--input-type=module", "--check"],
                cwd=REPO_ROOT,
                input=script_path.read_text(encoding="utf-8"),
                text=True,
                capture_output=True,
                check=False,
            )

            with self.subTest(script=str(script_path.relative_to(REPO_ROOT))):
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_opencode_plugin_entrypoints_export_server_plugin_objects(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available")

        for plugin_dir in plugin_dirs():
            entrypoint = plugin_dir / "opencode-plugin.js"
            script = (
                f'import plugin from "./{entrypoint.relative_to(REPO_ROOT)}";\n'
                f'if (plugin?.id !== "{plugin_dir.name}") process.exit(1);\n'
                'if (typeof plugin.server !== "function") process.exit(2);\n'
            )
            result = subprocess.run(
                [node, "--input-type=module", "-e", script],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            with self.subTest(plugin=plugin_dir.name):
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_sync_plugin_common_script_reports_clean_checkout(self):
        result = subprocess.run(
            [sys.executable, str(SYNC_COMMON_SCRIPT), "--check"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_plugin_hooks_do_not_require_host_async_support(self):
        hooks_paths = list(REPO_ROOT.glob("*/hooks/hooks.json"))

        for hooks_path in hooks_paths:
            hooks_config = load_json(hooks_path)
            async_paths = self.find_keys(hooks_config, "async")

            with self.subTest(hook=str(hooks_path.relative_to(REPO_ROOT))):
                self.assertEqual(
                    [],
                    async_paths,
                    "Codex skips hooks with async=true; use a command that backgrounds its own work instead",
                )

    def test_backgrounded_sandbox_setup_uses_preserved_hook_owner_pid(self):
        run_background = (REPO_ROOT / "XcodeBuildTools" / "hooks" / "run-background.sh").read_text(encoding="utf-8")
        setup_sandbox = (REPO_ROOT / "XcodeBuildTools" / "hooks" / "setup-sandbox.sh").read_text(encoding="utf-8")

        self.assertIn('hook_owner_pid="${CLAUDE_HOOK_OWNER_PID:-$PPID}"', run_background)
        self.assertIn('hook_owner_pid="$PPID"', run_background)
        self.assertIn('export CLAUDE_HOOK_OWNER_PID="$hook_owner_pid"', run_background)
        self.assertIn('HOOK_OWNER_PID="${CLAUDE_HOOK_OWNER_PID:-$PPID}"', setup_sandbox)
        self.assertIn('find_anchor "$SANDBOX_ROOT" "$HOOK_OWNER_PID"', setup_sandbox)
        self.assertNotIn('find_anchor "$SANDBOX_ROOT" "$PPID"', setup_sandbox)

    def test_mcp_configs_define_servers(self):
        for mcp_path in REPO_ROOT.glob("*/.mcp.json"):
            config = load_json(mcp_path)
            servers = config.get("mcpServers", {})

            with self.subTest(config=str(mcp_path.relative_to(REPO_ROOT))):
                self.assertIsInstance(servers, dict)
                self.assertTrue(servers)

            for name, server in servers.items():
                with self.subTest(config=str(mcp_path.relative_to(REPO_ROOT)), server=name):
                    self.assertTrue(
                        "command" in server or ("type" in server and "url" in server),
                        "MCP server should define either a command or an HTTP type/url",
                    )

    def test_python_scripts_compile(self):
        for script_path in REPO_ROOT.glob("**/*.py"):
            if "__pycache__" in script_path.parts:
                continue

            with self.subTest(script=str(script_path.relative_to(REPO_ROOT))):
                py_compile.compile(str(script_path), doraise=True)

    def test_argparse_scripts_expose_help_without_runtime_dependencies(self):
        script_paths = sorted(REPO_ROOT.glob("*/skills/*/scripts/*.py"))

        for script_path in script_paths:
            text = script_path.read_text(encoding="utf-8")
            if "ArgumentParser" not in text:
                continue

            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            with self.subTest(script=str(script_path.relative_to(REPO_ROOT))):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_shell_scripts_parse_with_bash(self):
        script_paths = sorted(REPO_ROOT.glob("XcodeBuildTools/**/*.sh"))
        script_paths.extend(sorted((REPO_ROOT / "XcodeBuildTools" / "bin").glob("*")))

        for script_path in script_paths:
            if not script_path.is_file():
                continue

            result = subprocess.run(
                ["bash", "-n", str(script_path)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            with self.subTest(script=str(script_path.relative_to(REPO_ROOT))):
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_agent_facing_docs_avoid_known_stale_terms(self):
        checks = {
            "CLAUDE.md": ["SwiftDevelopment", "lastUpdated"],
            ".claude/skills/update-plugin/SKILL.md": ["SwiftDevelopment"],
            "SwiftScaffolding/skills/scaffolding/SKILL.md": [
                "MacOS",
                "XCodeBuildMCP",
                "scaffolginf",
            ],
            "iOSSimulator/README.md": [
                "Claude can",
                "Claude views",
                "Claude identifies",
            ],
            "MarvinOutputStyle/README.md": [
                "Claude will",
                "Claude's communication",
                "Ask Claude Code",
            ],
            "iOSSimulator/skills/ios-simulator/SKILL.md": ["Read tool"],
            "iOSSimulator/skills/ios-simulator/references/script-details.md": ["Read tool"],
            "XcodeBuildTools/session-start.md": ["Claude session", "Claude sessions"],
            "XcodeBuildTools/hooks/setup-sandbox.sh": ["inject-session-id.py"],
            "XcodeBuildTools/bin/xcodebuild": [
                "Claude invocations",
                "Claude Bash",
                "inject-session-id.py",
            ],
            "XcodeBuildTools/bin/swift": [
                "Claude invocations",
                "Claude Bash",
                "inject-session-id.py",
            ],
        }

        for relative_path, stale_terms in checks.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for stale_term in stale_terms:
                with self.subTest(file=relative_path, stale_term=stale_term):
                    self.assertNotIn(stale_term, text)

    def test_scaffolding_skill_uses_portable_question_guidance(self):
        skill_path = REPO_ROOT / "SwiftScaffolding" / "skills" / "scaffolding" / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")

        self.assertNotIn("AskUserQuestion", text)
        self.assertIn("host's native structured question mechanism", text)

    def hook_commands(self, value):
        commands = []
        if isinstance(value, dict):
            command = value.get("command")
            if isinstance(command, str):
                commands.append(command)
            for child in value.values():
                commands.extend(self.hook_commands(child))
        elif isinstance(value, list):
            for child in value:
                commands.extend(self.hook_commands(child))
        return commands

    def find_keys(self, value, key, path="$"):
        paths = []
        if isinstance(value, dict):
            if key in value:
                paths.append(path)
            for child_key, child in value.items():
                paths.extend(self.find_keys(child, key, f"{path}.{child_key}"))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                paths.extend(self.find_keys(child, key, f"{path}[{index}]"))
        return paths

    def split_frontmatter(self, text):
        match = re.match(r"---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)", text, re.DOTALL)
        self.assertIsNotNone(match)
        return match.group("frontmatter"), match.group("body")


if __name__ == "__main__":
    unittest.main()
