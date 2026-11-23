"""验证计算内核和模型，覆盖解析基准、衍射、扫描、取消与导出。"""
import threading
import numpy as np
import pytest
from gaussian_lab.model import Project, Element, preset, save_project, load_project
from gaussian_lab.optics import (analytic, output_gaussian, simulate, scan, convergence,
                                 fresnel, coordinates, initial_field, encircled_radius, field_at, result_metadata, export_result, radial_energy, Cancelled, export_csv)


def small(**kwargs):
    args = dict(grid=256, samples=17, elements=[])
    args.update(kwargs)
    return Project(**args)


def test_gaussian_at_waist_and_rayleigh_range():
    p = small()
    zr = np.pi * p.waist**2 / p.wavelength
    np.testing.assert_allclose(analytic(p, [0, zr, -zr]), [p.waist, p.waist*2**.5, p.waist*2**.5])


def test_waist_offset_and_lens_reference():
    p = small(waist_z=-.1, elements=[Element("lens", .1, .12)])
    zr = np.pi*p.waist**2/p.wavelength
    q = 1/(1/(.2+1j*zr)-1/.12)
    r = output_gaussian(p)
    assert r["waist_z"] == pytest.approx(.1-q.real)
    assert r["waist"] == pytest.approx(np.sqrt(p.wavelength*q.imag/np.pi))


def test_multiple_lens_order_against_matrix():
    p = preset("双透镜扩束")
    zr = np.pi*p.waist**2/p.wavelength
    matrix = np.eye(2)
    z = 0
    for e in p.ordered():
        space = np.array([[1, e.z-z], [0, 1]])
        lens = np.array([[1, 0], [-1/e.value, 1]])
        matrix = lens @ space @ matrix
        z = e.z
    q = (matrix[0, 0]*1j*zr+matrix[0, 1])/(matrix[1, 0]*1j*zr+matrix[1, 1])
    assert output_gaussian(p)["waist_z"] == pytest.approx(z-q.real)


@pytest.mark.parametrize("waist_z", [0, -.3, .3])
def test_fresnel_gaussian_matches_analytic_width(waist_z):
    p = small(waist_z=waist_z, length=.25)
    r = simulate(p)
    factor = np.sqrt(-np.log(.14)/2)
    np.testing.assert_allclose(r.r86, r.gaussian_w*factor, rtol=.045)
    np.testing.assert_allclose(r.transmission, 1, atol=1e-12)


def test_lens_focusing_numeric_vs_analytic():
    p = Project(grid=512, samples=65)
    r = simulate(p)
    k = r.focus_index
    assert abs(r.z[k]-r.reference["waist_z"]) < p.length/(p.samples-1)
    assert r.r86[k] == pytest.approx(r.reference["waist"]*np.sqrt(-np.log(.14)/2), rel=.15)
    assert r.r86[k] < r.r86[0] / 5


def test_aperture_transmission_matches_gaussian_integral():
    p = small(grid=512, elements=[Element("aperture", 0, .0007)])
    r = simulate(p)
    expected = 1-np.exp(-2*(.00035/p.waist)**2)
    assert r.transmission[-1] == pytest.approx(expected, rel=.015)
    assert r.transmission[-1] < 1


def test_small_aperture_broadens_far_field():
    p = small(window=.012, grid=512)
    full = simulate(p)
    p.elements = [Element("aperture", 0, .0005)]
    clipped = simulate(p)
    assert clipped.theta86 > full.theta86 * 1.5
    assert clipped.transmission[-1] < full.transmission[-1]


def test_far_field_gaussian_definition():
    p = small(window=.012, grid=512)
    r = simulate(p)
    expected = p.wavelength/(np.pi*p.waist)*np.sqrt(-np.log(.14)/2)
    assert r.theta86 == pytest.approx(expected, rel=.1)


