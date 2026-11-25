import json
import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "XcodeBuildTools"
HOOKS_DIR = PLUGIN_ROOT / "hooks"
SANDBOX_LIB = HOOKS_DIR / "lib" / "sandbox.sh"
JQ = Path("/usr/bin/jq")

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def git(*args, cwd):
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={**os.environ, **GIT_ENV},
    )


@unittest.skipUnless(JQ.exists(), "sandbox hooks read their payload with /usr/bin/jq")
class SandboxKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.tmpdir = self.root / "tmp"
        self.tmpdir.mkdir()
        self.repo = self.root / "App"
        self.repo.mkdir()
        git("init", "-q", cwd=self.repo)
        git("commit", "-q", "--allow-empty", "-m", "init", cwd=self.repo)
        (self.repo / "Sources").mkdir()
        self.worktree = self.root / "worktrees" / "App"
        git("worktree", "add", "-q", "-b", "feature", str(self.worktree), cwd=self.repo)

    def run_hook(self, name, cwd):
        env_file = self.root / f"env-{time.monotonic_ns()}"
        env_file.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "CLAUDE_ENV_FILE": str(env_file),
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            "TMPDIR": str(self.tmpdir),
        }
        env.pop("CLAUDE_PROJECT_DIR", None)
        result = subprocess.run(
            ["bash", str(HOOKS_DIR / name)],
            input=json.dumps({"session_id": f"s-{time.monotonic_ns()}", "cwd": str(cwd)}),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return env_file.read_text(encoding="utf-8")

    def sandbox_key(self, cwd):
        exports = self.run_hook("write-env.sh", cwd)
        match = re.search(r'SANDBOX_DERIVED_DATA="\$\{TMPDIR:-/tmp\}/claude-sandbox/([^/]+)/build"', exports)
        self.assertIsNotNone(match, exports)
        self.assertIn(f'SANDBOX_PACKAGES="${{TMPDIR:-/tmp}}/claude-sandbox/{match.group(1)}/packages"', exports)
        self.assertIn(f'export PATH="{PLUGIN_ROOT}/bin:$PATH"', exports)
        return match.group(1)

    def test_key_is_shared_by_sessions_and_subdirectories_of_one_worktree(self):
        first = self.sandbox_key(self.repo)
        again = self.sandbox_key(self.repo)
        subdirectory = self.sandbox_key(self.repo / "Sources")

        self.assertRegex(first, r"^wt-App-[0-9a-f]{12}$")
        self.assertEqual(first, again)
        self.assertEqual(first, subdirectory)

    def test_separate_worktrees_get_separate_keys(self):
        main_key = self.sandbox_key(self.repo)
        worktree_key = self.sandbox_key(self.worktree)
        self.assertNotEqual(main_key, worktree_key)

    def test_non_git_folders_are_keyed_by_path(self):
        plain = self.root / "Plain"
        plain.mkdir()
        other = self.root / "Other" / "Plain"
        other.mkdir(parents=True)
        self.assertNotEqual(self.sandbox_key(plain), self.sandbox_key(other))
        self.assertRegex(self.sandbox_key(plain), r"^wt-Plain-[0-9a-f]{12}$")

    def wait_for(self, condition):
        for _ in range(100):
            if condition():
                return True
            time.sleep(0.02)
        return condition()

    def test_setup_creates_sandbox_and_sweeps_removed_worktrees_and_dead_legacy_sessions(self):
        sandbox_root = self.tmpdir / "claude-sandbox"
        worktree_key = self.sandbox_key(self.worktree)
        self.run_hook("setup-sandbox.sh", self.worktree)
        worktree_base = sandbox_root / worktree_key
        self.assertTrue((worktree_base / "build").is_dir())
        self.assertTrue((worktree_base / "packages").is_dir())
        self.assertTrue((worktree_base / ".last-used").is_file())
        self.assertTrue((worktree_base / "worktree").read_text(encoding="utf-8").strip())

        dead = subprocess.Popen(["true"])
        dead.wait()
        legacy_dead = sandbox_root / "legacy-dead"
        (legacy_dead / "build").mkdir(parents=True)
        (legacy_dead / "owner.pid").write_text(f"{dead.pid}\ntrue\n", encoding="utf-8")
        legacy_link = sandbox_root / "legacy-link"
        legacy_link.symlink_to(legacy_dead)
        live_comm = subprocess.run(
            ["ps", "-p", str(os.getpid()), "-o", "comm="],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        legacy_live = sandbox_root / "legacy-live"
        (legacy_live / "build").mkdir(parents=True)
        (legacy_live / "owner.pid").write_text(f"{os.getpid()}\n{live_comm}\n", encoding="utf-8")
        unowned = sandbox_root / "legacy-unowned"
        unowned.mkdir()

        git("worktree", "remove", "--force", str(self.worktree), cwd=self.repo)
        self.run_hook("setup-sandbox.sh", self.repo)

        self.assertFalse(worktree_base.exists())
        self.assertFalse(legacy_dead.exists())
        self.assertFalse(os.path.lexists(legacy_link))
        self.assertTrue(legacy_live.exists())
        self.assertTrue(unowned.exists())
        self.assertTrue((sandbox_root / self.sandbox_key(self.repo) / "build").is_dir())


class SandboxPrepareTests(unittest.TestCase):
    def run_lib(self, script):
        result = subprocess.run(
            ["bash", "-c", f'set -euo pipefail; source "{SANDBOX_LIB}"; {script}'],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_prepare_resets_a_sandbox_unused_for_days(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "claude-sandbox" / "wt-App-0123456789ab"
            (base / "build").mkdir(parents=True)
            (base / "packages").mkdir()
            (base / "build" / "old-output").write_text("x", encoding="utf-8")
            marker = base / ".last-used"
            marker.write_text("", encoding="utf-8")
            four_days_ago = time.time() - 4 * 24 * 3600
            os.utime(marker, (four_days_ago, four_days_ago))

            self.run_lib(f'sandbox_prepare "{base}"')

            self.assertTrue((base / "build").is_dir())
            self.assertFalse((base / "build" / "old-output").exists())
            self.assertGreater(marker.stat().st_mtime, four_days_ago + 3600)

    def test_prepare_keeps_a_recently_used_sandbox(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "claude-sandbox" / "wt-App-0123456789ab"
            (base / "build").mkdir(parents=True)
            (base / "build" / "output").write_text("x", encoding="utf-8")
            (base / ".last-used").write_text("", encoding="utf-8")

            self.run_lib(f'sandbox_prepare "{base}"')

            self.assertTrue((base / "build" / "output").exists())

    def test_base_lookup_only_accepts_the_per_worktree_layout(self):
        self.assertEqual(
            "/t/claude-sandbox/wt-App-0123456789ab",
            self.run_lib(
                'sandbox_base_for /t/claude-sandbox/wt-App-0123456789ab/build '
                '/t/claude-sandbox/wt-App-0123456789ab/packages'
            ),
        )
        # The OpenCode entry point's sandbox manages itself.
        self.assertEqual(
            "",
            self.run_lib(
                'sandbox_base_for /t/opencode-xcodebuildtools-sandbox/s1/build '
                '/t/opencode-xcodebuildtools-sandbox/s1/packages'
            ),
        )
        self.assertEqual("", self.run_lib('sandbox_base_for "" /t/claude-sandbox/wt-x/packages'))


if __name__ == "__main__":
    unittest.main()
