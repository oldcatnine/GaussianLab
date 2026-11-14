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