def test_project_round_trip_and_units(tmp_path):
    p = preset("光阑衍射")
    path = tmp_path/"project.json"
    save_project(p, path)
    assert load_project(path) == p
    path.write_text('{"schema_version": 2, "units": "SI"}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_project(path)


@pytest.mark.parametrize("change", [dict(waist=-1), dict(wavelength=float("nan")), dict(grid=127),
                                   dict(elements=[Element("lens", .1, 0)]),
                                   dict(elements=[Element("aperture", .1, -1)]),
                                   dict(elements=[Element("lens", 2, .1)])])
def test_invalid_inputs(change):
    with pytest.raises(ValueError):
        small(**change).validate()


def test_scan_matches_individual_calculations():
    p = small(elements=[Element("lens", .1, .12)])
    rows = scan(p, 0, .10, .14, 3)
    for row in rows:
        q = p.clone()
        q.elements[0].value = row["value_m"]
        r = simulate(q)
        assert row["min_r86_m"] == r.r86[r.focus_index]
    assert p.elements[0].value == .12


def test_zero_focal_length_is_failed_scan_point():
    rows = scan(small(elements=[Element()]), 0, -.1, .1, 3)
    assert rows[1]["status"] == "error"
    assert np.isnan(rows[1]["min_r86_m"])


def test_cancellation():
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Cancelled):
        simulate(small(), cancel)


def test_fresnel_identity_and_power():
    p = small()
    _, r2 = coordinates(p)
    f = initial_field(p, r2)
    assert not np.shares_memory(fresnel(f, p.wavelength, p.window/p.grid, 0), f)
    out = fresnel(f, p.wavelength, p.window/p.grid, .1)
    assert np.sum(abs(f)**2) == pytest.approx(np.sum(abs(out)**2), rel=1e-12)


def test_convergence_and_csv(tmp_path):
    p = small(grid=128)
    check = convergence(p)
    assert check["grid_change"] < .06
    assert check["window_change"] < .06
    path = tmp_path/"scan.csv"
    export_csv([check], path)
    assert "grid_change" in path.read_text(encoding="utf-8-sig")


def test_result_snapshot_survives_input_edits():
    p = small()
    r = simulate(p)
    p.waist *= 2
    assert r.project.waist != p.waist


@pytest.mark.parametrize("fraction", [.5, .86, .95])
def test_encircled_radius_against_gaussian_energy_integral(fraction):
    """用独立的圆对称高斯能量积分验证半径定义，避免将 w 直接等同于 r86。"""
    p = small(grid=512)
    _, r2 = coordinates(p)
    intensity = np.exp(-2 * r2 / p.waist**2)
    expected = p.waist * np.sqrt(-np.log(1 - fraction) / 2)
    measured = encircled_radius(intensity, np.sqrt(r2), fraction)
    assert abs(measured - expected) <= p.window / p.grid


def test_short_focus_refinement_matches_independent_gaussian_reference():
    """在横向采样足够的短焦距案例中，验证局部细化改善粗轴向漏采。"""
    p = small(grid=1024, window=.003, length=.18, elements=[Element("lens", .1, .04)])
    r = simulate(p)
    expected = r.reference["waist"] * np.sqrt(-np.log(.14) / 2)
    assert abs(r.focus["r86_m"] - expected) < expected * .05
    assert abs(r.focus["z_m"] - r.reference["waist_z"]) < .001
    assert r.focus["r86_m"] < r.focus["coarse_r86_m"] * .6
    assert r.focus["evaluations"] > 0
    assert np.all(np.diff(r.z) > 0)
    assert r.intensity.shape == (len(r.z), p.grid, p.grid)
    assert r.intensity.dtype == np.float32
    assert r.r86[r.focus_index] == r.focus["r86_m"]


def test_refined_plane_respects_apertures_after_last_lens():
    p = small(grid=128, elements=[Element("lens", .1, .12), Element("aperture", .2, .0002)])
    r = simulate(p)
    _, r2 = coordinates(p)
    image = abs(field_at(p, r.z[r.focus_index], r2))**2
    np.testing.assert_allclose(r.intensity[r.focus_index], image, atol=1e-7, rtol=1e-5)
    assert r.transmission[-1] < 1


