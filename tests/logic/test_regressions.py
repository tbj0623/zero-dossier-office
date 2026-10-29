#!/usr/bin/env python3
"""回归测试：锁死盲审发现的三类缺陷，防止后续修改时重新引入。

1. NA-006 E01 不得再用「次」作为距离单位（会被读成 index diff 4 → 另一个唯一解）
2. NA-003 E02 必须写明传送带的格位轴方向（时间轴 ↔ 格位轴的映射）
3. 发布版与盲审版 items 顺序不得等于答案顺序

运行：python tests/logic/test_regressions.py
"""
from __future__ import annotations

import itertools
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))

from verify_cases import check_rule  # noqa: E402

PUBLIC = ROOT / "cases" / "public"
AUTHOR = ROOT / "cases" / "author"
BLIND = ROOT / "work" / "blind-src"
RELEASED = ["NA-001", "NA-002", "NA-003", "NA-004", "NA-005", "NA-006"]


def load(folder: Path, cid: str) -> dict:
    return json.loads((folder / f"{cid}.json").read_text(encoding="utf-8"))


class TestNA006UnitAmbiguity(unittest.TestCase):
    """盲审 BLOCKING: 「相距整整三次」被读成 index diff 4，且同样唯一且不同。"""

    def test_evidence_text_no_longer_uses_次_as_a_distance_unit(self):
        for folder in (AUTHOR, PUBLIC, BLIND):
            body = load(folder, "NA-006")["evidence"][0]["body"]
            for bad in ("相距整整三次", "相差整整三次", "相距三次", "相隔三次"):
                self.assertNotIn(bad, body, f"{folder} 仍在使用「{bad}」这种以「次」为距离单位的措辞")

    def test_evidence_explicitly_states_serial_number_difference(self):
        for folder in (AUTHOR, PUBLIC, BLIND):
            body = load(folder, "NA-006")["evidence"][0]["body"]
            self.assertIn("序号", body, f"{folder} 未明确说明是「曝光序号」之差")
            self.assertIn("n+3", body, f"{folder} 未给出 n / n+3 的等价表述")

    def test_intended_reading_is_unique(self):
        c = load(AUTHOR, "NA-006")
        sols = [p for p in itertools.permutations(c["items"])
                if all(check_rule(p, r) for r in c["constraints"])]
        self.assertEqual(len(sols), 1)

    def test_gap4_reading_would_produce_a_different_solution(self):
        """证明这个歧义真实存在过：把 C01 改成 gap=4 会得到另一个唯一解。"""
        c = load(AUTHOR, "NA-006")
        alt = [dict(r) for r in c["constraints"]]
        for r in alt:
            if r["id"] == "C01":
                r["gap"] = 4
        sols = [p for p in itertools.permutations(c["items"])
                if all(check_rule(p, r) for r in alt)]
        self.assertEqual(len(sols), 1, "gap=4 应当也只有一个解——这正是必须消除歧义的原因")
        self.assertNotEqual(list(sols[0]), c["expected_solution"],
                            "两种读法必须给出不同排列，否则不构成歧义")


class TestNA003AxisMapping(unittest.TestCase):
    """盲审 MINOR: 时间轴（早于）与格位轴（第1-5格）的映射从未写明。"""

    def test_direction_is_stated(self):
        for folder in (AUTHOR, PUBLIC, BLIND):
            body = load(folder, "NA-003")["evidence"][1]["body"]
            self.assertIn("向第 5 格", body, f"{folder} 未写明传送带运行方向")
            self.assertIn("越晚", body, f"{folder} 未写明编号与时间的对应关系")

    def test_time_words_are_anchored_to_slots(self):
        c = load(AUTHOR, "NA-003")
        self.assertTrue(
            any("运行" in e["body"] for e in c["evidence"]),
            "至少一条证据必须交代传送带运行方向",
        )


class TestNoItemsOrderLeak(unittest.TestCase):
    """盲审发现：5/6 案件的 items 数组顺序 == 答案顺序。"""

    def test_public_items_order_differs_from_solution(self):
        for cid in RELEASED:
            with self.subTest(case=cid):
                d = load(PUBLIC, cid)
                self.assertNotEqual(d["items"], d["expected_solution"]
                                    if "expected_solution" in d else None,
                                    "public 不应含答案；此断言只在该字段存在时起效")

    def test_public_items_order_differs_from_author_solution(self):
        for cid in RELEASED:
            with self.subTest(case=cid):
                author = load(AUTHOR, cid)
                public = load(PUBLIC, cid)
                self.assertNotEqual(public["items"], author["expected_solution"],
                                    f"{cid} 的 public items 顺序仍是答案顺序，等于直接送答案")

    def test_blind_items_order_differs_from_solution(self):
        for cid in RELEASED:
            with self.subTest(case=cid):
                author = load(AUTHOR, cid)
                blind = load(BLIND, cid)
                self.assertNotEqual(blind["items"], author["expected_solution"],
                                    f"{cid} 的盲审包 items 顺序泄漏了答案")

    def test_items_still_a_valid_permutation(self):
        for cid in RELEASED:
            with self.subTest(case=cid):
                author = load(AUTHOR, cid)
                for folder in (PUBLIC, BLIND):
                    d = load(folder, cid)
                    self.assertEqual(sorted(d["items"]), sorted(author["items"]),
                                     f"{folder}/{cid} 打乱后不再是原集合的排列")


class TestAllEvidenceLoadBearing(unittest.TestCase):
    """盲审的正面结论，也要固化成测试：没有任何装饰性线索。"""

    def test_removing_any_evidence_breaks_uniqueness(self):
        for cid in RELEASED:
            with self.subTest(case=cid):
                c = load(AUTHOR, cid)
                for idx in range(len(c["constraints"])):
                    rest = [r for j, r in enumerate(c["constraints"]) if j != idx]
                    count = sum(1 for p in itertools.permutations(c["items"])
                                if all(check_rule(p, r) for r in rest))
                    self.assertGreater(count, 1,
                                       f"{cid} 去掉第 {idx} 条证据后仍有唯一解 → 该线索是装饰")


if __name__ == "__main__":
    unittest.main(verbosity=2)
