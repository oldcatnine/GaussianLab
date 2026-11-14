"""可选 CUDA 后端；CPU 不导入显卡依赖，设备故障可回退且保留原因。"""
from dataclasses import dataclass
from functools import lru_cache
import importlib
import os
from pathlib import Path
import sys
import site
import tempfile
import json
import hashlib
import shutil
import uuid
import zipfile
import numpy as np
from scipy import fft

_cuda_failure = ""


def bundled_runtime(source, cache_root=None):
    """中文发行路径下将随包运行库复制到独立缓存；按内容摘要隔离且不修改第三方库。"""
    source = Path(source).resolve()
    manifest = source / "RUNTIME-MANIFEST.json"
    key = hashlib.sha256(manifest.read_bytes()).hexdigest()[:16]
    root = Path(cache_root or os.environ.get("GAUSSIANLAB_CUDA_CACHE", str(Path(tempfile.gettempdir()) / "GaussianLab" / "runtimes")))
    if not str(root.resolve()).isascii():
        raise RuntimeError("CUDA 运行库需要英文路径，请解压至英文目录或设置 GAUSSIANLAB_CUDA_CACHE")
    target = root / key
    marker = target / ".ready"
    if marker.is_file():
        return target
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / (key + "." + uuid.uuid4().hex[:8])
    shutil.copytree(source, temporary)
    rows = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    for row in rows:
        path = temporary / row["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise RuntimeError("随包 CUDA 运行组件校验失败：" + row["path"])
    (temporary / ".ready").write_text(key, encoding="ascii")
    try:
        temporary.rename(target)
    except FileExistsError:
        if not marker.is_file():
            raise
        # 并行进程先完成缓存时，保留已完成缓存，清理本进程创建的独立临时目录。
        if temporary.resolve().parent == root.resolve() and temporary.name.startswith(key + "."):
            shutil.rmtree(temporary)
    return target


def ensure_cuda_headers(runtime):
    """从固定官方轮子补齐本机编译头文件；摘要验证后仅提取应用私有目录。"""
    runtime = Path(runtime)
    marker = runtime / ".headers-ready"
    if marker.is_file() and (runtime / "nvidia/cuda_runtime/include/cuda_runtime.h").is_file():
        return
    record = json.loads((runtime / "CUDA-HEADERS.json").read_text(encoding="utf-8"))
    if not record["url"].startswith("https://files.pythonhosted.org/") or record["bytes"] > 16 * 1024**2:
        raise RuntimeError("CUDA 头文件官方来源配置无效")
    import requests
    wheel = runtime / ("headers-" + uuid.uuid4().hex[:8] + ".whl")
    try:
        with requests.get(record["url"], stream=True, timeout=(10, 30)) as response:
            response.raise_for_status()
            size = 0
            with wheel.open("wb") as stream:
                for block in response.iter_content(1024**2):
                    size += len(block)
                    if size > record["bytes"]:
                        raise RuntimeError("CUDA 头文件下载大小超出固定清单")
                    stream.write(block)
        if wheel.stat().st_size != record["bytes"] or hashlib.sha256(wheel.read_bytes()).hexdigest() != record["sha256"]:
            raise RuntimeError("CUDA 头文件下载摘要不匹配")
        with zipfile.ZipFile(wheel) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or not entry.filename.startswith("nvidia/cuda_runtime/include/"):
                    continue
                dest = (runtime / entry.filename).resolve()
                if not dest.is_relative_to(runtime.resolve()):
                    raise RuntimeError("CUDA 轮子包含目录越界路径")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(entry))
        marker.write_text(record["sha256"], encoding="ascii")
    finally:
        wheel.unlink(missing_ok=True)


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
        if getattr(sys, "frozen", False):
            packaged = Path(sys._MEIPASS) / "cuda_runtime"
            runtime = str(bundled_runtime(packaged)) if packaged.is_dir() else ""
            if runtime:
                ensure_cuda_headers(runtime)
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
