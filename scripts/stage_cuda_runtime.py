"""整理 V3 随包 CUDA 运行组件和原始许可，生成逐文件摘要，不收集系统驱动。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

PACKAGES = ("cupy_cuda12x-14.2.0.dist-info", "cuda_pathfinder-1.8.3.dist-info",
            "nvidia_cuda_runtime_cu12-12.9.79.dist-info", "nvidia_cuda_nvrtc_cu12-12.9.86.dist-info",
            "nvidia_cufft_cu12-11.4.1.4.dist-info", "nvidia_nvjitlink_cu12-12.9.86.dist-info")
HEADERS = {"nvrtc.h", "cuda_occupancy.h", "cuda_fp16.h", "cuda_fp16.hpp", "cuda_bf16.h", "cuda_bf16.hpp",
           "cuda_fp8.h", "cuda_fp8.hpp", "cuda_fp6.h", "cuda_fp6.hpp", "cuda_fp4.h", "cuda_fp4.hpp",
           "crt/host_defines.h", "cuComplex.h", "cuda_awbarrier_helpers.h", "cuda_awbarrier_primitives.h",
           "cuda_wbarrier.h", "cuda_pipeline_helpers.h", "cuda_pipeline_primitives.h", "cuda_pipeline.h",
           "cuda_runtime_api.h", "cuda.h", "device_types.h", "vector_functions.h", "vector_types.h"}


def stage(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if target.exists():
        raise RuntimeError("CUDA 暂存目录已存在，请指定新的输出目录")
    target.mkdir(parents=True)
    shutil.copy2(Path(__file__).resolve().parents[1] / "packaging/cuda-headers-wheel.json", target / "CUDA-HEADERS.json")
    for name in ("cupy", "cupyx", "cupy_backends", "cuda") + PACKAGES:
        shutil.copytree(source / name, target / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (target / "nvidia").mkdir()
    # 新版 NVIDIA 轮子可使用 PEP 420 命名空间包，没有顶层初始化文件。
    if (source / "nvidia/__init__.py").is_file():
        shutil.copy2(source / "nvidia/__init__.py", target / "nvidia/__init__.py")
    for component in ("cuda_runtime", "cuda_nvrtc", "cufft", "nvjitlink"):
        root = source / "nvidia" / component
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if path.suffix.lower() == ".dll" or path.name == "__init__.py" or (
                str(rel).replace("\\", "/").removeprefix("include/") in HEADERS):
                dest = target / "nvidia" / component / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
    files = [{"path": path.relative_to(target).as_posix(), "bytes": path.stat().st_size,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(target.rglob("*")) if path.is_file()]
    manifest = {"cupy": "14.2.0", "cuda": "12.9", "python_abi": "cp310-win_amd64",
                "packages": list(PACKAGES), "files": files}
    (target / "RUNTIME-MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(files), "bytes": sum(row["bytes"] for row in files)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从已安装的固定 CUDA 轮子整理应用私有运行组件")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    stage(args.source, args.target)
