"""整理发行目录、完整许可、已校验的 Qt 对应源码和压缩附件。"""
import argparse
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import shutil
import sys
import subprocess
import tarfile
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gaussian_lab import __version__
TAG = "v" + __version__
RELEASE = ROOT / "releases" / TAG
SOURCE_URLS = [
    "https://download.qt.io/archive/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz",
    "https://download.qt.io/archive/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz",
    "https://download.qt.io/archive/qt/6.12/6.12.0/submodules/qtimageformats-everywhere-src-6.12.0.tar.xz",
    "https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz",
]


def download_sources(cache=None):
    """使用固定摘要复核 Qt 源码，可复用旧缓存；缺失时从原始官方 URL 下载。"""
    folder = RELEASE / "qt-sources"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "packaging/qt-source-manifest.json").read_text(encoding="utf-8"))
    for row in manifest:
        if row["url"] not in SOURCE_URLS or row["name"] != row["url"].rsplit("/", 1)[-1]:
            raise ValueError("Qt 源码清单与固定官方来源不匹配")
        expected = row["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Qt 源码摘要格式无效")
        target = folder / row["name"]
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        cached = Path(cache) / row["name"] if cache else None
        if cached and cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == expected:
            shutil.copy2(cached, target)
        else:
            with requests.get(row["url"], stream=True, timeout=(15, 90)) as payload:
                payload.raise_for_status()
                with target.open("wb") as output:
                    for chunk in payload.iter_content(1024 * 1024):
                        output.write(chunk)
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise RuntimeError("源码校验值不匹配：" + row["name"])
        print("源码校验通过：" + row["name"], flush=True)
    (folder / "SOURCE-MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder


def notices(bundle, source_folder):
    target = bundle / "THIRD_PARTY_LICENSES"
    target.mkdir(exist_ok=True)
    index = []
    for dist in distributions():
        name = dist.metadata.get("Name", "unknown")
        # 保守收集当前环境的许可；清单可能包含只在构建时使用的包。
        count = 0
        for file in dist.files or []:
            parts = str(file).lower().replace("\\", "/")
            basename = Path(str(file)).name.lower()
            if any(t in basename for t in ("license", "copying", "notice", "copyright")) or "/licenses/" in parts:
                path = Path(dist.locate_file(file))
                if not path.is_file() or path.stat().st_size > 4*1024**2:
                    continue
                rel = Path(name) / Path(str(file).replace("../", "")).name
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and dest.read_bytes() != path.read_bytes():
                    dest = dest.with_name(str(count) + "-" + dest.name)
                shutil.copy2(path, dest)
                count += 1
        index.append({"name": name, "version": dist.version, "license_files": count})
    # 部分 Qt 安装包只附商业许可选项说明，因此同时从已校验的对应源码归档中
    # 提取上游原始许可证文本，完整保留其内容。
    for archive in source_folder.glob("*.tar.xz"):
        with tarfile.open(archive, "r:xz") as tar:
            for member in tar.getmembers():
                if not member.isfile() or member.size > 2*1024**2:
                    continue
                parts = member.name.split("/")
                base = parts[-1].lower()
                if "/LICENSES/" not in member.name and not base.startswith(("license", "copying")):
                    continue
                dest = target / "Qt-upstream" / archive.name / Path(*parts[1:])
                dest.parent.mkdir(parents=True, exist_ok=True)
                data = tar.extractfile(member)
                if data:
                    dest.write_bytes(data.read())
    (target / "INDEX.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('构建解释器目录中未找到 CPython 许可证')
    (target / 'CPython').mkdir(exist_ok=True)
    shutil.copy2(python_license, target / 'CPython/LICENSE.txt')
    shutil.copy2(source_folder / "SOURCE-MANIFEST.json", target)
    assert list(target.rglob("LGPL-3.0-only.txt")), "缺少完整的 LGPL-3.0 许可证文本"



def application_source_names(root):
    """仓库按 Git 清单收集源码；源码 ZIP 解压后可按随附用途清单重建。"""
    root = Path(root)
    try:
        names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root,
                                        stderr=subprocess.DEVNULL).decode("utf-8").split("\0")
        if "gaussian_lab/__init__.py" not in names:
            raise ValueError("当前目录没有可用的 Git 源码清单")
    except (OSError, subprocess.SubprocessError, ValueError):
        rows = json.loads((root / "docs/file-inventory.json").read_text(encoding="utf-8"))
        names = [row["path"] for row in rows]
    return sorted(set(filter(None, names)))


def archive_application_source():
    """保存可重建源码，不收集本机环境、IDE、缓存和生成物。"""
    source_zip = RELEASE / f"GaussianLab-{TAG}-Application-Source.zip"
    with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zip_out:
        for name in application_source_names(ROOT):
            if name.startswith((".idea/", "outputs/", "releases/", ".venv/", "build/", "dist/")):
                continue
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT.resolve()):
                raise ValueError("源码清单包含项目之外的路径")
            if path.is_file():
                zip_out.write(path, Path(f"GaussianLab-{TAG}-Source") / name)
    return source_zip


