"""近轴高斯参考解与离散标量菲涅耳衍射。

光场采用 exp(-r²/w²)，薄透镜相位为 -i k r²/(2f)。
快速傅里叶传播具有周期性；诊断警告不能代替收敛验证。
"""
from dataclasses import asdict, dataclass, field
import csv
import json
import hashlib
import math
from pathlib import Path
import platform
import subprocess
from datetime import datetime
import scipy
from . import __version__
import numpy as np
from scipy.fft import fft2, ifft2, fftfreq, fftshift
from .model import Project
from .memory import estimate_memory
from .backend import Backend, array_module, select_backend, invalidate_cuda
from bisect import bisect_right
from functools import lru_cache


ALGORITHM_VERSION = "fresnel-coherent-modes-v3.2"


def source_fingerprint():
    """记录加载时的源码摘要；冻结程序可能没有独立源文件，明确返回未知。"""
    digest = hashlib.sha256()
    try:
        for name in ("optics.py", "model.py", "backend.py"):
            digest.update((Path(__file__).parent / name).read_bytes())
    except OSError:
        return None
    return digest.hexdigest()


SOURCE_SHA256 = source_fingerprint()


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
    """计算末个启用元件后的理想高斯参考；存在光阑时也不把参考解视为截断场解。"""
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
    """在入口面相干求和归一到同一基模功率的 HG/LG 模式，保留干涉项。"""
    xp = array_module(r2)
    q = q_initial(p)
    w = radius(q, p.wavelength)
    # 复光场的相位表示与高斯 q 参数的符号约定相配套。
    envelope = xp.exp(-r2 / w**2 + 1j * np.pi / p.wavelength * (1 / q).real * r2)
    axis = (xp.arange(p.grid) - p.grid // 2) * (p.window / p.grid)
    xx, yy = axis[None, :], axis[:, None]
    value = xp.zeros_like(envelope)
    for mode in p.modes:
        if mode.family == "HG":
            def hermite(order, t):
                previous, current = xp.ones_like(t), 2 * t
                if order == 0:
                    return previous
                for k in range(1, order):
                    previous, current = current, 2 * t * current - 2 * k * previous
                return current
            shape = (hermite(mode.n, np.sqrt(2) * xx / w)
                     * hermite(mode.m, np.sqrt(2) * yy / w)
                     / math.sqrt(2**(mode.n + mode.m) * math.factorial(mode.n) * math.factorial(mode.m)))
        else:
            order = abs(mode.m)
            rho = 2 * r2 / w**2
            previous, current = xp.ones_like(rho), 1 + order - rho
            if mode.n == 0:
                polynomial = previous
            else:
                for k in range(1, mode.n):
                    previous, current = current, ((2*k + 1 + order - rho)*current - (k + order)*previous)/(k + 1)
                polynomial = current
            shape = (math.sqrt(math.factorial(mode.n) / math.factorial(mode.n + order))
                     * rho**(order / 2) * polynomial * xp.exp(1j * mode.m * xp.arctan2(yy, xx)))
        value += mode.amplitude * xp.exp(1j * np.deg2rad(mode.phase_deg)) * envelope * shape
    scale = sum(mode.amplitude**2 for mode in p.modes) * float(xp.sum(abs(envelope)**2))
    if float(xp.sum(abs(value)**2)) <= max(scale * 1e-24, 1e-300):
        raise ValueError("相干输入近乎完全相消或光场无有效能量，请调整振幅、相位或窗口")
    return value


def fresnel(field, wavelength, dx, distance):
    if distance < -1e-14:
        raise ValueError("传播距离不能为负")
    if abs(distance) < 1e-14:
        return field.copy()
    f = fftfreq(field.shape[0], dx)
    phase = np.exp(-1j * np.pi * wavelength * distance * (f[:, None]**2 + f[None, :]**2))
    return ifft2(fft2(field) * phase)


def encircled_radius(intensity, radii, fraction=.86, order=None):
    xp = array_module(intensity)
    energy = xp.asarray(intensity).ravel()
    if not bool(xp.isfinite(energy).all()) or float(energy.sum()) <= 0:
        raise ValueError("光场能量为零或无效，请检查光阑与采样")
    if not 0 < fraction < 1:
        raise ValueError("包围能量比例须在 0 与 1 之间")
    if order is None:
        order = xp.argsort(radii.ravel())
    cumulative = xp.cumsum(energy[order])
    i = int(xp.searchsorted(cumulative, fraction * cumulative[-1]))
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
    focus: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    @property
    def focus_index(self):
        if self.focus:
            return int(np.argmin(abs(self.z - self.focus["z_m"])))
        # 兼容旧结果；仅在末片透镜之后搜索。
        lenses = [e.z for e in self.project.ordered() if e.kind == "lens"]
        start = max(lenses) if lenses else 0
        valid = np.flatnonzero(self.z >= start)
        return int(valid[np.argmin(self.r86[valid])])



class Propagation:
    """每个光学区段缓存起点频谱；任意观察面与焦区只做一次逆 FFT。"""

    def __init__(self, project, r2, backend=None, cancel=None):
        self.p, self.r2 = project, r2
        self.backend = backend or Backend()
        self.xp, self.fft = self.backend.xp, self.backend.fft
        self.cancel = cancel
        self.starts = [0.0]
        value = initial_field(project, r2)
        self.fields = [value]
        self.spectra = [None]
        self.warnings = []
        dx = project.window / project.grid
        f = self.fft.fftfreq(project.grid, dx)
        self.phase_rate = -1j * np.pi * project.wavelength * (f[:, None]**2 + f[None, :]**2)
        for element in project.ordered():
            check_cancel(cancel)
            value = self.at(element.z)
            diameter = element.value if element.kind == "aperture" else element.clear_diameter
            if diameter is not None:
                if diameter / dx < 12:
                    self.warnings.append(f"{element.label} 孔径不足 12 像素：请加密网格")
                value *= r2 <= (diameter / 2)**2
            if element.kind == "lens":
                illuminated = self.xp.sqrt(r2)[abs(value)**2 > abs(value).max()**2 * 1e-5]
                if illuminated.size and float(illuminated.max()) * 2 * dx > project.wavelength * abs(element.value):
                    self.warnings.append(f"{element.label} 透镜相位采样偏粗：请加密网格")
                value *= self.xp.exp(-1j * np.pi * r2 / (project.wavelength * element.value))
            self.starts.append(element.z)
            self.fields.append(value)
            self.spectra.append(None)

    def at(self, z):
        check_cancel(self.cancel)
        i = bisect_right(self.starts, z) - 1
        if i < 0:
            raise ValueError("传播距离不能为负")
        distance = z - self.starts[i]
        if abs(distance) < 1e-14:
            return self.fields[i].copy()
        if self.spectra[i] is None:
            self.spectra[i] = self.fft.fft2(self.fields[i])
        return self.fft.ifft2(self.spectra[i] * self.xp.exp(self.phase_rate * distance))


def field_at(project, z, r2, cancel=None, propagation=None):
    """从入口独立传播到任意观察面，确保跨越光阑和同位置元件时执行顺序一致。"""
    return (propagation or Propagation(project, r2, cancel=cancel)).at(z)


def refine_focus(p, zs, sizes, r2, order, cancel, propagation=None):
    """用实际衍射半径细化粗最小区间；高斯束腰仅作额外探测点，不替代数值答案。"""
    start = max((e.z for e in p.ordered() if e.kind == "lens"), default=0.0)
    indices = np.flatnonzero(zs >= start)
    coarse = int(indices[np.argmin(sizes[indices])])
    points = {float(zs[i]): float(sizes[i]) for i in indices}
    radii = array_module(r2).sqrt(r2)
    evaluations = 0

    def measure(z):
        nonlocal evaluations
        check_cancel(cancel)
        z = float(z)
        if z not in points:
            value = field_at(p, z, r2, cancel, propagation)
            points[z] = encircled_radius(abs(value)**2, radii, order=order)
            evaluations += 1
        return points[z]

    def bracket():
        positions = np.array(sorted(points))
        values = np.array([points[z] for z in positions])
        minimum = values.min()
        tied = np.flatnonzero(np.isclose(values, minimum, rtol=0, atol=1e-15))
        # 取最长连续等值区间的中心，避免把平台左端误报成唯一焦点。
        runs = np.split(tied, np.flatnonzero(np.diff(tied) > 1) + 1)
        run = max(runs, key=lambda group: positions[group[-1]] - positions[group[0]])
        lo = positions[max(0, run[0] - 1)]
        hi = positions[min(len(positions) - 1, run[-1] + 1)]
        center = (positions[run[0]] + positions[run[-1]]) / 2
        return float(lo), float(hi), float(center), minimum

    if p.focus_refinement:
        hint = output_gaussian(p)["waist_z"]
        if start <= hint <= p.length:
            measure(hint)
        for _ in range(p.focus_refinement):
            lo, hi, _, _ = bracket()
            for z in np.linspace(lo, hi, 9):
                measure(z)
        lo, hi, center, minimum = bracket()
        measure(center)
        # 中心重新测量后若不属于最低平台，保留已测得的最小值。
        best = min(points, key=lambda z: (points[z], abs(z - center)))
    else:
        best = float(zs[coarse])
        lo = float(zs[max(indices[0], coarse - 1)])
        hi = float(zs[min(len(zs) - 1, coarse + 1)])
    boundary = points.get(start, np.inf) <= points[best] or points.get(p.length, np.inf) <= points[best]
    return {"z_m": float(best), "r86_m": float(points[best]), "coarse_z_m": float(zs[coarse]),
            "coarse_r86_m": float(sizes[coarse]), "bracket_m": [lo, hi],
            "axial_bracket_width_m": hi - lo, "transverse_step_m": p.window / p.grid,
            "levels": p.focus_refinement, "evaluations": evaluations,
            "search_interval_m": [start, p.length], "boundary_minimum": bool(boundary),
            "note": "局部离散细化；括区与横向像素不是严格误差上界，多峰和硬孔径仍需收敛复核"}


@lru_cache(maxsize=1)
def source_revision():
    """会话首次计算时记录仓库状态，避免每次预览启动两个 Git 子进程。"""
    root = Path(__file__).resolve().parents[1]
    revision, dirty = None, None
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL,
                                           timeout=2, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).decode().strip()
        changes = subprocess.check_output(["git", "status", "--porcelain", "--", "gaussian_lab"],
                                          cwd=root, stderr=subprocess.DEVNULL, timeout=2,
                                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        dirty = bool(changes.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {"source_revision": revision, "source_dirty": dirty,
            "source_state_captured_at": datetime.now().astimezone().isoformat()}


def calculation_provenance():
    """记录每次计算时间、已加载源码摘要和会话首次捕获的仓库状态。"""
    return {"source_sha256": SOURCE_SHA256, "calculated_at": datetime.now().astimezone().isoformat(), **source_revision(),
            "algorithm_version": ALGORITHM_VERSION,
            "software_version": __version__, "python": platform.python_version(),
            "numpy": np.__version__, "scipy": scipy.__version__}

def simulate(project, cancel=None, progress=None, backend="cpu"):
    """按所选后端执行；仅 CUDA 执行错误回退，不吞掉参数错误或取消。"""
    project.validate()
    engine = select_backend(backend, project.grid)
    try:
        return _simulate(project, cancel, progress, engine)
    except Cancelled:
        raise
    except Exception as exc:
        if engine.name != "cuda" or not type(exc).__module__.startswith(("cupy", "cupy_backends")):
            raise
        invalidate_cuda(exc)
        check_cancel(cancel)
        cpu = Backend(requested=backend, reason=f"CUDA 执行失败，重新使用 CPU；{type(exc).__name__}: {exc}")
        return _simulate(project, cancel, progress, cpu)


def _simulate(project, cancel, progress, engine):
    p = project.clone().validate()
    xp, transforms = engine.xp, engine.fft
    x, r2 = coordinates(p)
    r2 = xp.asarray(r2)
    rr = xp.sqrt(r2)
    field = initial_field(p, r2)
    input_energy = float(xp.sum(abs(field)**2))
    dx = p.window / p.grid
    zs = np.asarray(p.sampling_positions())
    images = np.empty((len(zs) + 1, p.grid, p.grid), dtype=np.float32)
    propagation = Propagation(p, r2, engine, cancel)
    sizes, powers, warnings = [], [], list(propagation.warnings)
    if len(p.modes) != 1 or p.modes[0].n or p.modes[0].m:
        warnings.append("高阶/相干叠加输入：高斯 w、束腰与 θ 仅为基模包络参考；实际指标使用 r86 与 θ86")
    order = xp.argsort(rr.ravel())
    border = xp.ones(r2.shape, bool)
    border[8:-8, 8:-8] = False
    last_element_field = propagation.fields[-1]
    for i, z in enumerate(zs):
        check_cancel(cancel)
        field = propagation.at(float(z))
        intensity = abs(field)**2
        images[i] = engine.host(intensity)
        sizes.append(encircled_radius(intensity, rr, order=order))
        powers.append(float(intensity.sum() / input_energy))
        if float(intensity[border].sum()) / max(float(intensity.sum()), 1e-300) > .005:
            warnings.append("边界能量超过 0.5%：可能发生窗口截断/周期回绕，请扩大窗口并复核")
        if progress:
            progress(int((i + 1) / len(zs) * 80))
    frequencies = transforms.fftshift(transforms.fftfreq(p.grid, dx)) * p.wavelength
    angular_r = xp.sqrt(frequencies[:, None]**2 + frequencies[None, :]**2)
    angular_i = abs(transforms.fftshift(transforms.fft2(last_element_field)))**2
    theta = encircled_radius(angular_i, angular_r)
    if theta > .7 * p.wavelength / (2 * dx):
        warnings.append("远场角谱接近采样边界：θ86 可能欠采样")
    reference = output_gaussian(p)
    if not 0 <= reference["waist_z"] <= p.length:
        warnings.append("理想高斯参考束腰位于显示区间之外（可能为回推束腰）")
    sizes = np.asarray(sizes)
    focus = refine_focus(p, zs, sizes, r2, order, cancel, propagation)
    selected = focus["z_m"]
    if not np.any(zs == selected):
        j = int(np.searchsorted(zs, selected))
        for k in range(len(zs), j, -1):
            images[k] = images[k - 1]
        selected_intensity = abs(propagation.at(selected))**2
        images[j] = engine.host(selected_intensity)
        if float(selected_intensity[border].sum() / selected_intensity.sum()) > .005:
            warnings.append("细化焦区边界能量超过 0.5%：请扩大窗口并复核")
        zs = np.insert(zs, j, selected)
        sizes = np.insert(sizes, j, focus["r86_m"])
        powers = np.insert(powers, j, float(selected_intensity.sum() / input_energy))
    result = Result(p, zs, x, images[:len(zs)], analytic(p, zs), sizes, np.asarray(powers),
                    theta, reference, list(dict.fromkeys(warnings)), focus, calculation_provenance())
    result.provenance["backend"] = engine.information()
    result.provenance["input_power_integral"] = input_energy * dx**2
    result.provenance["memory_estimate"] = estimate_memory(p)
    result.provenance["sampling"] = {"transverse_step_m": dx,
                                     "axial_step_m": p.length / (p.samples - 1),
                                     "stored_planes": len(zs), "coherent_input": True}
    if focus["boundary_minimum"]:
        result.warnings.append("最小 r86 平台接触搜索区间边界；可能没有内部焦点，请检查传播范围")
    if sizes.min() < 3 * dx:
        result.warnings.append("最小光斑不足 3 个像素：尺寸精度有限，请加密网格")
    if progress:
        progress(100)
    return result


def scan(project, element_index, low, high, count=11, cancel=None, progress=None, backend="cpu"):
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
            r = simulate(p, cancel, backend=backend)
            k = r.focus_index
            rows.append({"value_m": float(value), "min_r86_m": float(r.r86[k]), "focus_z_m": float(r.z[k]),
                         "transmission": float(r.transmission[-1]), "theta86_rad": r.theta86,
                         "focus_bracket_m": r.focus["axial_bracket_width_m"],
                         "backend": r.provenance["backend"]["used"],
                         "backend_reason": r.provenance["backend"]["reason"],
                         "status": "warning" if r.warnings else "ok", "note": "；".join(r.warnings)})
        except ValueError as exc:
            rows.append({"value_m": float(value), "min_r86_m": float("nan"), "focus_z_m": float("nan"),
                         "transmission": float("nan"), "theta86_rad": float("nan"),
                         "focus_bracket_m": float("nan"), "backend": "not_run", "backend_reason": "参数或能量无效",
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



def result_summary(result):
    """提取可序列化指标与固定物理坐标的剖面，供导出与收敛使用。"""
    k = result.focus_index
    p = result.project
    image = result.intensity[k]
    profile_x = np.linspace(-min(p.window / 4, max(result.r86[k] * 3, p.waist)),
                            min(p.window / 4, max(result.r86[k] * 3, p.waist)), 129)
    profile = np.interp(profile_x, result.x, image[p.grid // 2] / max(float(image.max()), 1e-30))
    radii, energy = radial_energy(image, np.sqrt(np.add.outer(result.x**2, result.x**2)))
    quality = {"r50_m": float(radii[np.searchsorted(energy, .5)]),
               "r95_m": float(radii[np.searchsorted(energy, .95)]),
               "energy_inside_2r86": float(np.interp(2 * result.r86[k], radii, energy))}
    return {"quality": quality, "provenance": result.provenance, "endpoint_r86_m": float(result.r86[-1]), "focus_r86_m": float(result.r86[k]),
            "focus_z_m": float(result.z[k]), "theta86_rad": result.theta86,
            "transmission": float(result.transmission[-1]), "focus": result.focus,
            "profile_x_m": profile_x.tolist(), "focus_profile": profile.tolist(),
            "warnings": result.warnings, "project": asdict(p)}


def convergence(project, cancel=None, backend="cpu"):
    """分别改变横向网格、窗口与轴向分辨率；报告多指标变化，不自动宣称通过。"""
    project.validate()
    if project.grid > 1024 or project.focus_refinement >= 4 or project.samples > 321:
        raise ValueError("收敛检查基准网格最多 1024、轴向最多 321 点，焦区细化级数最多 3；加密结果仍受内存限制")
    variants = {"base": project.clone()}
    fine = project.clone()
    fine.grid *= 2
    variants["grid"] = fine
    wide = fine.clone()
    wide.window *= 2
    variants["window"] = wide
    axial = project.clone()
    axial.samples = 2 * axial.samples - 1
    axial.focus_refinement += 1
    variants["axial"] = axial
    # 先校验所有配置，避免执行到一半才遇到结果体积限制。
    for p in variants.values():
        p.validate()
    summaries = {}
    for name, p in variants.items():
        check_cancel(cancel)
        result = simulate(p, cancel, backend=backend)
        summaries[name] = result_summary(result)
        del result
    base = summaries["base"]
    changes = {}
    for name in ("grid", "window", "axial"):
        other = summaries[name]
        changes[name] = {key + "_relative": abs(other[key] - base[key]) / max(abs(base[key]), 1e-30)
                         for key in ("endpoint_r86_m", "focus_r86_m", "theta86_rad", "transmission")}
        changes[name]["focus_z_absolute_m"] = abs(other["focus_z_m"] - base["focus_z_m"])
        # 插值到基准剖面的同一物理横坐标；各自焦面，不等同于同一固定 z 平面。
        profile = np.interp(base["profile_x_m"], other["profile_x_m"], other["focus_profile"])
        changes[name]["focus_profile_rms"] = float(np.sqrt(np.mean((profile - base["focus_profile"])**2)))
    return {"algorithm_version": ALGORITHM_VERSION, "variants": summaries, "changes": changes,
            "base_r86_m": base["endpoint_r86_m"], "fine_r86_m": summaries["grid"]["endpoint_r86_m"],
            "wide_r86_m": summaries["window"]["endpoint_r86_m"],
            "grid_change": changes["grid"]["endpoint_r86_m_relative"],
            "window_change": changes["window"]["endpoint_r86_m_relative"],
            "status": "需结合警告与用途判断",
            "project": asdict(project),
            "note": "分别比较网格、等间距扩大窗口及轴向细化；结果变化不是严格误差界，也不自动构成精度认证"}


def result_metadata(result, convergence_report=None):
    """导出定义、输入与完整结果摘要；收敛记录只允许关联完全相同的输入。"""
    matching = (convergence_report is not None and
                convergence_report.get("algorithm_version") == ALGORITHM_VERSION and
                convergence_report["variants"]["base"]["project"] == asdict(result.project) and
                convergence_report["variants"]["base"].get("provenance", {}).get("source_sha256") ==
                result.provenance.get("source_sha256"))
    return {"schema_version": 2, "software_version": __version__, "algorithm_version": ALGORITHM_VERSION,
            "python": platform.python_version(), "numpy": np.__version__, "units": "SI",
            "project": asdict(result.project), "provenance": result.provenance, "metrics": result_summary(result),
            "definitions": {"gaussian_w_m": "无截断理想高斯强度 1/e² 半径参考",
                            "r86_m": "以光轴为圆心的 86% 包围能量半径",
                            "theta86_rad": "末个启用元件出射角谱的 86% 包围能量半角",
                            "intensity": "相对强度，未标定绝对功率"},
            "reference": result.reference, "warnings": result.warnings,
            "convergence": convergence_report if matching else None,
            "precision_status": "需复核采样与模型边界"}


def export_result(result, path, convergence_report=None):
    """将传播曲线、参数快照、完整指标及焦面包围能量曲线一并保存。"""
    from .model import save_project
    rows = [{"z_m": float(z), "gaussian_w_m": float(w), "r86_m": float(r), "transmission": float(t)}
            for z, w, r, t in zip(result.z, result.gaussian_w, result.r86, result.transmission)]
    export_csv(rows, path)
    save_project(result.project, Path(path).with_suffix(".project.json"))
    Path(str(path) + ".meta.json").write_text(
        json.dumps(result_metadata(result, convergence_report), ensure_ascii=False, indent=2), encoding="utf-8")
    rr = np.sqrt(np.add.outer(result.x**2, result.x**2))
    image = result.intensity[result.focus_index]
    radii, energy = radial_energy(image, rr)
    export_csv([{"radius_m": float(r), "encircled_fraction": float(e)} for r, e in zip(radii, energy)],
               Path(path).with_suffix(".energy.csv"))


def radial_energy(intensity, radii):
    """将同半径像素合并，得到以光轴为中心的包围能量曲线。"""
    flat = np.asarray(intensity, dtype=float).ravel()
    total = flat.sum()
    if not np.isfinite(flat).all() or total <= 0:
        raise ValueError("光场能量为零或无效")
    radius, inverse = np.unique(np.asarray(radii).ravel(), return_inverse=True)
    energy = np.bincount(inverse, weights=flat)
    return radius, np.cumsum(energy) / total
