"""无需初始化 CUDA 的内存规划与本机 RAM 读取；估算区间不构成分配保证。"""
import ctypes
import os
import sys


def estimate_memory(project):
    """结果体积精确按槽位计算；工作区按复场、缓存频谱及临时数组留出经验余量。"""
    pixels = project.grid**2
    segments = 1 + sum(1 for e in project.elements if e.enabled)
    total_result = project.result_storage_bytes()
    result = project.resident_result_bytes()
    # 每区段保留 complex128 场与频谱；额外 256 B/像素覆盖坐标、排序与 FFT 等工作区。
    work = pixels * (32 * segments + 256)
    return {"result_bytes": total_result, "resident_result_bytes": result,
            "disk_bytes": total_result if project.selected_storage() == "disk" else 0,
            "storage_mode": project.selected_storage(), "allocated_planes": len(project.sampling_positions()) + 1,
            "cpu_increment_low_bytes": result + work, "cpu_increment_high_bytes": result + 2 * work,
            "cuda_host_low_bytes": result + 32 * pixels, "cuda_host_high_bytes": result + 64 * pixels,
            "cuda_device_low_bytes": work, "cuda_device_high_bytes": 2 * work,
            "note": "结果含焦面槽位；磁盘模式按批重映射但 OS 文件缓存仍可占 RAM；工作区为估算，不含既有进程、A/B和绘图"}


def system_memory():
    """读取物理内存总量、当前可用 RAM 与进程工作集；失败返回未知，不影响计算。"""
    info = {"total_bytes": None, "available_bytes": None, "process_bytes": None}
    try:
        if sys.platform == "win32":
            from ctypes import wintypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD)] + [
                    (name, ctypes.c_ulonglong) for name in
                    ("total", "available", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            if kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
                info.update(total_bytes=int(status.total), available_bytes=int(status.available))

            class ProcessCounters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                    (name, ctypes.c_size_t) for name in
                    ("peak_working", "working", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]

            counters = ProcessCounters()
            counters.cb = ctypes.sizeof(counters)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
            if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                info["process_bytes"] = int(counters.working)
        elif hasattr(os, "sysconf"):
            page = os.sysconf("SC_PAGE_SIZE")
            info.update(total_bytes=page * os.sysconf("SC_PHYS_PAGES"),
                        available_bytes=page * os.sysconf("SC_AVPHYS_PAGES"))
    except (OSError, ValueError, AttributeError):
        pass
    return info


def format_memory(value):
    """以二进制单位显示估计容量，无法读取时明确标记未知。"""
    if value is None:
        return "未知"
    return f"{value / 1024**3:.2f} GiB" if value >= 1024**3 else f"{value / 1024**2:.1f} MiB"