def refresh_source():
    """仅刷新源码附件和外置摘要，不修改已经验证的运行包。"""
    archive_application_source()
    assets = [RELEASE / f"GaussianLab-{TAG}-{suffix}.zip" for suffix in
              ("Windows-x64", "Qt-Corresponding-Source", "Application-Source")]
    (RELEASE / "SHA256SUMS.txt").write_text("\n".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name for path in sorted(assets)) + "\n", encoding="utf-8")

def stage(cache=None):
    RELEASE.mkdir(parents=True, exist_ok=True)
    sources = download_sources(cache)
    bundle = RELEASE / f"GaussianLab-{TAG}-Windows-x64"
    if bundle.exists():
        # 只允许替换这个明确的生成目录，避免操作其他路径。
        if bundle.resolve().parent != RELEASE.resolve() or RELEASE.resolve().parent != (ROOT / 'releases').resolve():
            raise RuntimeError("发行暂存路径不符合预期")
        shutil.rmtree(bundle)
    shutil.copytree(ROOT / "dist" / TAG / "GaussianLab", bundle, dirs_exist_ok=True)
    if __version__.startswith("3.") and not (bundle / "_internal/cuda_runtime/RUNTIME-MANIFEST.json").is_file():
        raise RuntimeError("V3 运行包缺少随包 CUDA 组件，拒绝把 CPU 包标为完整发行")
    # 拒绝混入可能覆盖 Windows 系统 ICU 的外部环境动态库。
    forbidden = [p for p in bundle.rglob('*.dll') if p.name.lower().startswith(('icudt', 'icuuc', 'icuin'))]
    if forbidden:
        raise RuntimeError('发行目录中存在非预期的外部 ICU 动态库，请按当前配置重新构建')
    notices(bundle, sources)
    if (bundle / "_internal/cuda_runtime").is_dir():
        cuda_licenses = bundle / "THIRD_PARTY_LICENSES" / "CUDA"
        cuda_licenses.mkdir(parents=True, exist_ok=True)
        for info in (bundle / "_internal/cuda_runtime").glob("*.dist-info"):
            for path in info.rglob("*"):
                if path.is_file() and ("license" in str(path).lower() or "notice" in path.name.lower()):
                    dest = cuda_licenses / info.name / path.relative_to(info)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
    guide = (ROOT / f"docs/USER_GUIDE-{TAG}.md").read_text(encoding="utf-8")
    guide = guide.replace("](USER_GUIDE.md)", "](docs/USER_GUIDE.md)").replace("](项目学习手册.html)", "](docs/项目学习手册.html)")
    guide = guide.replace("](项目学习手册.md)", "](docs/项目学习手册.md)").replace("](../README.md)", "](docs/USER_GUIDE.md)")
    (bundle / "使用说明.md").write_text(guide, encoding="utf-8")
    shutil.copy2(ROOT / f"docs/release-notes-{TAG}.md", bundle / "版本说明.md")
    shutil.copy2(ROOT / "README.md", bundle / "README.md")
    shutil.copy2(ROOT / "LICENSE", bundle / "LICENSE")
    shutil.copy2(ROOT / "docs/THIRD-PARTY-NOTICES.md", bundle / "THIRD-PARTY-NOTICES.md")
    shutil.copytree(ROOT / "docs", bundle / "docs", dirs_exist_ok=True)
    examples = bundle / "examples"
    examples.mkdir(exist_ok=True)
    for name in ("focus", "expander", "diffraction"):
        shutil.copy2(ROOT / f"docs/assets/{name}.json", examples)
    (bundle / "版本信息.txt").write_text(f"GaussianLab {__version__}\nWindows 64 位便携目录版本\n"
        "解压整个文件夹，双击 GaussianLab.exe，无需安装 Python。\n随附 CUDA 组件；需要兼容 NVIDIA 驱动，否则自动使用 CPU。\nQt/PySide6 使用 LGPLv3 动态库；详见 THIRD-PARTY-NOTICES.md。\n", encoding="utf-8")
    with zipfile.ZipFile(RELEASE / f"GaussianLab-{TAG}-Windows-x64.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zip_out:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                zip_out.write(path, Path(bundle.name) / path.relative_to(bundle))
    with zipfile.ZipFile(RELEASE / f"GaussianLab-{TAG}-Qt-Corresponding-Source.zip", "w", zipfile.ZIP_STORED) as zip_out:
        for path in sorted(sources.iterdir()):
            zip_out.write(path, path.name)
    source_zip = archive_application_source()
    assets = [RELEASE / f"GaussianLab-{TAG}-Windows-x64.zip",
              RELEASE / f"GaussianLab-{TAG}-Qt-Corresponding-Source.zip", source_zip]
    checksum = "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(assets)) + "\n"
    (RELEASE / "SHA256SUMS.txt").write_text(checksum, encoding="utf-8")
    print(checksum)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="整理当前应用版本的 Windows 便携包与对应源码")
    parser.add_argument("--source-cache", type=Path)
    parser.add_argument("--refresh-source-only", action="store_true")
    args = parser.parse_args()
    if args.refresh_source_only:
        refresh_source()
    else:
        stage(args.source_cache)