def test_convergence_separates_axes_and_exports_matching_snapshot(tmp_path):
    p = small(grid=128, samples=17, focus_refinement=0)
    report = convergence(p)
    base = report["variants"]["base"]["project"]
    assert report["variants"]["grid"]["project"]["window"] == base["window"]
    assert report["variants"]["window"]["project"]["grid"] == base["grid"] * 2
    assert report["variants"]["window"]["project"]["window"] == base["window"] * 2
    assert report["variants"]["axial"]["project"]["grid"] == base["grid"]
    assert report["variants"]["axial"]["project"]["samples"] == 33
    assert report["variants"]["axial"]["project"]["focus_refinement"] == 1
    for changes in report["changes"].values():
        assert "focus_z_absolute_m" in changes and "theta86_rad_relative" in changes
        assert "transmission_relative" in changes and "focus_profile_rms" in changes
    r = simulate(p)
    assert result_metadata(r, report)["convergence"] is report
    from copy import deepcopy
    stale = deepcopy(report)
    stale["variants"]["base"]["provenance"]["source_sha256"] = "旧源码摘要"
    assert result_metadata(r, stale)["convergence"] is None
    assert len(r.provenance["source_sha256"]) == 64
    other = p.clone()
    other.waist *= 1.1
    assert result_metadata(simulate(other), report)["convergence"] is None
    target = tmp_path / "propagation.csv"
    export_result(r, target, report)
    import json
    metadata = json.loads((tmp_path / "propagation.csv.meta.json").read_text(encoding="utf-8"))
    assert metadata["metrics"]["focus_z_m"] == r.focus["z_m"]
    assert metadata["convergence"]["variants"]["base"]["project"] == base
    assert (tmp_path / "propagation.energy.csv").is_file()


def test_radial_energy_combines_shells_and_normalizes():
    radii, fraction = radial_energy(np.ones((2, 2)), np.array([[0., 1.], [1., 2.]]))
    np.testing.assert_allclose(radii, [0, 1, 2])
    np.testing.assert_allclose(fraction, [.25, .75, 1])


def test_focus_boundary_is_flagged_and_disabled_refinement_preserves_coarse_grid():
    p = small(grid=128, focus_refinement=0)
    r = simulate(p)
    assert len(r.z) == p.samples
    assert r.focus["boundary_minimum"]
    assert any("边界" in warning for warning in r.warnings)


def test_refinement_checks_cancellation_between_planes(monkeypatch):
    import gaussian_lab.optics as optics
    p = small(grid=128)
    cancel = threading.Event()
    original = optics.field_at
    def stop_after_first(*args, **kwargs):
        value = original(*args, **kwargs)
        cancel.set()
        return value
    monkeypatch.setattr(optics, "field_at", stop_after_first)
    with pytest.raises(Cancelled):
        simulate(p, cancel)


@pytest.mark.parametrize("levels", [-1, 5, 1.5, True])
def test_invalid_refinement_levels_are_rejected(levels):
    with pytest.raises(ValueError, match="焦区细化"):
        small(focus_refinement=levels).validate()


def test_warned_scan_points_are_not_silently_marked_ok():
    rows = scan(small(grid=128, elements=[Element("lens", .1, .04)]), 0, .03, .05, 3)
    assert all(row["status"] == "warning" and row["note"] for row in rows)
    assert all("focus_bracket_m" in row for row in rows)



def test_source_fingerprint_handles_frozen_environment_without_source(monkeypatch):
    import gaussian_lab.optics as optics
    from pathlib import Path
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("冻结程序中没有独立 Python 源文件")
    monkeypatch.setattr(Path, "read_bytes", unavailable)
    assert optics.source_fingerprint() is None
    assert optics.calculation_provenance()["algorithm_version"] == optics.ALGORITHM_VERSION


def test_lens_clear_diameter_matches_explicit_aperture(tmp_path):
    p = small(grid=128, elements=[Element("lens", .1, .12, clear_diameter=.0008)])
    equivalent = p.clone()
    equivalent.elements[0].clear_diameter = None
    equivalent.elements.insert(0, Element("aperture", .1, .0008))
    a, b = simulate(p), simulate(equivalent)
    np.testing.assert_allclose(a.z, b.z)
    np.testing.assert_allclose(a.intensity, b.intensity)
    np.testing.assert_allclose(a.r86, b.r86)
    np.testing.assert_allclose(a.transmission, b.transmission)
    assert 0 < a.transmission[-1] < 1
    path = tmp_path / "lens.json"
    save_project(p, path)
    assert load_project(path) == p
    p.elements[0].clear_diameter = None
    save_project(p, path)
    assert "clear_diameter" not in path.read_text(encoding="utf-8")
    assert load_project(path) == p
    for diameter in (0, -.001, float("nan"), float("inf")):
        p.elements[0].clear_diameter = diameter
        with pytest.raises(ValueError, match="有效通光直径"):
            p.validate()


