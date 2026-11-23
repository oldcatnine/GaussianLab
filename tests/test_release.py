"""验证发行入口、发布保护及证据记录，单元测试不修改网络状态。"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_release_entry_defers_gui_until_run():
    spec = importlib.util.spec_from_file_location("release_entry", ROOT / "app_entry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)


def test_distribution_includes_guide_and_source_notice():
    for file in ("USER_GUIDE-v0.1.0.md", "release-notes-v0.1.0.md", "THIRD-PARTY-NOTICES.md"):
        assert (ROOT / "docs" / file).is_file()
    text = (ROOT / "docs/THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
    assert "LGPL" in text and "Corresponding-Source.zip" in text
    assert "_internal" in text
    spec = (ROOT / "GaussianLab.spec").read_text(encoding="utf-8")
    assert "'qpdf.dll'" in spec and "'qtvirtualkeyboardplugin.dll'" in spec
    assert "runtime_names" in spec and "pyside_path / name" in spec
    assert "'icuuc.dll'" in spec


def test_publisher_requires_explicit_action_and_has_no_hardcoded_token():
    command = subprocess.run([sys.executable, str(ROOT / "scripts/publish_github.py"), "--help"],
                             capture_output=True, text=True, encoding="utf-8", env={**os.environ,"PYTHONIOENCODING":"utf-8"})
    assert command.returncode == 0
    assert "--visibility" in command.stdout
    text = (ROOT / "scripts/publish_github.py").read_text(encoding="utf-8")
    assert "GIT_TERMINAL_PROMPT" in text
    assert "'ghp_" not in text and '"ghp_' not in text


def test_upload_reader_and_bulk_proxy_configuration(tmp_path):
    spec = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/publish_github.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / 'sample.bin'
    path.write_bytes(b'abc' * 100)
    stream = module.UploadReader(path)
    try:
        assert len(stream) == 300
        assert stream.read(7) == b'abcabca'
        assert stream.tell() == 7
    finally:
        stream.close()
    adapter = module.BulkUploadAdapter()
    assert adapter.poolmanager.connection_pool_kw['blocksize'] == 1024**2
    proxy = adapter.proxy_manager_for('http://localhost:12345')
    assert proxy.connection_pool_kw['blocksize'] == 1024**2


def test_published_private_release_has_verified_frozen_evidence():
    release = json.loads((ROOT / 'docs/github-release-v0.1.0.json').read_text(encoding='utf-8'))
    smoke = json.loads((ROOT / 'docs/github-release-smoke-v0.1.0.json').read_text(encoding='utf-8'))
    assert release['private'] is True and release['draft'] is False
    assert release['tag'] == 'v0.1.0'
    assert len(release['assets']) == 2  # 两个压缩包；校验清单由下载集成验证脚本检查。
    for asset in release['assets']:
        assert asset['github_digest'] == 'sha256:' + asset['sha256']
        assert asset['bytes'] > 0
    assert smoke['frozen'] is True and smoke['status'] == 'passed'
    assert len(smoke['cases']) == 3 and smoke['scan_points'] == 3



def test_current_versions_and_export_backends_are_consistent():
    from gaussian_lab import __version__
    assert __version__ == "4.0.3"
    text = (ROOT / "packaging/windows-version-info.txt").read_text(encoding="utf-8")
    assert "filevers=(4, 0, 3, 0)" in text and "prodvers=(4, 0, 3, 0)" in text
    assert "StringStruct('ProductVersion', '4.0.3')" in text
    spec = (ROOT / "GaussianLab.spec").read_text(encoding="utf-8")
    assert "packaging/windows-version-info.txt" in spec
    assert "matplotlib.backends.backend_svg" in spec and "matplotlib.backends.backend_pdf" in spec
    for name in (f"USER_GUIDE-v{__version__}.md", f"release-notes-v{__version__}.md"):
        assert (ROOT / "docs" / name).is_file()


def test_qt_sources_have_fixed_names_urls_and_hashes():
    rows = json.loads((ROOT / "packaging/qt-source-manifest.json").read_text(encoding="utf-8"))
    assert len(rows) == 4
    for row in rows:
        assert row["name"] == row["url"].rsplit("/", 1)[-1]
        assert row["url"].startswith("https://download.qt.io/")
        assert len(row["sha256"]) == 64 and set(row["sha256"]) <= set("0123456789abcdef")


def test_v31_portable_evidence_matches_extracted_dual_backend():
    artifacts = json.loads((ROOT / "docs/release-artifacts-v3.1.0.json").read_text(encoding="utf-8"))
    smoke = json.loads((ROOT / "docs/release-smoke-v3.1.0.json").read_text(encoding="utf-8"))
    assert artifacts["version"] == "3.1.0"
    assert len(artifacts["assets"]) == 3
    assert all(row["zip_crc"] == "passed" for row in artifacts["assets"])
    for backend in ("cpu", "cuda"):
        report = smoke[backend]
        assert report["version"] == artifacts["version"] and report["frozen"]
        assert report["status"] == artifacts["frozen_smoke"][backend] == "passed"
        assert report["exit_code"] == 0
        assert report["executable_sha256"] == artifacts["executable_sha256"]
        assert len(report["cases"]) == 3
        assert all(case["backend"]["used"] == backend for case in report["cases"])
        assert report["preview"]["backend"]["used"] == backend
    assert smoke["cuda"]["headers_download_verified"]


def test_release_verification_rejects_tampered_archive(tmp_path):
    from scripts.verify_release import TAG, verify_archives
    import hashlib
    import pytest
    names = [f"GaussianLab-{TAG}-{suffix}.zip" for suffix in
             ("Windows-x64", "Qt-Corresponding-Source", "Application-Source")]
    original = b"original bytes"
    for name in names:
        (tmp_path / name).write_bytes(original)
    (tmp_path / "SHA256SUMS.txt").write_text("\n".join(hashlib.sha256(original).hexdigest() + "  " + name for name in names), encoding="utf-8")
    (tmp_path / names[0]).write_bytes(b"changed bytes")
    with pytest.raises(RuntimeError, match="摘要不匹配"):
        verify_archives(tmp_path, tmp_path / "extract")
    assert not (tmp_path / "extract").exists()



def test_application_source_can_be_repacked_without_git_metadata(tmp_path):
    from scripts.prepare_release import application_source_names
    docs = tmp_path / "docs"
    docs.mkdir()
    names = ["gaussian_lab/__init__.py", "GaussianLab.spec", "requirements-build.txt"]
    (docs / "file-inventory.json").write_text(json.dumps([{"path": name} for name in names]), encoding="utf-8")
    assert application_source_names(tmp_path) == sorted(names)


def test_packaged_runtime_cache_validates_files_and_is_reusable(tmp_path):
    from gaussian_lab.backend import bundled_runtime
    import hashlib
    import pytest
    source = tmp_path / "中文运行库"
    source.mkdir()
    payload = source / "library.txt"
    payload.write_bytes(b"known-runtime")
    manifest = {"files": [{"path": "library.txt", "sha256": hashlib.sha256(payload.read_bytes()).hexdigest()}]}
    (source / "RUNTIME-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    cache = tmp_path / "cache"
    target = bundled_runtime(source, cache)
    assert (target / "library.txt").read_bytes() == b"known-runtime"
    assert bundled_runtime(source, cache) == target
    payload.write_bytes(b"corrupt")
    (source / "RUNTIME-MANIFEST.json").write_text(json.dumps(manifest) + " ", encoding="utf-8")
    with pytest.raises(RuntimeError, match="校验失败"):
        bundled_runtime(source, cache)


def test_cuda_headers_hash_failure_never_extracts(tmp_path, monkeypatch):
    from gaussian_lab.backend import ensure_cuda_headers
    import requests
    import pytest
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def raise_for_status(self):
            pass
        def iter_content(self, size):
            yield b"bad"
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Response())
    record = {"url": "https://files.pythonhosted.org/example.whl", "bytes": 3, "sha256": "0"*64}
    (tmp_path / "CUDA-HEADERS.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(RuntimeError, match="摘要不匹配"):
        ensure_cuda_headers(tmp_path)
    assert not (tmp_path / ".headers-ready").exists()
    assert not list(tmp_path.glob("*.whl"))


def test_remote_build_keeps_draft_until_downloaded_binary_is_verified():
    text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "--draft=false" not in text
    assert "gh release upload" in text
    assert "requirements-cuda.txt" in text
    assert "PYTHONUTF8: '1'" in text
    verifier = (ROOT / "scripts/verify_published_release.py").read_text(encoding="utf-8")
    assert "--allow-draft" in verifier and "--smoke" in verifier


def test_download_reuse_requires_matching_size_and_server_digest(tmp_path, monkeypatch):
    import hashlib
    import pytest
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    import verify_published_release as verifier
    path = tmp_path / 'asset.zip'
    path.write_bytes(b'good')
    calls = []
    class Client:
        def get(self, *args, **kwargs):
            calls.append(args)
            raise RuntimeError('需要重新下载')
    asset = {'size': 4, 'digest': 'sha256:' + hashlib.sha256(b'good').hexdigest(), 'url': 'https://example.invalid/asset'}
    verifier.download(Client(), asset, path)
    assert not calls
    path.write_bytes(b'bad!')
    with pytest.raises(RuntimeError, match='重新下载'):
        verifier.download(Client(), asset, path)
    assert len(calls) == 1


def test_v3_published_assets_have_real_cpu_and_cuda_download_evidence():
    release = json.loads((ROOT / 'docs/github-release-v3.0.0.json').read_text(encoding='utf-8'))
    smoke = json.loads((ROOT / 'docs/github-release-smoke-v3.0.0.json').read_text(encoding='utf-8'))
    assert release['private'] and not release['draft'] and release['tag'] == 'v3.0.0'
    assert release['build_run']['conclusion'] == 'success'
    assert len(release['assets']) == 3
    for asset in release['assets']:
        assert asset['github_digest'] == 'sha256:' + asset['sha256']
    assert set(smoke) == {'cpu', 'cuda'}
    for kind, report in smoke.items():
        assert report['version'] == '3.0.0' and report['frozen'] and report['status'] == 'passed'
        assert report['exit_code'] == 0 and len(report['cases']) == 3
        assert all(case['backend']['used'] == kind for case in report['cases'])
        assert report['preview']['quality'] == 'preview' and report['preview']['backend']['used'] == kind
    assert smoke['cuda']['headers_download_verified'] is True
    assert smoke['cuda']['executable_sha256'] == smoke['cpu']['executable_sha256']



def test_cuda_stage_accepts_nvidia_namespace_without_init(tmp_path):
    """新安装的官方轮子使用命名空间包时，仍须完整整理可用运行组件。"""
    from scripts.stage_cuda_runtime import stage, PACKAGES
    source, target = tmp_path / "input", tmp_path / "staged"
    for name in ("cupy", "cupyx", "cupy_backends", "cuda") + PACKAGES:
        folder = source / name
        folder.mkdir(parents=True)
        (folder / "LICENSE.txt").write_text("fixture license", encoding="utf-8")
    for component in ("cuda_runtime", "cuda_nvrtc", "cufft", "nvjitlink"):
        folder = source / "nvidia" / component / "bin"
        folder.mkdir(parents=True)
        (folder / (component + ".dll")).write_bytes(b"fixture")
    stage(source, target)
    report = json.loads((target / "RUNTIME-MANIFEST.json").read_text(encoding="utf-8"))
    assert len([row for row in report["files"] if row["path"].endswith(".dll")]) == 4
    assert not (target / "nvidia/__init__.py").exists()
    assert (target / "CUDA-HEADERS.json").is_file()



def test_v311_portable_covers_cuda_and_coherent_input():
    """冻结证据须来自同一个可执行文件，并实际覆盖高阶与相干输入光。"""
    artifacts = json.loads((ROOT / "docs/release-artifacts-v3.1.1.json").read_text(encoding="utf-8"))
    smoke = json.loads((ROOT / "docs/release-smoke-v3.1.1.json").read_text(encoding="utf-8"))
    assert artifacts["version"] == "3.1.1"
    assert len(artifacts["assets"]) == 3
    assert all(row["zip_crc"] == "passed" for row in artifacts["assets"])
    for backend in ("cpu", "cuda"):
        report = smoke[backend]
        assert report["version"] == "3.1.1" and report["frozen"]
        assert report["status"] == "passed" and report["exit_code"] == 0
        assert report["executable_sha256"] == artifacts["executable_sha256"]
        assert report["coherent_input"]["backend"]["used"] == backend
        assert report["coherent_input"]["modes"] == 2
        assert report["higher_modes"] == ["HG12", "LG12"]
        assert all(case["backend"]["used"] == backend for case in report["cases"])
    assert smoke["cuda"]["headers_verified"]
    assert smoke["cuda"]["headers_source"] in (["local-wheel"], ["official-download"])



def test_cuda_headers_retry_tls_then_verify_before_extract(tmp_path, monkeypatch):
    """首次网络握手中断应自动恢复，仍必须对完整官方轮子做摘要验证。"""
    import hashlib
    import io
    import zipfile
    import requests
    import time
    from gaussian_lab.backend import ensure_cuda_headers
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("nvidia/cuda_runtime/include/cuda_runtime.h", b"verified fixture header")
    payload = buffer.getvalue()
    record = {"url": "https://files.pythonhosted.org/fixture.whl", "bytes": len(payload),
              "sha256": hashlib.sha256(payload).hexdigest()}
    (tmp_path / "CUDA-HEADERS.json").write_text(json.dumps(record), encoding="utf-8")
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_content(self, size): yield payload
    def get(*args, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise requests.exceptions.SSLError("temporary TLS EOF")
        return Response()
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    ensure_cuda_headers(tmp_path)
    assert len(calls) == 3
    assert (tmp_path / ".headers-ready").read_text(encoding="ascii") == record["sha256"]
    assert (tmp_path / "nvidia/cuda_runtime/include/cuda_runtime.h").read_bytes() == b"verified fixture header"
    assert not list(tmp_path.glob("headers-*.whl"))



def test_cuda_headers_local_official_wheel_needs_no_network(tmp_path, monkeypatch):
    """离线使用者提供官方轮子后，按相同摘要检查并完成私有头文件初始化。"""
    import hashlib
    import zipfile
    import requests
    from gaussian_lab.backend import ensure_cuda_headers
    local = tmp_path / "official.whl"
    with zipfile.ZipFile(local, "w") as archive:
        archive.writestr("nvidia/cuda_runtime/include/cuda_runtime.h", b"offline header fixture")
    record = {"url": "https://files.pythonhosted.org/fixture.whl", "bytes": local.stat().st_size,
              "sha256": hashlib.sha256(local.read_bytes()).hexdigest()}
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "CUDA-HEADERS.json").write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setenv("GAUSSIANLAB_CUDA_HEADERS_WHEEL", str(local))
    def forbidden(*args, **kwargs):
        raise AssertionError("本地轮子初始化不应访问网络")
    monkeypatch.setattr(requests, "get", forbidden)
    ensure_cuda_headers(runtime)
    assert (runtime / ".headers-source").read_text(encoding="ascii") == "local-wheel"
    assert (runtime / ".headers-ready").read_text(encoding="ascii") == record["sha256"]
    assert (runtime / "nvidia/cuda_runtime/include/cuda_runtime.h").is_file()
    assert local.is_file()


def test_patch_version_policy_and_explicit_release_tag():
    """小更新规则持久化，发布命令不得隐式使用旧标签，第四代延续 CUDA 验证。"""
    policy = (ROOT / "agents.md").read_text(encoding="utf-8")
    assert "0.0.1" in policy and "4.0.0 → 4.0.1 → 4.0.2" in policy
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "default: v4.0.3" in workflow
    publisher = (ROOT / "scripts/publish_github.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--tag", required=True' in publisher
    for name in ("prepare_release.py", "verify_release.py"):
        assert 'int(__version__.split(".")[0]) >= 3' in (ROOT / "scripts" / name).read_text(encoding="utf-8")


def test_release_verification_preserves_repository_visibility():
    """附件核验适用于现有公开或私有仓库，不强制修改访问权限。"""
    text = (ROOT / "scripts/verify_published_release.py").read_text(encoding="utf-8")
    assert "assert repo['private']" not in text
    assert "assert args.allow_draft or not release['draft']" in text
    assert "'private':repo['private']" in text


def test_v4_published_artifacts_and_frozen_backends_are_verified():
    """第四代真实附件与 CPU/CUDA 冻结证据必须对应同一可执行文件。"""
    release = json.loads((ROOT / "docs/github-release-v4.0.0.json").read_text(encoding="utf-8"))
    smoke = json.loads((ROOT / "docs/github-release-smoke-v4.0.0.json").read_text(encoding="utf-8"))
    assert release["tag"] == "v4.0.0" and release["draft"] is False
    assert release["workflow"]["conclusion"] == "success"
    assert release["windows_version"]["FileVersion"] == "4.0.0"
    assert release["windows_version"]["ProductVersion"] == "4.0.0"
    assert len(release["assets"]) == 3
    for asset in release["assets"]:
        assert asset["bytes"] > 0 and asset["github_digest"] == "sha256:" + asset["sha256"]
    assert set(smoke) == {"cpu", "cuda"}
    for backend, data in smoke.items():
        assert data["version"] == "4.0.0" and data["frozen"]
        assert data["exit_code"] == 0 and data["status"] == "passed"
        assert len(data["cases"]) == 3
        assert all(case["backend"]["used"] == backend for case in data["cases"])
    assert smoke["cpu"]["executable_sha256"] == smoke["cuda"]["executable_sha256"]
    assert smoke["cuda"]["headers_verified"]
