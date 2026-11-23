"""使用可选的固定版本外部传播库验证代表性案例，不将其作为产品运行依赖。"""
import pytest
from gaussian_lab.model import Project, Element
from scripts.validate_numerics import compare_lightpipes


@pytest.mark.parametrize("elements", [[], [Element("lens", .1, .12)],
                                     [Element("aperture", .03, .0009, "A1"), Element("lens", .1, .12)]])
def test_lightpipes_convolution_agrees_on_bounded_cases(elements):
    pytest.importorskip("LightPipes")
    p = Project(grid=512, samples=17, window=.004, length=.22, elements=elements)
    report = compare_lightpipes(p)
    assert report["normalized_intensity_l1"] < .08
    assert report["r86_relative_difference"] < .05
    assert report["transmission_absolute_difference"] < .04



def test_focal_plane_shape_against_analytic_and_lightpipes():
    """独立核对真实焦面二维强度，外部卷积有限网格差异不能当成显示修正量。"""
    lp = pytest.importorskip("LightPipes")
    import numpy as np
    from gaussian_lab.optics import simulate, coordinates, initial_field, analytic
    p = Project(grid=1024, samples=17, window=.003, length=.18, elements=[Element("lens", .1, .04)])
    r = simulate(p)
    k = r.focus_index
    x, r2 = coordinates(p)
    actual = r.intensity[k]/r.intensity[k].max()
    w = analytic(p, [r.z[k]])[0]
    expected = np.exp(-2*r2/w**2)
    np.testing.assert_allclose(actual, expected, atol=1e-4)
    field = lp.Begin(p.window, p.wavelength, p.grid)
    field.field = initial_field(p, r2)
    field = lp.Fresnel(field, .1)
    field = lp.Lens(field, .04)
    field = lp.Fresnel(field, float(r.z[k] - .1))
    external = abs(field.field)**2
    external /= external.max()
    roi = r2 < (3*w)**2
    assert np.sqrt(np.mean((actual[roi] - external[roi])**2)) < .03