@pytest.mark.parametrize("mode", [("HG", 0, 0), ("HG", 3, 2), ("LG", 2, -3)])
def test_modes_equal_power_and_free_space_conservation(mode):
    """用解析归一化与无损传播检查高阶模式，而非只核对形状截图。"""
    from gaussian_lab.model import Mode
    p = small(grid=256, window=.006, modes=[Mode(*mode)])
    _, r2 = coordinates(p)
    value = initial_field(p, r2)
    power = np.sum(abs(value)**2) * (p.window / p.grid)**2
    assert power == pytest.approx(np.pi*p.waist**2/2, rel=1e-7)
    r = simulate(p)
    np.testing.assert_allclose(r.transmission, 1, atol=1e-12)
    assert r.provenance["sampling"]["coherent_input"] is True


def test_hg_nodes_lg_vortex_and_phase_interference():
    """解析节点、涡旋符号与相位反转验证复振幅输入的物理含义。"""
    from gaussian_lab.model import Mode
    p = small(modes=[Mode("HG", 1, 0)])
    _, r2 = coordinates(p)
    hg = initial_field(p, r2)
    mid = p.grid//2
    np.testing.assert_allclose(hg[:, mid], 0, atol=1e-15)
    assert hg[mid, mid+5] == pytest.approx(-hg[mid, mid-5])
    p.modes = [Mode("LG", 0, 1)]
    lg = initial_field(p, r2)
    assert lg[mid, mid] == 0
    assert lg[mid+5, mid] / lg[mid, mid+5] == pytest.approx(1j)
    p.modes = [Mode("LG", 0, -1)]
    np.testing.assert_allclose(initial_field(p, r2), lg.conj(), atol=1e-14)
    p.modes = [Mode(), Mode("HG", 1, 0)]
    a = initial_field(p, r2)
    p.modes[1].phase_deg = 180
    b = initial_field(p, r2)
    assert abs(a[mid, mid+5])**2 == pytest.approx(abs(b[mid, mid-5])**2)
    assert abs(a[mid, mid+5])**2 > abs(b[mid, mid+5])**2
    p.modes = [Mode(), Mode(phase_deg=180)]
    with pytest.raises(ValueError, match="相消"):
        simulate(p)


def test_coherent_propagation_is_linear_with_waist_offset():
    from gaussian_lab.model import Mode
    p = small(grid=128, waist_z=.1, modes=[Mode(), Mode("LG", 1, 2, .7, 55)])
    _, r2 = coordinates(p)
    combined = field_at(p, .2, r2)
    parts = []
    for mode in p.modes:
        q = p.clone()
        q.modes = [mode]
        parts.append(field_at(q, .2, r2))
    np.testing.assert_allclose(combined, sum(parts), atol=1e-13)


def test_mode_project_roundtrip_legacy_and_validation(tmp_path):
    from gaussian_lab.model import Mode, from_dict
    p = small(modes=[Mode(), Mode("LG", 2, -3, .4, 90)])
    path = tmp_path / "modes.json"
    save_project(p, path)
    assert load_project(path) == p
    assert from_dict({"grid": 128, "samples": 17}).modes == [Mode()]
    q = p.clone()
    q.modes[0].phase_deg = 45
    assert p.modes[0].phase_deg == 0
    for modes in ([], [Mode("bad")], [Mode("HG", -1)], [Mode("HG", 0, -1)],
                  [Mode("LG", 9)], [Mode(amplitude=float("nan"))], [Mode(amplitude=0)],
                  [Mode(phase_deg=float("inf"))], [Mode()]*9):
        p.modes = modes
        with pytest.raises(ValueError):
            p.validate()


