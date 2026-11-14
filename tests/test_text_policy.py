"""检查项目中文说明规范，以及学习手册的文件覆盖和离线导航完整性。"""
import ast
import io
import json
from pathlib import Path
import re
import subprocess
import tokenize

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u4e00-\u9fff]")


def test_first_party_python_explanations_are_chinese():
    paths = [ROOT / "app_entry.py", ROOT / "GaussianLab.spec"]
    for folder in ("gaussian_lab", "scripts", "tests"):
        paths.extend((ROOT / folder).glob("*.py"))
    for path in paths:
        source = path.read_text(encoding="utf-8-sig")
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type != tokenize.COMMENT or not re.search(r"[A-Za-z]", token.string):
                continue
            if re.search(r"coding[:=]|mode: python", token.string):
                continue
            assert CJK.search(token.string), (path.name, token.start, token.string)
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node)
                if doc:
                    assert CJK.search(doc), (path.name, doc)


def test_application_docs_use_neutral_language():
    paths = [ROOT / "README.md", ROOT / "agents.md", *(ROOT / "docs").glob("*.md")]
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        assert not re.search(r"给老师|发给老师|老师或演示用户", text), path.name
    rules = (ROOT / "agents.md").read_text(encoding="utf-8")
    assert "中文" in rules and "项目学习手册" in rules


def test_file_inventory_covers_versioned_files():
    rows = json.loads((ROOT / "docs/file-inventory.json").read_text(encoding="utf-8"))
    mapping = {row["path"]: row for row in rows}
    assert len(mapping) == len(rows)
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    assert set(filter(None, names)) <= mapping.keys()
    manual = (ROOT / "docs/项目学习手册.md").read_text(encoding="utf-8")
    for name, row in mapping.items():
        assert CJK.search(row["purpose"]), name
        assert (ROOT / name).is_file() or row["optional_local"], name
        assert f"`{name}`" in manual, name


def test_handbook_has_complete_sections_and_offline_navigation():
    text = (ROOT / "docs/项目学习手册.md").read_text(encoding="utf-8")
    assert re.findall(r"^## (\d+)[.． ]", text, re.M) == [str(i) for i in range(1, 25)]
    for term in ("r86", "Fresnel", "ABCD", "Job", "国际单位制", "限制", "附录"):
        assert term in text, term
    page = (ROOT / "docs/项目学习手册.html").read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>") and 'lang="zh-CN"' in page
    ids = set(re.findall(r'id="(section-\d+)"', page))
    links = set(re.findall(r'href="#(section-\d+)"', page))
    assert len(ids) >= 24 and ids == links
    assert not re.search(r'<(?:script|img|link)[^>]+(?:src|href)="https?://', page)
