"""生成焦区、独立衍射、孔径取舍和进程峰值内存的可复现验证记录。"""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from gaussian_lab.model import Project, Element
from gaussian_lab.optics import (simulate, convergence, result_summary, coordinates,
                                 encircled_radius, output_gaussian, ALGORITHM_VERSION)


def compare_lightpipes(project):
    """用 LightPipes 卷积传播独立对照；只支持本验证所需的入口束腰案例。"""
    import LightPipes as lp
    if lp.__version__ != "2.1.5":
        raise ValueError("独立对照要求 LightPipes==2.1.5")
    if project.waist_z != 0:
        raise ValueError("独立对照当前仅接受入口为束腰的案例")
    p = project.clone()
    result = simulate(p)
    x, r2 = coordinates(p)
    value = lp.Begin(p.window, p.wavelength, p.grid)
    np.testing.assert_allclose(value.xvalues, x, rtol=0, atol=1e-15)
    # Begin 保持非解析场；直接赋予标准高斯振幅，避免透镜调用高斯快捷分支。
    value.field = np.exp(-r2 / p.waist**2).astype(complex)
    input_energy = float(np.sum(abs(value.field)**2))
    previous = 0.0
    for element in p.ordered():
        value = lp.Fresnel(value, element.z - previous)
        value = lp.Lens(value, element.value) if element.kind == "lens" else lp.CircAperture(value, element.value / 2)
        previous = element.z
    value = lp.Fresnel(value, p.length - previous)
    external = lp.Intensity(value)
    internal = result.intensity[-1].astype(float)
    a, b = internal / internal.sum(), external / external.sum()
    r_external = encircled_radius(external, np.sqrt(r2))
    return {"project": asdict(p), "lightpipes_version": lp.__version__, "method": "LightPipes.Fresnel 卷积传播",
            "normalized_intensity_l1": float(abs(a - b).sum()),
            "r86_relative_difference": float(abs(result.r86[-1] - r_external) / r_external),
            "transmission_absolute_difference": float(abs(result.transmission[-1] - external.sum() / input_energy)),
            "internal_r86_m": float(result.r86[-1]), "external_r86_m": r_external,
            "internal_transmission": float(result.transmission[-1]),
            "external_transmission": float(external.sum() / input_energy), "warnings": result.warnings,
            "profile_x_m": x[::max(1, p.grid // 128)].tolist(),
            "internal_profile": (internal[p.grid // 2] / internal.max())[::max(1, p.grid // 128)].tolist(),
            "external_profile": (external[p.grid // 2] / external.max())[::max(1, p.grid // 128)].tolist()}


def memory_peak():
    """读取当前进程峰值工作集；该值包括解释器、依赖和所有临时分配。"""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("peak", "working", "quota_peak_paged", "quota_paged",
                                                   "quota_peak_nonpaged", "quota_nonpaged", "pagefile", "peak_pagefile")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.peak)
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def memory_case(grid):
    p = Project(grid=grid, samples=33)
    before = memory_peak()
    start = time.perf_counter()
    result = simulate(p)
    return {"grid": grid, "samples": p.samples, "actual_planes": len(result.z),
            "seconds": time.perf_counter() - start, "import_peak_bytes": before,
            "process_peak_bytes": memory_peak(), "result_array_bytes": result.intensity.nbytes,
            "note": "独立子进程的实际峰值工作集；结果体积限制不等于进程内存限制"}


def main():
    parser = argparse.ArgumentParser(description="执行数值对照与工程验证，输出 JSON 和孔径分析图")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/numerical-validation-v2.json")
    parser.add_argument("--memory-case", type=int, choices=(256, 512, 1024))
    args = parser.parse_args()
    if args.memory_case:
        print(json.dumps(memory_case(args.memory_case), ensure_ascii=True))
        return
    import LightPipes
    report = {"date": datetime.now().astimezone().isoformat(), "algorithm_version": ALGORITHM_VERSION,
              "python": platform.python_version(), "platform": platform.platform(),
              "processor": platform.processor(), "numpy": np.__version__, "lightpipes": LightPipes.__version__}
    short = Project(grid=1024, window=.003, samples=17, length=.18, elements=[Element("lens", .1, .04)])
    report["short_focus"] = result_summary(simulate(short))
    coarse = short.clone()
    coarse.focus_refinement = 0
    report["short_focus_coarse"] = result_summary(simulate(coarse))
    reference = np.sqrt(-np.log(.14)/2) * output_gaussian(short)["waist"]
    report["short_focus_reference_r86_m"] = float(reference)
    report["short_focus_relative_error"] = abs(report["short_focus"]["focus_r86_m"] / reference - 1)
    # 低于高网格资源上限；四组计算一次只保留指标摘要。
    report["convergence"] = convergence(Project(grid=256, samples=33))
    report["independent"] = []
    for grid in (512, 1024):
        for name, elements in (("自由传播", []), ("单透镜", [Element("lens", .1, .12)]),
                               ("光阑与透镜", [Element("aperture", .03, .0009, "A1"), Element("lens", .1, .12)])):
            p = Project(name=name, grid=grid, samples=17, window=.004, length=.22, elements=elements)
            report["independent"].append(compare_lightpipes(p))
    report["aperture_tradeoff"] = []
    for diameter in np.linspace(.45e-3, 1.35e-3, 7):
        p = Project(grid=512, samples=33, window=.004, length=.28, waist=.65e-3,
                    elements=[Element("aperture", .06, float(diameter), "A1"), Element("lens", .1, .12)])
        summary = result_summary(simulate(p))
        summary["aperture_diameter_m"] = float(diameter)
        fine = p.clone()
        fine.grid = 1024
        fine.samples = 65
        fine.focus_refinement = 3
        summary["refined"] = result_summary(simulate(fine))
        summary["refined_focus_r86_relative_change"] = abs(summary["refined"]["focus_r86_m"] / summary["focus_r86_m"] - 1)
        summary["refined_theta86_relative_change"] = abs(summary["refined"]["theta86_rad"] / summary["theta86_rad"] - 1)
        report["aperture_tradeoff"].append(summary)
    report["memory"] = []
    for grid in (256, 512, 1024):
        run = subprocess.run([sys.executable, str(Path(__file__)), "--memory-case", str(grid)],
                             capture_output=True, text=True, check=True)
        report["memory"].append(json.loads(run.stdout))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    rows = report["aperture_tradeoff"]
    diameters = [row["aperture_diameter_m"] * 1e3 for row in rows]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
    for ax, key, scale, ylabel in zip(axes, ("focus_r86_m", "transmission", "theta86_rad"),
                                     (1e6, 100, 1e3), ("最小 r86 / μm", "透过率 / %", "θ86 / mrad")):
        ax.plot(diameters, [row[key] * scale for row in rows], "o-", label="512 网格 / 33 点")
        ax.plot(diameters, [row["refined"][key] * scale for row in rows], "s--", label="1024 网格 / 65 点")
        ax.legend(fontsize=8)
        ax.set(xlabel="光阑直径 / mm", ylabel=ylabel)
        ax.grid(alpha=.25)
    fig.suptitle("光阑孔径取舍：有限网格数值实验与加密对照")
    fig.savefig(args.output.with_suffix(".png"), dpi=180)
    plt.close(fig)
    print(json.dumps({"output": str(args.output), "short_focus_error": report["short_focus_relative_error"],
                      "maximum_external_l1": max(row["normalized_intensity_l1"] for row in report["independent"]),
                      "memory_mib": [round(row["process_peak_bytes"] / 1024**2, 1) for row in report["memory"]]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