def test_finer_sampling_limits_and_actual_axial_planes():
    assert Project().grid == 1024
    small(grid=2048, samples=17).validate()
    with pytest.raises(ValueError, match="384 MiB"):
        small(grid=2048, samples=65, storage_mode="ram").validate()
    p = small(grid=128, samples=641, focus_refinement=0)
    r = simulate(p)
    assert len(r.z) == 641
    assert r.provenance["sampling"]["axial_step_m"] == pytest.approx(p.length/640)
    assert r.intensity.shape == (641, 128, 128)


def test_higher_modes_match_independent_lightpipes_source():
    """对照已有验证依赖，比较 HG/LG 源场；只允许相同归一化常数。"""
    lp = pytest.importorskip("LightPipes")
    from gaussian_lab.model import Mode
    for mode in [Mode("HG", 2, 1), Mode("LG", 1, 2)]:
        p = small(modes=[mode])
        _, r2 = coordinates(p)
        actual = initial_field(p, r2)
        reference = lp.Begin(p.window, p.wavelength, p.grid)
        if mode.family == "HG":
            reference = lp.GaussHermite(reference, p.waist, n=mode.m, m=mode.n)
        else:
            # 本项目采用 exp(+i lφ)，上游采用 exp(-i lφ)，比较时翻转方位阶数。
            reference = lp.GaussLaguerre(reference, p.waist, p=mode.n, l=-mode.m, ecs=0)
        expected = reference.field
        scale = np.vdot(expected, actual) / np.vdot(expected, expected)
        np.testing.assert_allclose(actual, expected * scale, atol=1e-12)



@pytest.mark.parametrize("budget", [0, 31, 65537, 384.0, True, float("nan")])
def test_memory_limit_rejects_invalid_budget(budget):
    with pytest.raises(ValueError, match="结果数据上限"):
        small(memory_limit_mib=budget).validate()


def test_custom_memory_limit_legacy_and_roundtrip(tmp_path):
    from gaussian_lab.model import from_dict
    p = small(grid=2048, samples=65, memory_limit_mib=1536, storage_mode="ram")
    p.validate()
    assert p.result_storage_bytes() == 1056 * 1024**2
    path = tmp_path / "memory.json"
    save_project(p, path)
    assert load_project(path).memory_limit_mib == 1536
    assert from_dict({"grid": 128, "samples": 17}).memory_limit_mib == 384
    p.memory_limit_mib = 384
    with pytest.raises(ValueError, match="提高结果数据上限"):
        p.validate()


def test_memory_prediction_matches_allocated_volume_with_duplicate_disabled_planes():
    from gaussian_lab.memory import estimate_memory
    p = small(grid=128, samples=17, focus_refinement=0,
              elements=[Element("lens", .1, .2), Element("lens", .1, -.2),
                        Element("lens", .111, .3, enabled=False)])
    predicted = estimate_memory(p)
    assert len(p.sampling_positions()) == 17
    assert predicted["allocated_planes"] == 18
    r = simulate(p)
    assert r.intensity.base.nbytes == predicted["result_bytes"]
    assert r.provenance["memory_estimate"] == predicted
    p.elements[-1].enabled = True
    updated = estimate_memory(p)
    assert updated["allocated_planes"] == 19
    assert updated["result_bytes"] > predicted["result_bytes"]
    assert updated["cuda_device_high_bytes"] > predicted["cuda_device_high_bytes"]


def test_memory_prediction_scales_and_does_not_probe_cuda(monkeypatch):
    from gaussian_lab.memory import estimate_memory, system_memory, format_memory
    from gaussian_lab import backend
    def forbidden():
        raise AssertionError("预测内存不应初始化 CUDA")
    monkeypatch.setattr(backend, "cuda_probe", forbidden)
    p = small(grid=128)
    a = estimate_memory(p)
    p.grid = 256
    b = estimate_memory(p)
    for key in a:
        if key.endswith("bytes"):
            assert b[key] == 4*a[key]
    info = system_memory()
    if info["total_bytes"] is not None:
        assert 0 <= info["available_bytes"] <= info["total_bytes"]
    assert format_memory(None) == "未知"
    assert format_memory(1024**3) == "1.00 GiB"
