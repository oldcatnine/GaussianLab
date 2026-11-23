"""检查需求、研究与文档的一致性；此类断言不验证物理计算精度。"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectDocsTests(unittest.TestCase):
    def test_user_requirements_are_recorded(self):
        text = (ROOT / "docs/requirements.md").read_text(encoding="utf-8")
        for requirement in range(1, 12):
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
        for index in range(1, 25):
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



def test_current_numeric_evidence_matches_implemented_acceptance():
    import json
    report = json.loads((ROOT / "docs/numerical-validation-v2.json").read_text(encoding="utf-8"))
    assert report["algorithm_version"] == "fresnel-focus-v2"
    assert report["short_focus_relative_error"] < .05
    assert len(report["independent"]) == 6
    assert max(row["normalized_intensity_l1"] for row in report["independent"]) < .08
    assert max(row["r86_relative_difference"] for row in report["independent"]) < .05
    assert max(row["transmission_absolute_difference"] for row in report["independent"]) < .04
    assert len(report["aperture_tradeoff"]) == 7
    assert all("refined" in row for row in report["aperture_tradeoff"])
    assert all(row["process_peak_bytes"] >= row["result_array_bytes"] for row in report["memory"])
    assert (ROOT / "docs/numerical-validation-v2.png").is_file()
    text = (ROOT / "docs/validation-v2.md").read_text(encoding="utf-8")
    for term in ("局部细化", "LightPipes", "限制", "内存", "尚未"):
        assert term in text



def test_current_guides_match_export_choices_and_resolve_local_links():
    guide = (ROOT / "docs/USER_GUIDE.md").read_text(encoding="utf-8")
    manual = (ROOT / "docs/项目学习手册.md").read_text(encoding="utf-8")
    source = (ROOT / "gaussian_lab/gui.py").read_text(encoding="utf-8")
    for label in ("当前分析图", "光斑图", "剖面强度曲线", "强度曲面", "包围能量", "轴向传播", "参数扫描"):
        assert label in source and label in guide and label in manual
    for term in ("853e9b3", "300 dpi", "CPU", "快照", "V0.1.0", "白底"):
        assert term in guide, term
    assert "USER_GUIDE.md" in (ROOT / "docs/USER_GUIDE-v0.1.0.md").read_text(encoding="utf-8")
    for filename in ("USER_GUIDE.md", "项目学习手册.md", "product-design.md", "product-plan.md", "requirements.md", "iteration-plan-v3.2.md"):
        path = ROOT / "docs" / filename
        targets = re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8"))
        assert targets, filename
        for target in targets:
            if target.startswith(("http:", "https:", "#", "C:/", "file:")):
                continue
            relative = target.split("#", 1)[0]
            assert (path.parent / relative).is_file(), (filename, target)
    offline = (ROOT / "docs/项目学习手册.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," in offline
    assert 'src="assets/white-theme-desktop.png"' not in offline


def test_v3_current_documents_distinguish_release_preview_and_historical_evidence():
    import json
    from gaussian_lab import __version__
    from gaussian_lab.backend import preview_project
    from gaussian_lab.model import Project
    release = json.loads((ROOT / 'docs/github-release-v3.0.0.json').read_text(encoding='utf-8'))
    assert release['tag'] == 'v3.0.0' and not release['draft']
    for name in ('README.md', 'docs/USER_GUIDE.md', 'docs/acceleration.md', 'docs/项目学习手册.md'):
        text = (ROOT / name).read_text(encoding='utf-8')
        assert 'V3.0.0' in text and '400 ms' in text, name
        assert '稳定包仍走原来的 CPU 路径' not in text, name
        assert '本说明针对源码开发版' not in text, name
    for name in ('README.md', 'docs/USER_GUIDE.md', 'docs/项目学习手册.md'):
        assert 'V' + __version__ in (ROOT / name).read_text(encoding='utf-8'), name
    p = preview_project(Project())
    for name in ('USER_GUIDE.md', 'acceleration.md', '项目学习手册.md'):
        text = (ROOT / 'docs' / name).read_text(encoding='utf-8')
        assert str(p.grid) in text and str(p.samples) in text and '完整计算' in text, name
    guide = (ROOT / 'docs/USER_GUIDE.md').read_text(encoding='utf-8')
    assert '使用 V2.0.0 便携包或当前源码' not in guide
    assert '3.6 MB' in guide and '源码安装' in guide
    log = (ROOT / 'docs/development-log.md').read_text(encoding='utf-8')
    overview = log.split('## 2. 当前阶段总览', 1)[1].split('## 3.', 1)[0]
    assert release['tag'] in overview and 'V0.1 已实现' not in overview



def test_coherent_modes_sampling_documentation_matches_model():
    """核对新增需求、模型限制与源码操作入口同步，避免把旧便携包当新实现。"""
    from gaussian_lab.model import Project
    assert Project().grid == 1024
    for name in ("requirements.md", "USER_GUIDE.md", "项目学习手册.md", "project-review-2026-11-23.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        for term in ("相干", "HG", "LG", "2048", "641", "384 MiB"):
            assert term in text, (name, term)
    review = (ROOT / "docs/project-review-2026-11-23.md").read_text(encoding="utf-8")
    assert "未验证" in review and "便携包" in review
