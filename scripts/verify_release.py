"""核验当前发行附件，解压独立副本并用隔离环境执行冻结程序冒烟测试。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gaussian_lab import __version__
TAG = "v" + __version__


def digest(path):
    """分块计算大型发行文件摘要，避免一次性读入整个压缩包。"""
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_archives(release, destination):
    """核对固定附件集合、摘要、CRC 和关键运行文件后解压测试副本。"""
    release, destination = Path(release), Path(destination)
    if destination.exists():
        raise RuntimeError("独立测试目录已经存在，请指定新的测试位置")
    expected_names = {f"GaussianLab-{TAG}-Windows-x64.zip", f"GaussianLab-{TAG}-Qt-Corresponding-Source.zip",
                      f"GaussianLab-{TAG}-Application-Source.zip"}
    entries = [line.split("  ", 1) for line in (release / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines() if line]
    if len(entries) != 3 or {row[1] for row in entries} != expected_names:
        raise RuntimeError("发行附件集合或版本与当前应用不匹配")
    checked = []
    for expected, name in entries:
        path = release / name
        actual = digest(path)
        if actual != expected:
            raise RuntimeError("发行文件摘要不匹配：" + name)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("压缩包完整性检查失败：" + name)
            names = archive.namelist()
            if "Windows-x64" in name:
                prefix = f"GaussianLab-{TAG}-Windows-x64/"
                for required in ("GaussianLab.exe", "_internal/python310.dll", "使用说明.md",
                                 "docs/项目学习手册.html", "docs/USER_GUIDE.md",
                                 "THIRD_PARTY_LICENSES/CPython/LICENSE.txt"):
                    if prefix + required not in names:
                        raise RuntimeError("便携包缺少：" + required)
                if not any(item.endswith("/LGPL-3.0-only.txt") for item in names):
                    raise RuntimeError("便携包缺少原始 LGPL 许可")
                forbidden = {"icuuc.dll", "qtvirtualkeyboardplugin.dll", "qpdf.dll", "Qt6DataVisualization.dll"}
                if any(item.rsplit("/", 1)[-1] in forbidden for item in names):
                    raise RuntimeError("便携包混入已排除的动态库")
                destination.mkdir(parents=True)
                archive.extractall(destination)
        checked.append({"name": name, "bytes": path.stat().st_size, "sha256": actual, "zip_crc": "passed"})
    return checked, destination / f"GaussianLab-{TAG}-Windows-x64"


def run_frozen_smoke(bundle, output):
    """移除开发环境路径，在独立工作目录运行随包 EXE。"""
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ)
    system = Path(environment.get("SystemRoot", "C:/Windows"))
    environment["PATH"] = str(system / "System32") + os.pathsep + str(system)
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    result = subprocess.run([str(bundle / "GaussianLab.exe"), "--smoke-test", str(output)],
                            cwd=output, env=environment, capture_output=True, timeout=240)
    (output / "stdout.log").write_bytes(result.stdout)
    (output / "stderr.log").write_bytes(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"冻结程序冒烟测试退出码为 {result.returncode}，详情见 {output}")
    report = json.loads((output / "smoke-result.json").read_text(encoding="utf-8"))
    if report["version"] != __version__ or not report["frozen"] or report["status"] != "passed":
        raise RuntimeError("冻结程序版本或冒烟报告无效")
    report["exit_code"] = result.returncode
    report["environment"] = "PATH 仅保留 Windows 系统目录，移除开发用 Python/Qt 环境变量"
    report["executable_sha256"] = digest(bundle / "GaussianLab.exe")
    return report


def main():
    parser = argparse.ArgumentParser(description="检查当前便携发行包，可执行解压版冻结验证")
    parser.add_argument("--release-dir", type=Path, default=ROOT / "releases" / TAG)
    parser.add_argument("--extract-to", type=Path)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    destination = args.extract_to or ROOT / "outputs" / f"portable-{TAG}-{time.time_ns()}"
    assets, bundle = verify_archives(args.release_dir, destination)
    report = {"version": __version__, "assets": assets, "bundle_name": bundle.name,
              "executable_sha256": digest(bundle / "GaussianLab.exe")}
    if args.smoke:
        smoke = run_frozen_smoke(bundle, destination / "smoke-output")
        (ROOT / f"docs/release-smoke-{TAG}.json").write_text(json.dumps(smoke, ensure_ascii=False, indent=2), encoding="utf-8")
        report["frozen_smoke"] = "passed"
    (ROOT / f"docs/release-artifacts-{TAG}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"version": __version__, "bundle": str(bundle), "assets": assets,
                      "smoke": report.get("frozen_smoke", "未执行")}, ensure_ascii=True))


if __name__ == "__main__":
    main()
