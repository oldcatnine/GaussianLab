"""验证计算内核和模型，覆盖解析基准、衍射、扫描、取消与导出。"""
import threading
import numpy as np
import pytest
from gaussian_lab.model import Project, Element, preset, save_project, load_project
from gaussian_lab.optics import (analytic, output_gaussian, simulate, scan, convergence,
                                 fresnel, coordinates, initial_field, encircled_radius, Cancelled, export_csv)


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
