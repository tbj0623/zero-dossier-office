#!/usr/bin/env python3
"""构建隔离回归：旧缓存、旧 dist 与未批准案件不得进入新发行目录。"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "tools" / "build.mjs"
PUBLIC = ROOT / "cases" / "public"
SITE_CASES = ROOT / "site" / "cases"
RELEASED = {f"NA-{number:03d}.json" for number in range(1, 7)}


def run_build(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(BUILD), "--out", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


class BuildIsolationTests(unittest.TestCase):
    def test_stale_site_cache_and_previous_output_are_excluded(self):
        """旧 site/cases 与旧输出中的额外文件都不能进入新构建。"""
        sentinel = SITE_CASES / "__stale-build-test__.json"
        self.assertFalse(sentinel.exists(), f"测试哨兵已存在，拒绝覆盖：{sentinel}")
        SITE_CASES.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix=".build-isolation-", dir=ROOT) as tmp:
            output = Path(tmp) / "out"
            (output / "cases").mkdir(parents=True)
            (output / "stale-from-previous-build.txt").write_text("must disappear", encoding="utf-8")
            (output / "cases" / "NA-999.json").write_text('{"stale":true}', encoding="utf-8")
            sentinel.write_text('{"stale_site_cache":true}', encoding="utf-8")
            try:
                result = run_build(output)
            finally:
                sentinel.unlink(missing_ok=True)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            actual_cases = {path.name for path in (output / "cases").iterdir()}
            self.assertEqual(RELEASED, actual_cases)
            self.assertFalse((output / "stale-from-previous-build.txt").exists())
            self.assertFalse((output / "cases" / "NA-999.json").exists())
            self.assertEqual(["solver.mjs"], sorted(path.name for path in (output / "engine").iterdir()))
            self.assertFalse((output / "tools").exists())

    def test_unapproved_public_case_fails_without_replacing_previous_output(self):
        """public 源目录出现白名单外 JSON 时必须失败，旧输出保持原样。"""
        sentinel = PUBLIC / "__UNAPPROVED_BUILD_TEST__.json"
        self.assertFalse(sentinel.exists(), f"测试哨兵已存在，拒绝覆盖：{sentinel}")

        with tempfile.TemporaryDirectory(prefix=".build-isolation-", dir=ROOT) as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            marker = output / "previous-good-output.txt"
            marker.write_text("keep me", encoding="utf-8")
            sentinel.write_text('{"not_released":true}', encoding="utf-8")
            try:
                result = run_build(output)
            finally:
                sentinel.unlink(missing_ok=True)

            combined = result.stdout + result.stderr
            self.assertNotEqual(0, result.returncode, combined)
            self.assertIn("__UNAPPROVED_BUILD_TEST__.json", combined)
            self.assertEqual("keep me", marker.read_text(encoding="utf-8"))
            self.assertFalse(list(Path(tmp).glob(".out.stage-*")))

    def test_protected_output_paths_are_rejected(self):
        """构建输出不能指向源码目录或仓库根目录。"""
        for unsafe in ("site", "cases", "release"):
            with self.subTest(output=unsafe):
                result = subprocess.run(
                    ["node", str(BUILD), "--out", unsafe],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertIn("拒绝", result.stdout + result.stderr)
        root_output = subprocess.run(
            ["node", str(BUILD), "--out", "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(0, root_output.returncode)
        self.assertIn("输出目录", root_output.stdout + root_output.stderr)
        self.assertTrue((ROOT / "site" / "index.html").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
