"""Documentation checks for the requirements/research stage, not physics tests."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectDocsTests(unittest.TestCase):
    def test_user_requirements_are_recorded(self):
        text = (ROOT / "docs/requirements.md").read_text(encoding="utf-8")
        for requirement in range(1, 8):
            self.assertIn(f"R{requirement:02d}：", text)
        for term in ("Python", "透镜焦距", "光阑", "距离", "束腰位置", "远场发散角", "聚焦光斑尺寸曲线", "GUI"):
            self.assertIn(term, text)

    def test_readme_local_links_resolve(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\((docs/[^)]+)\)", text)
        self.assertEqual(len(links), 3)
        for link in links:
            self.assertTrue((ROOT / link).is_file(), link)

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
        self.assertIn("尚未实现计算内核和 GUI", readme)


if __name__ == "__main__":
    unittest.main()
