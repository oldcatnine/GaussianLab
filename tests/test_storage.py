"""验证完整强度磁盘缓存、文件生命周期及新增模式的物理含义。"""
import gc
import threading
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from gaussian_lab.model import Project, Mode, MODE_PRESET_KEYS, mode_preset, from_dict, save_project, load_project
from gaussian_lab.optics import simulate, coordinates, initial_field, Cancelled
from gaussian_lab.memory import estimate_memory
from gaussian_lab import storage


@pytest.mark.parametrize("key", MODE_PRESET_KEYS)
def test_requested_modes_and_power(key):
    modes = mode_preset(key)
    if key.startswith("LG"):
        assert modes == [Mode("LG", 0, int(key[-1]))]
    elif "+" not in key:
        assert modes == [Mode("HG", int(key[-2]), int(key[-1]))]
    else:
        assert modes == [Mode("HG", 0, 1), Mode("HG", 1, 0)]
    p = Project(grid=256, elements=[], modes=modes)
    _, r2 = coordinates(p)
    field = initial_field(p, r2)
    power = np.sum(abs(field)**2) * (p.window/p.grid)**2
    expected = np.pi*p.waist**2/2 * (2 if "+" in key else 1)
    assert power == pytest.approx(expected, rel=1e-9)
    if key.startswith("TEM") and "+" not in key:
        # 沿非节点的偏轴截线计数符号变化，独立验证两个方向的阶数和轴向对应。
        mid = p.grid//2
        for line, order in ((field[mid+5,:].real,modes[0].n),(field[:,mid+5].real,modes[0].m)):
            values = line[abs(line)>abs(line).max()*1e-10]
            assert np.count_nonzero(np.diff(np.signbit(values))) == order
    if key.startswith("LG"):
        mid = p.grid//2
        assert field[mid, mid] == 0
        assert field[mid+4, mid]/field[mid, mid+4] == pytest.approx(1j**int(key[-1]))


def test_tem_axes_and_coherent_phase():
    p = Project(grid=128, elements=[], modes=mode_preset("TEM03"))
    _, r2 = coordinates(p)
    a = initial_field(p, r2)
    p.modes = mode_preset("TEM30")
    np.testing.assert_allclose(initial_field(p, r2), a.T, atol=1e-14)
    p.modes = mode_preset("TEM01+TEM10")
    same = abs(initial_field(p, r2))**2
    assert same[68, 60] == pytest.approx(0, abs=1e-25)
    p.modes[1].phase_deg = 90
    quadrature = abs(initial_field(p, r2))**2
    assert quadrature[68, 60] > 0
    np.testing.assert_allclose(quadrature, quadrature.T, atol=1e-14)


def test_all_requested_tem_combinations_are_available():
    requested = {"TEM00","TEM01","TEM02","TEM10","TEM20","TEM21","TEM12","TEM30"}
    complete = {f"TEM{n}{m}" for n in range(4) for m in range(4)}
    assert requested <= set(MODE_PRESET_KEYS)
    assert complete <= set(MODE_PRESET_KEYS)
    assert len(MODE_PRESET_KEYS) == len(set(MODE_PRESET_KEYS)) == 22


def test_storage_choices_extended_sampling_and_roundtrip(tmp_path):
    p = Project(grid=4096, samples=2049)
    p.validate()
    assert p.selected_storage() == "disk"
    assert estimate_memory(p)["disk_bytes"] == p.result_storage_bytes()
    assert p.resident_result_bytes() == 64*1024**2
    path = tmp_path/"disk.json"
    save_project(p, path)
    assert load_project(path) == p
    p.storage_mode = "ram"
    with pytest.raises(ValueError, match="384 MiB"):
        p.validate()
    p.storage_mode = "bad"
    with pytest.raises(ValueError, match="存储"):
        p.validate()
    assert from_dict({"grid":128, "samples":17}).storage_mode == "ram"


def test_disk_ram_identical_refined_focus_and_view_lifetime(monkeypatch):
    p = Project(grid=128, samples=17, focus_refinement=2)
    expected = simulate(p)
    p.storage_mode = "disk"
    # 每张平面都重映射，覆盖焦面插入时的倒序移动与文件切片所有权。
    monkeypatch.setattr(Project, "resident_result_bytes", lambda self: self.grid**2*4)
    actual = simulate(p)
    assert actual.focus["z_m"] not in p.sampling_positions()
    np.testing.assert_array_equal(expected.intensity, actual.intensity)
    np.testing.assert_array_equal(expected.z, actual.z)
    np.testing.assert_array_equal(expected.r86, actual.r86)
    view = actual.intensity[actual.focus_index]
    path = view._owner.path
    peak = float(view.max())
    del actual
    gc.collect()
    assert path.exists() and float(view.max()) == peak
    del view
    gc.collect()
    assert not path.exists() and not path.parent.exists()


def test_auto_exceeds_ram_budget_without_reducing_sampling():
    p = Project(grid=128, samples=641, memory_limit_mib=32, focus_refinement=0, elements=[])
    r = simulate(p)
    assert isinstance(r.intensity, storage.DiskIntensity)
    assert r.intensity.shape == (641,128,128)
    assert r.provenance["memory_estimate"]["storage_mode"] == "disk"
    path = r.intensity._owner.path
    del r
    gc.collect()
    assert not path.exists()


def test_cancel_and_disk_full_cleanup(monkeypatch, tmp_path):
    def make_dir(**kwargs):
        directory = tmp_path / "private-result"
        directory.mkdir()
        return str(directory)
    monkeypatch.setattr(storage.tempfile, "mkdtemp", make_dir)
    p = Project(grid=128, samples=17, storage_mode="disk")
    cancel = threading.Event()
    with pytest.raises(Cancelled):
        simulate(p, progress=lambda value: cancel.set(), cancel=cancel)
    gc.collect()
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setattr(storage.shutil, "disk_usage", lambda _: SimpleNamespace(free=1))
    with pytest.raises(ValueError, match="磁盘空间不足"):
        storage.allocate_intensity(p)
    assert list(tmp_path.iterdir()) == []
