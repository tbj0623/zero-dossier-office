#!/usr/bin/env python3
"""第零证物局 · Python 测试（标准库 unittest，零依赖）。

运行：python -m unittest discover -s tests/logic -p 'test_*.py'
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))

from verify_cases import (  # noqa: E402
    CaseError,
    check_rule,
    load_author_cases,
    solutions,
    validate,
)

PUBLIC = ROOT / "cases" / "public"
BLIND = ROOT / "work" / "blind-src"
RELEASED = ["NA-001", "NA-002", "NA-003", "NA-004", "NA-005", "NA-006"]


def load_public(cid: str) -> dict:
    return json.loads((PUBLIC / f"{cid}.json").read_text(encoding="utf-8"))


class TestOperatorSemantics(unittest.TestCase):
    """运算符语义是解题公平性的地基，逐条钉死。"""

    def test_at(self):
        self.assertTrue(check_rule(("a", "b", "c"), {"op": "at", "a": "b", "slot": 1}))
        self.assertFalse(check_rule(("a", "b", "c"), {"op": "at", "a": "b", "slot": 0}))

    def test_not_at(self):
        self.assertTrue(check_rule(("a", "b", "c"), {"op": "not_at", "a": "b", "slot": 0}))
        self.assertFalse(check_rule(("a", "b", "c"), {"op": "not_at", "a": "b", "slot": 1}))

    def test_before_after(self):
        order = ("a", "b", "c")
        self.assertTrue(check_rule(order, {"op": "before", "a": "a", "b": "c"}))
        self.assertFalse(check_rule(order, {"op": "before", "a": "c", "b": "a"}))
        self.assertTrue(check_rule(order, {"op": "after", "a": "c", "b": "a"}))

    def test_immediately_before_requires_adjacency(self):
        near = ("a", "b", "c")
        apart = ("a", "c", "b")
        rule = {"op": "immediately_before", "a": "a", "b": "b"}
        self.assertTrue(check_rule(near, rule))
        self.assertFalse(check_rule(apart, rule))

    def test_adjacent_is_symmetric(self):
        order = ("a", "b", "c", "d")
        self.assertTrue(check_rule(order, {"op": "adjacent", "a": "b", "b": "a"}))
        self.assertTrue(check_rule(order, {"op": "adjacent", "a": "a", "b": "b"}))
        self.assertFalse(check_rule(order, {"op": "adjacent", "a": "a", "b": "c"}))

    def test_distance_is_index_difference_not_gap_count(self):
        order = ("a", "b", "c", "d", "e")
        self.assertTrue(check_rule(order, {"op": "distance", "a": "a", "b": "d", "gap": 3}))
        self.assertFalse(check_rule(order, {"op": "distance", "a": "a", "b": "d", "gap": 2}))

    def test_between_is_strict_and_not_centered(self):
        order = ("a", "b", "c", "d")
        self.assertTrue(check_rule(order, {"op": "between", "a": "b", "b": "a", "c": "d"}))
        self.assertFalse(check_rule(order, {"op": "between", "a": "a", "b": "b", "c": "d"}))

    def test_between_endpoint_order_irrelevant(self):
        order = ("x", "y", "z")
        self.assertTrue(check_rule(order, {"op": "between", "a": "y", "b": "z", "c": "x"}))

    def test_unknown_op_rejected(self):
        with self.assertRaises(CaseError):
            check_rule(("a", "b"), {"op": "xor", "a": "a", "b": "b"})

    def test_bad_gap_rejected(self):
        with self.assertRaises(CaseError):
            check_rule(("a", "b"), {"op": "distance", "a": "a", "b": "b", "gap": 5})
        with self.assertRaises(CaseError):
            check_rule(("a", "b"), {"op": "distance", "a": "a", "b": "b", "gap": 0})

    def test_bad_slot_rejected(self):
        with self.assertRaises(CaseError):
            check_rule(("a", "b"), {"op": "at", "a": "a", "slot": 9})

    def test_unknown_item_rejected(self):
        with self.assertRaises(CaseError):
            check_rule(("a", "b"), {"op": "at", "a": "zz", "slot": 0})


class TestAuthorCases(unittest.TestCase):
    """六个作者版案件必须通过全部形式化校验。"""

    @classmethod
    def setUpClass(cls):
        cls.cases = load_author_cases()
        cls.by_id = {c["id"]: c for c in cls.cases}

    def test_six_cases_present(self):
        self.assertEqual(sorted(self.by_id), RELEASED)

    def test_every_case_validates(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                verdict = validate(case)
                self.assertEqual(verdict["solutions"], 1)
                self.assertEqual(verdict["solution"], case["expected_solution"])

    def test_every_clue_is_essential(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                verdict = validate(case)
                for n in verdict["necessity"]:
                    self.assertTrue(n["essential"], f"{case['id']}/{n['id']} 冗余")

    def test_no_hidden_constraint(self):
        """每条正式约束都必须至少被一条玩家可读证据承载。"""
        for case in self.cases:
            with self.subTest(case=case["id"]):
                referenced = {cid for ev in case["evidence"] for cid in ev["constraint_ids"]}
                formal = {c["id"] for c in case["constraints"]}
                self.assertEqual(referenced, formal)

    def test_three_staged_hints(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(3 <= len(case["hints"]) <= 4)
                self.assertEqual(len(set(case["hints"])), len(case["hints"]))

    def test_rejecting_a_clue_breaks_uniqueness(self):
        """删除任一约束后必须出现多解——证明没有一条线索是装饰。"""
        for case in self.cases:
            with self.subTest(case=case["id"]):
                clues = case["constraints"]
                for idx in range(len(clues)):
                    rest = clues[:idx] + clues[idx + 1:]
                    self.assertGreater(len(solutions(case, rest)), 1)


class TestRejection(unittest.TestCase):
    """校验器必须真的会拒绝坏数据，而不是只对好数据点头。"""

    @classmethod
    def setUpClass(cls):
        cls.base = load_author_cases()[0]

    def _mutate(self, fn) -> dict:
        c = copy.deepcopy(self.base)
        fn(c)
        return c

    def test_rejects_duplicate_items(self):
        c = self._mutate(lambda x: x["items"].__setitem__(1, x["items"][0]))
        with self.assertRaises(CaseError):
            validate(c)

    def test_rejects_wrong_expected_solution(self):
        c = self._mutate(lambda x: x["expected_solution"].reverse())
        with self.assertRaises(CaseError):
            validate(c)

    def test_rejects_missing_evidence_mapping(self):
        c = self._mutate(lambda x: x["evidence"].pop())
        with self.assertRaises(CaseError):
            validate(c)

    def test_rejects_unknown_constraint_ref(self):
        def bad(x):
            x["evidence"][0]["constraint_ids"] = ["C99"]
        with self.assertRaises(CaseError):
            validate(self._mutate(bad))

    def test_rejects_non_unique_case(self):
        def drop_rule(x):
            x["evidence"].pop()
            x["constraints"].pop()
        c = self._mutate(drop_rule)
        # 去掉一条约束并同步删证据后，应当要么非唯一，要么证据映射不完整
        with self.assertRaises(CaseError):
            validate(c)

    def test_rejects_unknown_operator(self):
        def bad(x):
            x["constraints"][0]["op"] = "xor"
        with self.assertRaises(CaseError):
            validate(self._mutate(bad))

    def test_rejects_too_few_hints(self):
        def bad(x):
            x["hints"] = ["只有一条"]
        with self.assertRaises(CaseError):
            validate(self._mutate(bad))


class TestPublishedDataHygiene(unittest.TestCase):
    """发布层与盲审层不得泄漏作者答案。"""

    def test_public_matches_author_constraints(self):
        for cid in RELEASED:
            with self.subTest(case=cid):
                pub = load_public(cid)
                author = json.loads((ROOT / "cases" / "author" / f"{cid}.json").read_text(encoding="utf-8"))
                self.assertEqual(pub["constraints"], author["constraints"])
                # items 的「顺序」被故意打乱以防泄漏答案，只校验集合相同
                self.assertEqual(sorted(pub["items"]), sorted(author["items"]))
                self.assertEqual(pub["slots"], author["slots"])

    def test_public_has_no_answer_field(self):
        for cid in RELEASED:
            with self.subTest(case=cid):
                pub = load_public(cid)
                for field in ("expected_solution", "editorial_note", "status"):
                    self.assertNotIn(field, pub)

    def test_blind_pack_cannot_leak_solution(self):
        leaks = {"constraints", "expected_solution", "hints", "epilogue",
                 "logic_recap", "twist", "resolution", "editorial_note"}
        for cid in RELEASED:
            with self.subTest(case=cid):
                blind = json.loads((BLIND / f"{cid}.json").read_text(encoding="utf-8"))
                self.assertEqual(leaks & set(blind), set(), f"{cid} 盲审包泄漏")

    def test_blind_pack_is_solvable_by_text(self):
        """盲审包必须保留证据正文与物品/格位，否则独立解题无从下手。"""
        for cid in RELEASED:
            with self.subTest(case=cid):
                blind = json.loads((BLIND / f"{cid}.json").read_text(encoding="utf-8"))
                self.assertEqual(len(blind["items"]), len(blind["slots"]))
                self.assertGreaterEqual(len(blind["evidence"]), 3)
                for ev in blind["evidence"]:
                    self.assertGreater(len(ev["body"]), 10)


class TestPublishGate(unittest.TestCase):
    def test_all_six_cases_pass_all_four_gates(self):
        """四项门禁的签核文件都必须存在且为 PASS。"""
        review = ROOT / "review"
        for cid in RELEASED:
            for gate in ("formal", "semantic", "blind", "browser"):
                path = review / f"{cid}-{gate}.json"
                with self.subTest(case=cid, gate=gate):
                    self.assertTrue(path.exists(), f"缺少 {path.name}")
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(data["status"], "PASS", f"{cid}/{gate} 未通过")


if __name__ == "__main__":
    unittest.main(verbosity=2)
