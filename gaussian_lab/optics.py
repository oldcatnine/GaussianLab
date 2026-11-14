"""Paraxial Gaussian reference and sampled scalar Fresnel diffraction.

Fields use exp(-r²/w²) and a -i k r²/(2f) thin-lens phase.
FFT propagation is periodic; warnings do not constitute a convergence proof.
"""
from dataclasses import dataclass
import csv
import threading
import numpy as np
from scipy.fft import fft2, ifft2, fftfreq, fftshift
from .model import Project


class Cancelled(Exception):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise Cancelled("计算已取消")


def q_initial(p):
    return complex(-p.waist_z, np.pi * p.waist**2 / p.wavelength)


def radius(q, wavelength):
    return np.sqrt(-wavelength / (np.pi * (1 / q).imag))


def analytic(p, positions):
    p.validate()
    result = []
    for z in positions:
        q, last = q_initial(p), 0.0
        for e in p.ordered():
            if e.z > z:
                break
            q += e.z - last
            if e.kind == "lens":
                q = 1 / (1 / q - 1 / e.value)
            last = e.z
        result.append(radius(q + z - last, p.wavelength))
    return np.asarray(result)


def output_gaussian(p):
    """Reference after final active element, even when a real aperture is present."""
    q, last = q_initial(p), 0.0
    for e in p.ordered():
        q += e.z - last
        if e.kind == "lens":
            q = 1 / (1 / q - 1 / e.value)
        last = e.z
    w0 = np.sqrt(p.wavelength * q.imag / np.pi)
    return {"waist_z": float(last - q.real), "waist": float(w0),
            "divergence": float(p.wavelength / (np.pi * w0)), "last_z": last}


