"""验证区段传播、后端回退、预览采样与缓存边界；设备对照需要可用 CUDA。"""
import numpy as np
import pytest
from gaussian_lab import backend
from gaussian_lab.model import Element, Mode, Project, preset
from gaussian_lab.optics import Propagation, coordinates, initial_field, fresnel, simulate, Cancelled
from gaussian_lab.session import ResultCache


def test_cpu_and_small_auto_do_not_probe_cuda(monkeypatch):
    def forbidden():
        raise AssertionError("CPU 路径不应初始化 CUDA")
    monkeypatch.setattr(backend, "cuda_probe", forbidden)
    assert backend.select_backend("cpu").name == "cpu"
    assert backend.select_backend("auto", 256).name == "cpu"


def test_no_device_falls_back_with_reason(monkeypatch):
    monkeypatch.delenv("GAUSSIANLAB_DISABLE_CUDA", raising=False)
    monkeypatch.setattr(backend, "cuda_probe", lambda: (None, "CPU", "测试：无设备"))
    p = Project(grid=128, samples=17, focus_refinement=0)
    r = simulate(p, backend="cuda")
    assert r.provenance["backend"]["used"] == "cpu"
    assert "无设备" in r.provenance["backend"]["reason"]


def test_cuda_execution_error_retries_cpu_but_never_swallows_cancellation(monkeypatch):
    import gaussian_lab.optics as optics
    engine = backend.Backend(name="cuda", requested="cuda")
    monkeypatch.setattr(optics, "select_backend", lambda *args: engine)
    failure = type("DeviceFailure", (RuntimeError,), {"__module__": "cupy.cuda"})
    original = optics._simulate
    calls = []
    def attempt(p, cancel, progress, current):
        calls.append(current.name)
        if current.name == "cuda":
            raise failure("测试设备故障")
        return original(p, cancel, progress, current)
    monkeypatch.setattr(optics, "_simulate", attempt)
    monkeypatch.setattr(optics, "invalidate_cuda", lambda error: None)
    p = Project(grid=128, samples=17, focus_refinement=0)
    assert simulate(p, backend="cuda").provenance["backend"]["used"] == "cpu"
    assert calls == ["cuda", "cpu"]
    def cancelled(*args):
        raise Cancelled()
    monkeypatch.setattr(optics, "_simulate", cancelled)
    with pytest.raises(Cancelled):
        simulate(p, backend="cuda")


@pytest.mark.parametrize("elements", [[], [Element("aperture", 0, .0007), Element("lens", 0, .12)],
    [Element("lens", .1, -.05), Element("aperture", .1, .0007), Element("lens", .2, .15)]])
def test_segment_cache_matches_independent_original_propagation(elements):
    p = Project(grid=128, samples=17, elements=elements)
    _, r2 = coordinates(p)
    propagation = Propagation(p, r2)
    for z in (0, .05, .1, .15, .2, .4):
        value, last = initial_field(p, r2), 0.
        for e in p.ordered():
            if e.z > z:
                break
            value = fresnel(value, p.wavelength, p.window / p.grid, e.z - last)
            value *= np.exp(-1j * np.pi * r2 / (p.wavelength * e.value)) if e.kind == "lens" else r2 <= (e.value / 2)**2
            last = e.z
        expected = fresnel(value, p.wavelength, p.window / p.grid, z - last)
        np.testing.assert_allclose(propagation.at(z), expected, atol=1e-12, rtol=1e-10)


def test_preview_does_not_modify_input_and_cache_is_bounded():
    p = preset("光阑衍射")
    q = backend.preview_project(p)
    assert (q.grid, q.samples, q.focus_refinement) == (256, 33, 0)
    assert p.grid == 1024 and p.samples == 65 and p.focus_refinement == 2
    assert p.elements == q.elements and p.elements is not q.elements
    q.grid, q.samples = 128, 17
    r = simulate(q)
    cache = ResultCache(budget=r.intensity.nbytes * 2)
    key = cache.key(q, "cpu", True)
    assert key != cache.key(q, "cpu", False)
    assert key != cache.key(q, "cuda", True)
    cache.put(key, r)
    assert cache.get(key) is r
    cache.put("second", r)
    assert cache.get(key) is None
    assert cache.bytes <= cache.budget


def test_repository_state_is_captured_once_while_calculation_time_is_per_result(monkeypatch):
    import gaussian_lab.optics as optics
    calls = []
    def git(*args, **kwargs):
        calls.append(args)
        return b"test-revision" if len(calls) == 1 else b""
    optics.source_revision.cache_clear()
    monkeypatch.setattr(optics.subprocess, "check_output", git)
    try:
        first, second = optics.calculation_provenance(), optics.calculation_provenance()
        assert len(calls) == 2
        assert first["source_state_captured_at"] == second["source_state_captured_at"]
        assert first["source_revision"] == "test-revision" and first["source_dirty"] is False
    finally:
        optics.source_revision.cache_clear()


