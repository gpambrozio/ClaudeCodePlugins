import json
import py_compile
import re
import shlex
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def plugin_dirs():
    return sorted(
        path.parent.parent
        for path in REPO_ROOT.glob("*/.claude-plugin/plugin.json")
    )


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
        for skill_path in REPO_ROOT.glob("*/skills/*/SKILL.md"):
            text = skill_path.read_text(encoding="utf-8")
            match = re.match(r"---\n(?P<frontmatter>.*?)\n---", text, re.DOTALL)

            with self.subTest(skill=str(skill_path.relative_to(REPO_ROOT))):
                self.assertIsNotNone(match, "SKILL.md should start with frontmatter")
                frontmatter = match.group("frontmatter")
                self.assertIn(f"name: {skill_path.parent.name}", frontmatter)
                self.assertRegex(frontmatter, r"(?m)^description: .+")

    def test_hook_commands_reference_existing_plugin_files(self):
        hooks_paths = list(REPO_ROOT.glob("*/hooks/hooks.json"))
        hooks_paths.append(REPO_ROOT / "common" / "hooks.json")

        for hooks_path in hooks_paths:
            plugin_dir = REPO_ROOT if hooks_path.parent.name == "common" else hooks_path.parent.parent
            hooks_config = load_json(hooks_path)
            commands = self.hook_commands(hooks_config)

            for command in commands:
                if not command.startswith("${CLAUDE_PLUGIN_ROOT}/"):
                    continue

                rendered = command.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_dir))
                executable = Path(shlex.split(rendered)[0])

                with self.subTest(hook=str(hooks_path.relative_to(REPO_ROOT)), command=command):
                    self.assertTrue(executable.exists(), f"{executable} does not exist")

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
            ".claude/commands/update-plugin.md": ["SwiftDevelopment"],
            "SwiftScaffolding/commands/scaffolding.md": [
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
            "XcodeBuildTools/bin/xcodebuild": ["Claude invocations", "Claude Bash"],
            "XcodeBuildTools/bin/swift": ["Claude invocations", "Claude Bash"],
        }

        for relative_path, stale_terms in checks.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for stale_term in stale_terms:
                with self.subTest(file=relative_path, stale_term=stale_term):
                    self.assertNotIn(stale_term, text)

    def test_claude_specific_question_tool_stays_in_metadata(self):
        command_path = REPO_ROOT / "SwiftScaffolding" / "commands" / "scaffolding.md"
        text = command_path.read_text(encoding="utf-8")
        frontmatter, body = self.split_frontmatter(text)

        self.assertIn("AskUserQuestion", frontmatter)
        self.assertNotIn("AskUserQuestion", body)
        self.assertIn("host's native structured question mechanism", body)

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

    def split_frontmatter(self, text):
        match = re.match(r"---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)", text, re.DOTALL)
        self.assertIsNotNone(match)
        return match.group("frontmatter"), match.group("body")


if __name__ == "__main__":
    unittest.main()
