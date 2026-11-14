"""The sandbox's app, `sandbox/acme/`: its harness passes, fails when a test of either layer
fails, and the lanes script reads it as the Tauri + React app it is.

Every test works on a copy, a git repository of its own, so the app is never changed. The
harness tests need `just`, `cargo` and the app's `node_modules` (`npm ci` in `sandbox/acme/`):
without them they skip, and fail under CI, where a skip would hide them."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACME = ROOT / "sandbox" / "acme"
LANES = ROOT / "plugins" / "app" / "scripts" / "review-lanes.sh"
BUILT = shutil.ignore_patterns("node_modules", "target", "dist", "gen")


class AcmeCopy(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.app = Path(self.folder.name) / "acme"
        shutil.copytree(ACME, self.app, ignore=BUILT)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.app, check=True)

    def tearDown(self):
        self.folder.cleanup()


class TheLanesOfAChange(AcmeCopy):
    def lanes(self, path: str) -> list[str]:
        self.assertTrue((self.app / path).is_file(), f"{path} is not in the app")
        result = subprocess.run(
            ["bash", str(LANES)], cwd=self.app, input=path + "\n", capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.split()

    def test_the_rust_logic_goes_to_backend_and_arch(self):
        self.assertEqual(self.lanes("src-tauri/core/src/fees.rs"), ["backend", "arch"])

    def test_the_screen_goes_to_frontend_and_arch(self):
        self.assertEqual(self.lanes("src/features/fees/FeeScreen.tsx"), ["frontend", "arch"])

    def test_a_command_goes_to_security_too(self):
        self.assertEqual(self.lanes("src-tauri/src/fees/api.rs"), ["backend", "arch", "security"])

    def test_the_justfile_and_the_required_checks_go_to_infra(self):
        self.assertEqual(self.lanes("justfile"), ["infra"])
        self.assertEqual(self.lanes("required-checks.json"), ["infra"])

    def test_the_app_s_settings_are_ones_the_script_takes(self):
        """An unknown key under `review` would exit 2 on every path."""
        self.assertEqual(self.lanes(".claude/daneel.json"), [])


class TheHarness(AcmeCopy):
    def setUp(self):
        missing = [tool for tool in ("just", "cargo", "npx") if shutil.which(tool) is None]
        if not (ACME / "node_modules").is_dir():
            missing.append("sandbox/acme/node_modules (run `npm ci` there)")
        if missing:
            reason = "the harness needs " + ", ".join(missing)
            if os.environ.get("CI"):
                self.fail(reason)
            self.skipTest(reason)
        super().setUp()
        (self.app / "node_modules").symlink_to(ACME / "node_modules")

    def harness(self) -> subprocess.CompletedProcess:
        return subprocess.run(["just", "harness"], cwd=self.app, capture_output=True, text=True)

    def edit(self, path: str, old: str, new: str) -> None:
        file = self.app / path
        text = file.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, f"{old!r} once in {path}")
        file.write_text(text.replace(old, new), encoding="utf-8")

    def test_it_passes_on_the_app(self):
        result = self.harness()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("4 passed", result.stdout + result.stderr)
        self.assertIn("3 passed", result.stdout)

    def test_it_fails_when_a_rust_test_fails(self):
        self.edit("src-tauri/core/src/fees.rs", "(350, 50)", "(351, 50)")
        result = self.harness()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("a_started_kilogram_is_charged_whole ... FAILED", result.stdout)

    def test_it_fails_when_a_screen_test_fails(self):
        self.edit("src/features/fees/presenter.ts", 'padStart(2, "0")', 'padStart(3, "0")')
        result = self.harness()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("4 passed", result.stdout + result.stderr, "the Rust layer still passes")
        self.assertRegex(result.stdout + result.stderr, r"FeeScreen\.test\.tsx.*\n?.*failed|Tests\s+\d+ failed")

    def test_it_never_builds_the_shell(self):
        """The shell needs Tauri's system libraries; the harness runs without them, so it
        neither resolves nor compiles the shell's package."""
        shell_lock = self.app / "src-tauri" / "Cargo.lock"
        shell_lock.unlink(missing_ok=True)  # there when someone checked the shell by hand
        self.assertEqual(self.harness().returncode, 0)
        self.assertFalse(shell_lock.exists(), "the shell was resolved")
        self.assertFalse((self.app / "src-tauri" / "target").exists(), "the shell was compiled")
        locked = (self.app / "src-tauri" / "core" / "Cargo.lock").read_text(encoding="utf-8")
        self.assertEqual(locked.count("[[package]]"), 1, "the logic crate depends on nothing")


if __name__ == "__main__":
    unittest.main()
