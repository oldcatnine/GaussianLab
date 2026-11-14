"""Stage redistributable folder, full notices, verified Qt sources and ZIP assets."""
import argparse
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "releases" / "v0.1.0"
SOURCE_URLS = [
    "https://download.qt.io/archive/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz",
    "https://download.qt.io/archive/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz",
    "https://download.qt.io/archive/qt/6.12/6.12.0/submodules/qtimageformats-everywhere-src-6.12.0.tar.xz",
    "https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz",
]


def download_sources():
    folder = RELEASE / "qt-sources"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for url in SOURCE_URLS:
        target = folder / url.rsplit("/", 1)[-1]
        response = requests.get(url + ".mirrorlist", timeout=60)
        response.raise_for_status()
        # MirrorBrain publishes the expected SHA-256 near the file metadata.
        matches = re.findall(r'\b[0-9a-f]{64}\b', response.text)
        if not matches:
            raise RuntimeError(f"No published SHA-256 for {target.name}")
        expected = matches[0]
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            with requests.get(url, stream=True, timeout=90) as payload:
                payload.raise_for_status()
                with target.open("wb") as output:
                    for chunk in payload.iter_content(1024*1024):
                        output.write(chunk)
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Source checksum mismatch: {target.name}")
        manifest.append({"name": target.name, "url": url, "sha256": actual})
        print(f"Verified source: {target.name}", flush=True)
    (folder / "SOURCE-MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder


def notices(bundle, source_folder):
    target = bundle / "THIRD_PARTY_LICENSES"
    target.mkdir(exist_ok=True)
    index = []
    for dist in distributions():
        name = dist.metadata.get("Name", "unknown")
        # Include notices of the environment conservatively; some are build-only.
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
    # Qt wheels may contain only the commercial alternative notice. Also extract
    # all upstream license texts from the corresponding verified source archives.
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
        raise RuntimeError('CPython license not found in the build interpreter')
    (target / 'CPython').mkdir(exist_ok=True)
    shutil.copy2(python_license, target / 'CPython/LICENSE.txt')
    shutil.copy2(source_folder / "SOURCE-MANIFEST.json", target)
    assert list(target.rglob("LGPL-3.0-only.txt")), "Missing full LGPL-3.0 text"


def stage():
    RELEASE.mkdir(parents=True, exist_ok=True)
    sources = download_sources()
    bundle = RELEASE / "GaussianLab-v0.1.0-Windows-x64"
    if bundle.exists():
        # Only replace this exact generated release folder, never arbitrary paths.
        if bundle.resolve().parent != RELEASE.resolve() or RELEASE.resolve().parent != (ROOT / 'releases').resolve():
            raise RuntimeError("Unexpected release staging path")
        shutil.rmtree(bundle)
    shutil.copytree(ROOT / "dist/GaussianLab", bundle, dirs_exist_ok=True)
    # Disallow accidental environment libraries that could shadow Windows ICU.
    forbidden = [p for p in bundle.rglob('*.dll') if p.name.lower().startswith(('icudt', 'icuuc', 'icuin'))]
    if forbidden:
        raise RuntimeError('Unexpected third-party ICU library in final bundle; rebuild from current spec')
    notices(bundle, sources)
    shutil.copy2(ROOT / "docs/USER_GUIDE-v0.1.0.md", bundle / "使用说明.md")
    shutil.copy2(ROOT / "docs/release-notes-v0.1.0.md", bundle / "版本说明.md")
    shutil.copy2(ROOT / "docs/THIRD-PARTY-NOTICES.md", bundle / "THIRD-PARTY-NOTICES.md")
    examples = bundle / "examples"
    examples.mkdir(exist_ok=True)
    for name in ("focus", "expander", "diffraction"):
        shutil.copy2(ROOT / f"docs/assets/{name}.json", examples)
    (bundle / "版本信息.txt").write_text("GaussianLab 0.1.0\nWindows x64 portable folder build\n"
        "解压整个文件夹，双击 GaussianLab.exe，无需安装 Python。\nQt/PySide6: LGPLv3 dynamic libraries; see THIRD-PARTY-NOTICES.md.\n", encoding="utf-8")
    with zipfile.ZipFile(RELEASE / "GaussianLab-v0.1.0-Windows-x64.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zip_out:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                zip_out.write(path, Path(bundle.name) / path.relative_to(bundle))
    with zipfile.ZipFile(RELEASE / "GaussianLab-v0.1.0-Qt-Corresponding-Source.zip", "w", zipfile.ZIP_STORED) as zip_out:
        for path in sorted(sources.iterdir()):
            zip_out.write(path, path.name)
    assets = list(RELEASE.glob("*.zip"))
    checksum = "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(assets)) + "\n"
    (RELEASE / "SHA256SUMS.txt").write_text(checksum, encoding="utf-8")
    print(checksum)


if __name__ == "__main__":
    stage()
