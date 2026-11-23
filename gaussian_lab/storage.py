"""完整 float32 强度体积的 RAM 或磁盘映射存储；按批写回以减少常驻页。"""
from pathlib import Path
import shutil
import tempfile
import weakref
import numpy as np


def _cleanup(path, mappings):
    """最后一个结果/切片引用释放后关闭映射并清理本任务私有文件。"""
    for mapping in mappings:
        if not mapping.closed:
            mapping.close()
    try:
        path.unlink(missing_ok=True)
        path.parent.rmdir()
    except OSError:
        pass


class _Owner:
    def __init__(self, path):
        self.path = path
        self.mappings = []
        self.finalizer = weakref.finalize(self, _cleanup, path, self.mappings)


class DiskIntensity(np.memmap):
    """切片保留文件所有者；普通算术副本不延长原始磁盘文件的生命周期。"""

    def __array_finalize__(self, obj):
        super().__array_finalize__(obj)
        self._owner = getattr(obj, "_owner", None) if self._mmap is not None else None


def allocate_intensity(project):
    """验证空间后创建私有映射；保留完整网格与轴向面，兼容原数组接口。"""
    shape = (len(project.sampling_positions()) + 1, project.grid, project.grid)
    if project.selected_storage() == "ram":
        return np.empty(shape, dtype=np.float32)
    directory = Path(tempfile.mkdtemp(prefix="GaussianLab-field-"))
    path = directory / "intensity.bin"
    try:
        required = project.result_storage_bytes()
        free = shutil.disk_usage(directory).free
        if required + 256 * 1024**2 > free:
            raise ValueError(f"磁盘空间不足：结果需要 {required/1024**3:.2f} GiB，当前可用 {free/1024**3:.2f} GiB；请减少采样")
        owner = _Owner(path)
        result = DiskIntensity(path, dtype=np.float32, mode="w+", shape=shape)
        result._owner = owner
        owner.mappings.append(result._mmap)
        return result
    except Exception:
        if path.exists():
            path.unlink(missing_ok=True)
        directory.rmdir()
        raise


def checkpoint_intensity(images, project, completed, force=False):
    """仅在尚未发布的求解数组上写回并重映射，不在结果发布后关闭其活动视图。"""
    if not isinstance(images, DiskIntensity):
        return images
    planes = max(1, project.resident_result_bytes() // (project.grid**2 * 4))
    if not force and completed % planes:
        return images
    owner, shape = images._owner, images.shape
    images.flush()
    images._mmap.close()
    result = DiskIntensity(owner.path, dtype=np.float32, mode="r+", shape=shape)
    result._owner = owner
    owner.mappings.append(result._mmap)
    return result
