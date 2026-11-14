"""对照 V2.0.0、优化 CPU 与实际 CUDA，记录重复测量及数值偏差。"""
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import types
from dataclasses import asdict
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gaussian_lab.backend import select_backend, preview_project
from gaussian_lab.model import preset
from gaussian_lab.optics import simulate, SOURCE_SHA256, ALGORITHM_VERSION
import numpy as np


def baseline():
    source = subprocess.check_output(["git", "show", "v2.0.0:gaussian_lab/optics.py"], cwd=ROOT).decode("utf-8")
    module = types.ModuleType("gaussian_lab._baseline")
    module.__file__ = str(ROOT / "gaussian_lab/optics.py")
    module.__package__ = "gaussian_lab"
    sys.modules[module.__name__] = module
    exec(compile(source, "v2.0.0/optics.py", "exec"), module.__dict__)
    return module.simulate


def timed(call, count=3):
    values = []
    for _ in range(count):
        start = time.perf_counter()
        result = call()
        values.append(time.perf_counter() - start)
    return result, values


def main():
    old = baseline()
    started = time.perf_counter()
    engine = select_backend("cuda")
    probe_seconds = time.perf_counter() - started
    if engine.name != "cuda":
        raise RuntimeError("本实测要求实际 CUDA，不能把回退 CPU 算作显卡通过：" + engine.reason)
    report = {"baseline": "v2.0.0", "algorithm_version": ALGORITHM_VERSION, "source_sha256": SOURCE_SHA256,
              "platform": platform.platform(), "python": platform.python_version(), "numpy": np.__version__,
              "engine": engine.information(), "cupy": engine.xp.__version__, "probe_seconds": probe_seconds,
              "note": "同一进程内每种形状先预热，再重复三次取中位数；未清除磁盘内核缓存，不代表首次安装冷启动。计时含结果传回内存，不含界面绘制。",
              "cases": []}
    for name, grid, samples in (("单透镜聚焦", 512, 65), ("双透镜扩束", 512, 65),
                                ("光阑衍射", 512, 65), ("光阑衍射", 1024, 33)):
        p = preset(name)
        p.grid, p.samples = grid, samples
        old(p)
        simulate(p)
        warm = simulate(p, backend="cuda")
        if warm.provenance["backend"]["used"] != "cuda":
            raise RuntimeError("CUDA 在预热时回退，停止性能报告")
        before, before_time = timed(lambda: old(p))
        cpu, cpu_time = timed(lambda: simulate(p))
        gpu, gpu_time = timed(lambda: simulate(p, backend="cuda"))
        assert gpu.provenance["backend"]["used"] == "cuda"
        np.testing.assert_allclose(cpu.z, before.z, atol=1e-12)
        np.testing.assert_allclose(cpu.intensity, before.intensity, rtol=1e-5, atol=1e-7)
        np.testing.assert_allclose(cpu.r86, before.r86, atol=1e-12)
        np.testing.assert_allclose(gpu.intensity, cpu.intensity, rtol=1e-5, atol=1e-7)
        np.testing.assert_allclose(gpu.r86, cpu.r86, atol=1e-12)
        np.testing.assert_allclose(gpu.transmission, cpu.transmission, atol=1e-12)
        assert abs(gpu.theta86 - cpu.theta86) < 1e-12
        preview, preview_time = timed(lambda: simulate(preview_project(p), backend="auto"))
        row = {"project": asdict(p), "baseline_seconds": before_time, "cpu_seconds": cpu_time,
               "cuda_seconds": gpu_time, "preview_seconds": preview_time,
               "cpu_speedup": statistics.median(before_time) / statistics.median(cpu_time),
               "cuda_speedup_vs_v2": statistics.median(before_time) / statistics.median(gpu_time),
               "cuda_speedup_vs_cpu": statistics.median(cpu_time) / statistics.median(gpu_time),
               "cpu_vs_baseline_max_absolute_intensity": float(np.max(abs(cpu.intensity-before.intensity))),
               "cuda_vs_cpu_max_absolute_intensity": float(np.max(abs(cpu.intensity-gpu.intensity))),
               "max_r86_difference_m": float(np.max(abs(cpu.r86-gpu.r86))),
               "preview_project": asdict(preview.project), "actual_backend": gpu.provenance["backend"]}
        report["cases"].append(row)
        print(json.dumps({"case": name, "grid": grid, "baseline": statistics.median(before_time),
              "cpu": statistics.median(cpu_time), "cuda": statistics.median(gpu_time),
              "preview": statistics.median(preview_time)}, ensure_ascii=True), flush=True)
    destination = ROOT / "docs/acceleration-validation.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(destination))


if __name__ == "__main__":
    main()
