"""可选 CUDA 后端；CPU 不导入显卡依赖，设备故障可回退且保留原因。"""
from dataclasses import dataclass
from functools import lru_cache
import importlib
import os
from pathlib import Path
import sys
import site
import tempfile
import numpy as np
from scipy import fft

_cuda_failure = ""


@dataclass
class Backend:
    xp: object = np
    fft: object = fft
    name: str = "cpu"
    device: str = "CPU"
    requested: str = "cpu"
    reason: str = "兼容 CPU 计算"

    def host(self, array):
        return np.asarray(array) if self.name == "cpu" else self.xp.asnumpy(array)

    def information(self):
        return {"requested": self.requested, "used": self.name, "device": self.device,
                "reason": self.reason, "precision": "complex128 / float64"}


def array_module(value):
    return importlib.import_module("cupy") if type(value).__module__.split(".")[0] == "cupy" else np


@lru_cache(maxsize=1)
def cuda_probe():
    """在工作线程中首次检测设备及 FFT；缓存失败，避免每次改参反复初始化。"""
    try:
        cache = Path(tempfile.gettempdir()) / "GaussianLab" / "cupy-cache"
        cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("CUPY_CACHE_DIR", str(cache))
        default = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GaussianLab" / "cuda-v2-dev"
        runtime = os.environ.get("GAUSSIANLAB_CUDA_PATH", str(default) if default.is_dir() else "")
        if runtime:
            path = str(Path(runtime).resolve())
            if path not in sys.path:
                sys.path.append(path)
            # 注册独立安装目录，使 NVIDIA 官方路径查找器能发现随包头文件和动态库。
            if path not in site.PREFIXES:
                site.PREFIXES.append(path)
        cp = importlib.import_module("cupy")
        if cp.cuda.runtime.getDeviceCount() < 1:
            raise RuntimeError("没有 NVIDIA CUDA 设备")
        value = cp.arange(64, dtype=cp.float64).reshape(8, 8).astype(cp.complex128)
        restored = cp.fft.ifft2(cp.fft.fft2(value))
        if float(cp.max(cp.abs(restored - value))) > 1e-10:
            raise RuntimeError("CUDA FFT 自检失败")
        cp.cuda.get_current_stream().synchronize()
        name = cp.cuda.runtime.getDeviceProperties(0)["name"]
        return cp, name.decode() if isinstance(name, bytes) else str(name), ""
    except Exception as exc:
        return None, "CPU", f"{type(exc).__name__}: {exc}"


def select_backend(requested="cpu", grid=512):
    if requested not in ("cpu", "auto", "cuda"):
        raise ValueError("后端须为 cpu、auto 或 cuda")
    if requested == "cpu":
        return Backend(requested=requested)
    if os.environ.get("GAUSSIANLAB_DISABLE_CUDA") == "1":
        return Backend(requested=requested, reason="CUDA 已禁用，使用 CPU")
    if _cuda_failure:
        return Backend(requested=requested, reason="本会话 CUDA 执行失败，使用 CPU；" + _cuda_failure)
    if requested == "auto" and grid < 512:
        return Backend(requested=requested, reason="小网格优先 CPU，避免传输及初始化开销")
    cp, device, error = cuda_probe()
    if cp is None:
        return Backend(requested=requested, reason="CUDA 不可用，回退 CPU；" + error)
    return Backend(cp, cp.fft, "cuda", device, requested, "CUDA 光场与 FFT")


def invalidate_cuda(error):
    """本进程设备执行失败后缓存故障，避免后续自动任务重复碰撞。"""
    global _cuda_failure
    _cuda_failure = f"{type(error).__name__}: {error}"


def preview_project(project):
    """预览保留物理输入，限制网格和轴向点数；不代替完整精度结果。"""
    p = project.clone()
    p.grid = min(p.grid, 256)
    p.samples = min(p.samples, 33)
    p.focus_refinement = 0
    return p.validate()
