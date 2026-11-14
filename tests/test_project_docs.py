"""Documentation checks for the requirements/research stage, not physics tests."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectDocsTests(unittest.TestCase):
    def test_user_requirements_are_recorded(self):
        text = (ROOT / "docs/requirements.md").read_text(encoding="utf-8")
        for requirement in range(1, 11):
            self.assertIn(f"R{requirement:02d}：", text)
        for term in ("Python", "透镜焦距", "光阑", "距离", "束腰位置", "远场发散角", "聚焦光斑尺寸曲线", "GUI"):
            self.assertIn(term, text)

    def test_readme_local_links_resolve(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\((docs/[^)]+)\)", text)
        self.assertGreaterEqual(len(links), 5)
        for link in links:
            self.assertTrue((ROOT / link).is_file(), link)

    def test_confirmed_scope_and_3d_design_are_recorded(self):
        requirements = (ROOT / "docs/requirements.md").read_text(encoding="utf-8")
        for term in ("多片薄透镜", "单透镜聚焦", "双透镜扩束", "随焦距、光阑变化", "3D"):
            self.assertIn(term, requirements)
        design = (ROOT / "docs/product-design.md").read_text(encoding="utf-8")
        for term in ("横向视觉放大", "强度曲面", "观察屏", "PyVistaQt", "三维电磁仿真", "旧结果"):
            self.assertIn(term, design)
        research = (ROOT / "docs/research.md").read_text(encoding="utf-8")
        self.assertIn("https://github.com/pyvista/pyvistaqt", research)

    def test_development_journal_is_linked_and_traceable(self):
        journal = ROOT / "docs/development-log.md"
        text = journal.read_text(encoding="utf-8")
        for index in range(1, 6):
            self.assertIn(f"### DEV-{index:03d}｜", text)
        for commit in ("ae68e77", "939530a", "18df815", "0c03199"):
            self.assertIn(commit, text)
        for term in ("工具与方法", "验证证据", "问题与处理", "报告素材", "后续记录模板", "尚未实现", "ENOTFOUND"):
            self.assertIn(term, text)
        for link in re.findall(r"\]\(([^)]+\.md)\)", text):
            self.assertTrue((journal.parent / link).is_file(), link)
        for filename in ("agents.md", "README.md"):
            self.assertIn("docs/development-log.md", (ROOT / filename).read_text(encoding="utf-8"))

    def test_consolidated_plan_covers_delivery_and_acceptance(self):
        plan_path = ROOT / "docs/product-plan.md"
        text = plan_path.read_text(encoding="utf-8")
        sections = re.findall(r"^## (\d+)\.", text, re.MULTILINE)
        self.assertEqual(sections, [str(i) for i in range(1, 17)])
        for term in ("多片薄透镜", "单透镜聚焦", "双透镜扩束", "焦距扫描", "光阑扫描", "3D",
                     "横向视觉放大", "观察屏", "r86", "θ86", "收敛", "Git commit", "尚未实现"):
            self.assertIn(term, text)
        for link in re.findall(r"\]\(([^)]+\.md)\)", text):
            self.assertTrue((plan_path.parent / link).is_file(), link)
        self.assertIn("docs/product-plan.md", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_research_has_traceable_primary_sources_and_limits(self):
        text = (ROOT / "docs/research.md").read_text(encoding="utf-8")
        for source in ("DCC-Lab/RayTracing", "opticspy/lightpipes", "jzli559/GaussianBeam"):
            self.assertIn("https://github.com/" + source, text)
        for term in ("MIT", "BSD-3-Clause", "Apache-2.0", "ENOTFOUND", "未实测", "gaussianbeam.py", "propagators.py"):
            self.assertIn(term, text)

    def test_design_keeps_distinct_physical_metrics(self):
        text = (ROOT / "docs/product-design.md").read_text(encoding="utf-8")
        for term in ("讨论稿", "半角", "r86", "θ86", "收敛", "SI", "参数快照"):
            self.assertIn(term, text)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("启动软件.cmd", readme)


if __name__ == "__main__":
    unittest.main()
