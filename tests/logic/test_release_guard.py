"""Prevent regressions that publish untested site versions."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

class ReleaseGuards(unittest.TestCase):
    def test_pages_only_after_ci(self):
        self.assertIn("workflow_run:", PAGES)
        self.assertIn("workflows: [CI]", PAGES)
        self.assertIn("types: [completed]", PAGES)
        self.assertIn("workflow_run.conclusion == 'success'", PAGES)
        self.assertIn("workflow_run.event == 'push'", PAGES)
        self.assertNotIn("  push:\n", PAGES)
        self.assertNotIn("  workflow_dispatch:\n", PAGES)

    def test_exact_commit_and_latest_main_guard(self):
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha }}", PAGES)
        self.assertIn("BUILD_VERSION: ${{ github.event.workflow_run.head_sha }}", PAGES)
        self.assertGreaterEqual(PAGES.count("git ls-remote origin refs/heads/main"), 2)
        self.assertIn("steps.final-check.outputs.publish == 'true'", PAGES)

    def test_browser_gate_includes_v3_v4(self):
        self.assertIn("python tests/browser/e2e.py", CI)
        self.assertIn("python tests/browser/ux_v3.py", CI)
        self.assertIn("python tests/browser/ux_v4.py", CI)
        self.assertIn("python tests/browser/ux_v5.py", CI)
        self.assertIn("python tests/browser/a11y.py", CI)
        self.assertIn("chromium firefox webkit", CI)

if __name__ == "__main__":
    unittest.main()