@pytest.mark.parametrize("name", ["单透镜聚焦", "双透镜扩束", "光阑衍射"])
def test_real_cuda_matches_cpu(name):
    engine = backend.select_backend("cuda")
    if engine.name != "cuda":
        pytest.skip(engine.reason)
    p = preset(name)
    p.grid, p.samples = 256, 17
    cpu, gpu = simulate(p), simulate(p, backend="cuda")
    assert gpu.provenance["backend"]["used"] == "cuda"
    np.testing.assert_allclose(gpu.intensity, cpu.intensity, atol=1e-7, rtol=1e-5)
    np.testing.assert_allclose(gpu.r86, cpu.r86, atol=1e-14, rtol=1e-10)
    np.testing.assert_allclose(gpu.transmission, cpu.transmission, atol=1e-12)
    assert gpu.theta86 == pytest.approx(cpu.theta86, rel=1e-10)
    assert gpu.focus == cpu.focus
    assert gpu.warnings == cpu.warnings


@pytest.mark.parametrize("modes", [[Mode("HG", 2, 1)], [Mode("LG", 1, -2)],
                                  [Mode(), Mode("HG", 1, 0, .7, 90)]])
def test_real_cuda_higher_and_coherent_modes_match_cpu(modes):
    """在真实显卡核验新增递推和复振幅叠加，避免仅验证旧基模分支。"""
    engine = backend.select_backend("cuda")
    if engine.name != "cuda":
        pytest.skip(engine.reason)
    p = Project(grid=256, samples=17, modes=modes, focus_refinement=0, elements=[])
    cpu, gpu = simulate(p), simulate(p, backend="cuda")
    assert gpu.provenance["backend"]["used"] == "cuda"
    np.testing.assert_allclose(gpu.intensity, cpu.intensity, atol=1e-7, rtol=1e-5)
    np.testing.assert_allclose(gpu.r86, cpu.r86, atol=1e-14)
    np.testing.assert_allclose(gpu.transmission, cpu.transmission, atol=1e-12)
    assert gpu.theta86 == pytest.approx(cpu.theta86, rel=1e-10)


def test_cuda_install_entry_and_minimum_pinned_runtime():
    """安装入口必须固定版本、处理中文编码，并与随包组件清单一致。"""
    from pathlib import Path
    from scripts.stage_cuda_runtime import PACKAGES
    root = Path(__file__).resolve().parents[1]
    requirements = (root / "requirements-cuda.txt").read_text(encoding="utf-8")
    rows = [line for line in requirements.splitlines() if line and not line.startswith("#")]
    assert len(rows) == len(PACKAGES) == 6
    assert all("==" in row for row in rows)
    script = (root / "scripts/install_cuda_runtime.ps1").read_text(encoding="utf-8-sig")
    assert "-X utf8 -m pip" in script and "--only-binary=:all:" in script
    assert "select_backend('cuda')" in script
    assert "install_cuda_runtime.ps1" in (root / "安装显卡加速.cmd").read_text(encoding="utf-8")


def test_real_cuda_disk_storage_matches_cpu_ram():
    """真实 GPU 写入磁盘缓存后的高阶模式与 CPU 内存结果一致。"""
    engine = backend.select_backend("cuda")
    if engine.name != "cuda":
        pytest.skip(engine.reason)
    p = Project(grid=128, samples=17, modes=[Mode("LG", 0, 5)])
    cpu = simulate(p)
    p.storage_mode = "disk"
    gpu = simulate(p, backend="cuda")
    assert gpu.provenance["backend"]["used"] == "cuda"
    assert gpu.provenance["memory_estimate"]["storage_mode"] == "disk"
    np.testing.assert_allclose(gpu.intensity, cpu.intensity, atol=1e-7, rtol=1e-5)
    np.testing.assert_array_equal(gpu.r86, cpu.r86)


def test_fresh_process_3d_preview_then_first_cuda_calculation(tmp_path):
    """独立解释器复现曾闪退的启动顺序，不能先在同一进程预热 CUDA。"""
    import json
    import subprocess
    import sys
    from pathlib import Path
    engine = backend.select_backend("cuda")
    if engine.name != "cuda":
        pytest.skip(engine.reason)
    root = Path(__file__).resolve().parents[1]
    output = tmp_path/"startup.json"
    result = subprocess.run([sys.executable,"-X","faulthandler",str(root/"scripts/validate_startup_crash.py"),
                             "--output",str(output),"--runs","3"],cwd=root,capture_output=True,timeout=150)
    assert result.returncode == 0, (result.returncode,result.stderr.decode(errors="replace")[-5000:])
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed" and report["preview_grid"] == 256
    assert len(report["runs"]) == 3
    assert all(row == {"grid":1024,"backend":"cuda","scene_matches":True,"fft_cache_released":True} for row in report["runs"])
    assert len(report["cleanup_threads"]) >= 3
    assert set(report["cleanup_threads"]) == {report["main_thread"]}
