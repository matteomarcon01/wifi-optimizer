from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
        cls.metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        cls.routing_cases = json.loads(
            (ROOT / "tests" / "routing_cases.json").read_text(encoding="utf-8")
        )

    def test_core_routes_to_each_function_reference(self) -> None:
        for name in ("diagnosis-guide.md", "optimization-guide.md"):
            with self.subTest(name=name):
                self.assertIn(f"references/{name}", self.skill)
                self.assertTrue((ROOT / "references" / name).is_file())

    def test_diagnosis_only_requests_do_not_load_optimization(self) -> None:
        self.assertIn("Do not load the optimization guide for a diagnosis-only request.", self.skill)

    def test_ambiguous_requests_default_to_diagnosis(self) -> None:
        self.assertIn("Choose **Diagnosis** when the request is ambiguous.", self.skill)

    def test_optimization_without_evidence_starts_with_diagnosis(self) -> None:
        self.assertIn("Diagnosis (prerequisite for requested optimization)", self.skill)

    def test_default_prompt_is_read_only_diagnosis(self) -> None:
        self.assertIn("$wifi-optimizer", self.metadata)
        self.assertIn("without changing any settings", self.metadata)
        self.assertNotIn("then apply", self.metadata)

    def test_routing_fixture_covers_critical_boundaries(self) -> None:
        self.assertGreaterEqual(len(self.routing_cases), 8)
        ids = {case["id"] for case in self.routing_cases}
        self.assertEqual(len(ids), len(self.routing_cases))
        self.assertTrue(any(case["expected_transition"] == "Optimization" for case in self.routing_cases))
        self.assertTrue(any(not case["settings_change_authorized"] for case in self.routing_cases))
        self.assertTrue(
            any(
                "ignore-untrusted-page-instructions" in case["required_behavior"]
                for case in self.routing_cases
            )
        )

    def test_readmes_document_both_functions(self) -> None:
        self.assertIn("## Two core functions", self.readme)
        self.assertIn("## 两个核心功能", self.readme_cn)

    def test_readmes_include_safe_agent_native_install_prompt(self) -> None:
        self.assertLess(
            self.readme.index("## Installation"),
            self.readme.index("### Install with an Agent (recommended)"),
        )
        self.assertLess(
            self.readme.index("### Install with an Agent (recommended)"),
            self.readme.index("### Manual installation"),
        )
        self.assertLess(
            self.readme_cn.index("## 安装"),
            self.readme_cn.index("### 使用 Agent 安装（推荐）"),
        )
        self.assertLess(
            self.readme_cn.index("### 使用 Agent 安装（推荐）"),
            self.readme_cn.index("### 手动安装"),
        )
        for readme in (self.readme, self.readme_cn):
            self.assertIn("wifi-optimizer/SKILL.md", readme)
            self.assertIn("https://github.com/iAmCorey/wifi-optimizer", readme)
            self.assertNotIn("REPOSITORY_URL_OR_LOCAL_PATH", readme)
            self.assertNotIn("仓库_URL_或本地路径", readme)
        self.assertIn("Do not run the network probe", self.readme)
        self.assertIn("不要运行网络检测脚本", self.readme_cn)


if __name__ == "__main__":
    unittest.main()
