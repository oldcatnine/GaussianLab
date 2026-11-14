"""在真实 Qt/VTK 窗口中验证连续改参、CUDA 预览、完整计算与缓存。"""
import json
import gc
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QTimer, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from gaussian_lab.gui import MainWindow
from gaussian_lab.model import preset


def wait(app, condition, timeout=60):
    deadline = time.perf_counter() + timeout
    while not condition() and time.perf_counter() < deadline:
        app.processEvents()
        time.sleep(.005)
    app.processEvents()
    if not condition():
        raise TimeoutError("真实窗口验证超时")


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(auto_compute=False)
    errors = []
    window.show_error = errors.append
    heartbeats = []
    heartbeat = QTimer()
    heartbeat.setInterval(50)
    heartbeat.timeout.connect(lambda: heartbeats.append(time.perf_counter()))
    window.show()
    window.fill_project(preset("光阑衍射"))
    window.backend_choice.setCurrentIndex(window.backend_choice.findData("cuda"))
    app.processEvents()
    heartbeat.start()
    try:
        window.auto_preview.setChecked(True)
        for value in (.68, .72, .76):
            window.waist.setValue(value)
            app.processEvents()
            time.sleep(.04)
        start = time.perf_counter()
        wait(app, lambda: window.result is not None and abs(window.result.project.waist - .00076) < 1e-14 and not window.job.isRunning())
        preview_seconds = time.perf_counter() - start
        preview = window.result
        assert preview.provenance["backend"]["used"] == "cuda"
        assert preview.provenance["quality"] == "preview"
        assert preview.project.grid == 256 and preview.project.focus_refinement == 0
        window.waist.setValue(.77)
        start = time.perf_counter()
        wait(app, lambda: abs(window.result.project.waist - .00077) < 1e-14 and not window.job.isRunning())
        warm_preview_seconds = time.perf_counter() - start
        start = time.perf_counter()
        window.compute()
        wait(app, lambda: window.job.kind == "simulate" and not window.job.isRunning())
        full_seconds = time.perf_counter() - start
        assert window.result.project.grid == 512 and window.result.project.focus_refinement == 2
        assert window.result.provenance["backend"]["used"] == "cuda"
        start = time.perf_counter()
        window.compute()
        wait(app, lambda: not window.job.isRunning())
        cache_seconds = time.perf_counter() - start
        assert window.job.cache_hit
        window.tabs.setCurrentIndex(3)
        app.processEvents()
        image = ROOT / "docs/assets/cuda-preview-desktop.png"
        if not window.grab().save(str(image)):
            raise RuntimeError("窗口截图保存失败")
        assert not errors, errors
        report = {"backend": window.result.provenance["backend"], "preview_grid": preview.project.grid,
                  "last_edit_to_preview_seconds": preview_seconds, "full_click_to_display_seconds": full_seconds,
                  "warm_edit_to_preview_seconds": warm_preview_seconds,
                  "cached_click_to_display_seconds": cache_seconds, "heartbeat_count": len(heartbeats),
                  "max_heartbeat_gap_seconds": max((b-a for a, b in zip(heartbeats, heartbeats[1:])), default=None),
                  "errors": errors, "status": "passed", "screenshot": "assets/cuda-preview-desktop.png",
                  "note": "真实窗口计时含 400ms 防抖、计算、信号处理和场景/图表更新；不是纯内核计时，首次 CUDA 可能含初始化。"}
        (ROOT / "docs/interaction-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=True))
    finally:
        heartbeat.stop()
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()
        gc.collect()


if __name__ == "__main__":
    main()