def coordinates(p):
    x = (np.arange(p.grid) - p.grid // 2) * (p.window / p.grid)
    xx, yy = np.meshgrid(x, x)
    return x, xx**2 + yy**2


def initial_field(p, r2):
    q = q_initial(p)
    w = radius(q, p.wavelength)
    # Gaussian reference uses opposite q phase convention to complex field.
    return np.exp(-r2 / w**2 + 1j * np.pi / p.wavelength * (1 / q).real * r2)


def fresnel(field, wavelength, dx, distance):
    if distance < -1e-14:
        raise ValueError("传播距离不能为负")
    if abs(distance) < 1e-14:
        return field.copy()
    f = fftfreq(field.shape[0], dx)
    phase = np.exp(-1j * np.pi * wavelength * distance * (f[:, None]**2 + f[None, :]**2))
    return ifft2(fft2(field) * phase)


def encircled_radius(intensity, radii, fraction=.86):
    energy = np.asarray(intensity).ravel()
    if not np.isfinite(energy).all() or energy.sum() <= 0:
        raise ValueError("光场能量为零或无效，请检查光阑与采样")
    order = np.argsort(radii.ravel())
    cumulative = np.cumsum(energy[order])
    i = np.searchsorted(cumulative, fraction * cumulative[-1])
    return float(radii.ravel()[order[min(i, len(order) - 1)]])


@dataclass
class Result:
    project: Project
    z: np.ndarray
    x: np.ndarray
    intensity: np.ndarray
    gaussian_w: np.ndarray
    r86: np.ndarray
    transmission: np.ndarray
    theta86: float
    reference: dict
    warnings: list[str]

    @property
    def focus_index(self):
        # Focus search only after the final lens (or final element without lenses).
        lenses = [e.z for e in self.project.ordered() if e.kind == "lens"]
        start = max(lenses) if lenses else 0
        valid = np.flatnonzero(self.z >= start)
        return int(valid[np.argmin(self.r86[valid])])


def simulate(project, cancel=None, progress=None):
    p = project.clone().validate()
    x, r2 = coordinates(p)
    rr = np.sqrt(r2)
    field = initial_field(p, r2)
    input_energy = float(np.sum(abs(field)**2))
    dx = p.window / p.grid
    zs = np.unique(np.r_[np.linspace(0, p.length, p.samples), [e.z for e in p.ordered()]])
    images, sizes, powers, warnings = [], [], [], []
    elements, index, last_z = p.ordered(), 0, 0.0
    last_element_field = field.copy()
    for i, z in enumerate(zs):
        check_cancel(cancel)
        field = fresnel(field, p.wavelength, dx, z - last_z)
        while index < len(elements) and elements[index].z <= z + 1e-14:
            e = elements[index]
            if e.kind == "lens":
                illuminated = rr[abs(field)**2 > abs(field).max()**2 * 1e-5]
                if illuminated.size and 2 * np.pi * illuminated.max() * dx / (p.wavelength * abs(e.value)) > np.pi:
                    warnings.append(f"{e.label} 透镜相位采样偏粗：请加密网格")
                field *= np.exp(-1j * np.pi * r2 / (p.wavelength * e.value))
            else:
                if e.value / dx < 12:
                    warnings.append(f"{e.label} 孔径不足 12 像素：请加密网格")
                field *= r2 <= (e.value / 2)**2
            index += 1
            last_element_field = field.copy()
        intensity = abs(field)**2
        images.append(intensity.astype(np.float32))
        sizes.append(encircled_radius(intensity, rr))
        powers.append(float(intensity.sum() / input_energy))
        border = np.ones(intensity.shape, bool)
        border[8:-8, 8:-8] = False
        if intensity[border].sum() / max(intensity.sum(), 1e-300) > .005:
            warnings.append("边界能量超过 0.5%：可能发生窗口截断/周期回绕，请扩大窗口并复核")
        last_z = z
        if progress:
            progress(int((i + 1) / len(zs) * 100))
    frequencies = fftshift(fftfreq(p.grid, dx)) * p.wavelength
    angular_r = np.sqrt(frequencies[:, None]**2 + frequencies[None, :]**2)
    angular_i = abs(fftshift(fft2(last_element_field)))**2
    theta = encircled_radius(angular_i, angular_r)
    if theta > .7 * p.wavelength / (2 * dx):
        warnings.append("远场角谱接近采样边界：θ86 可能欠采样")
    reference = output_gaussian(p)
    if not 0 <= reference["waist_z"] <= p.length:
        warnings.append("理想高斯参考束腰位于显示区间之外（可能为回推束腰）")
    sizes = np.asarray(sizes)
    result = Result(p, zs, x, np.asarray(images), analytic(p, zs), sizes, np.asarray(powers),
                    theta, reference, list(dict.fromkeys(warnings)))
    if result.focus_index == len(zs) - 1:
        result.warnings.append("数值最小 r86 位于搜索区间末端，请扩大传播范围")
    if sizes.min() < 3 * dx:
        result.warnings.append("最小光斑不足 3 个像素：尺寸精度有限，请加密网格")
    return result


def scan(project, element_index, low, high, count=11, cancel=None, progress=None):
    if not 0 <= element_index < len(project.elements):
        raise ValueError("请选择被扫描的元件")
    if not project.elements[element_index].enabled:
        raise ValueError("不能扫描已停用的元件")
    if not np.isfinite([low, high]).all() or low >= high or not 3 <= count <= 51:
        raise ValueError("扫描范围须递增，点数须在 3—51 之间")
    if project.elements[element_index].kind == "aperture" and low <= 0:
        raise ValueError("光阑扫描直径须大于零")
    rows = []
    for i, value in enumerate(np.linspace(low, high, count)):
        check_cancel(cancel)
        p = project.clone()
        p.elements[element_index].value = float(value)
        try:
            r = simulate(p, cancel)
            k = r.focus_index
            rows.append({"value_m": float(value), "min_r86_m": float(r.r86[k]), "focus_z_m": float(r.z[k]),
                         "transmission": float(r.transmission[-1]), "theta86_rad": r.theta86,
                         "status": "ok", "note": "；".join(r.warnings)})
        except ValueError as exc:
            rows.append({"value_m": float(value), "min_r86_m": float("nan"), "focus_z_m": float("nan"),
                         "transmission": float("nan"), "theta86_rad": float("nan"),
                         "status": "error", "note": str(exc)})
        if progress:
            progress(int((i + 1) / count * 100))
    return rows


def export_csv(rows, path):
    if not rows:
        raise ValueError("没有可导出的数据")
    with open(path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def convergence(project, cancel=None):
    """Compare base grid, finer dx, and larger window at unchanged dx."""
    if project.grid > 512:
        raise ValueError("收敛检查基准网格最多 512；将执行两次双倍网格计算")
    base = simulate(project, cancel)
    b = float(base.r86[-1])
    del base
    fine = project.clone()
    fine.grid *= 2
    refined = simulate(fine, cancel)
    fine_radius = float(refined.r86[-1])
    del refined
    wide = fine.clone()
    wide.window *= 2
    expanded = simulate(wide, cancel)
    # Compare the final observation plane as a reproducible metric.
    return {"base_r86_m": b, "fine_r86_m": fine_radius,
            "wide_r86_m": float(expanded.r86[-1]),
            "grid_change": float(abs(fine_radius - b) / b),
            "window_change": float(abs(expanded.r86[-1] - b) / b),
            "note": "仅比较末端观察面 r86；不代表焦点或远场全面收敛"}
