"""独立进程验证先建立三维预览，再首次启用 CUDA，并重复完整计算的真实启动顺序。"""
import argparse
import faulthandler
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(output, backend="auto", runs=3):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from gaussian_lab.gui import MainWindow, Job
    faulthandler.enable()
    app = QApplication.instance() or QApplication([])
    report = {"status": "running", "requested": backend, "runs": [], "cleanup_threads": [],
              "main_thread": threading.get_ident(), "errors": [], "grid": 1024}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    original = Job.release_cuda_cache

    def release(job):
        if job.cuda_fft_cache is not None:
            report["cleanup_threads"].append(threading.get_ident())
        return original(job)

    Job.release_cuda_cache = release
    window = MainWindow(display_mode="3d")
    window.backend_choice.setCurrentIndex(window.backend_choice.findData(backend))
    window.show_error = report["errors"].append
    window.show()
    state = {"started": False, "finished_result": None}
    started = time.perf_counter()

    def finish(code):
        timer.stop()
        window.close()
        report["seconds"] = time.perf_counter()-started
        report["status"] = "passed" if code == 0 else "failed"
        save()
        app.exit(code)

    def tick():
        if report["errors"]:
            finish(1)
            return
        if window.job is None or window.job.isRunning() or window.result is None:
            return
        # finished 信号的主线程回调也要处理完，才能检验缓存清理归属。
        if not window.run_button.isEnabled():
            return
        if not state["started"]:
            report["preview_grid"] = window.result.project.grid
            state["started"] = True
            save()
            window.compute()
            return
        result = window.result
        if result.provenance.get("quality") != "full" or result is state["finished_result"]:
            return
        state["finished_result"] = result
        report["runs"].append({"grid": result.project.grid, "backend": result.provenance["backend"]["used"],
                               "scene_matches": window.scene.result is result,
                               "fft_cache_released": window.job.cuda_fft_cache is None})
        save()
        if len(report["runs"]) >= runs:
            finish(0)
        else:
            window.waist.setValue(window.waist.value()+.01)
            window.compute()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(50)
    QTimer.singleShot(120000, lambda: finish(2))
    save()
    try:
        return app.exec()
    finally:
        Job.release_cuda_cache = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="验证默认三维启动计算不会闪退")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.runs <= 20:
        parser.error("重复次数须为 1—20")
    raise SystemExit(run(args.output, args.backend, args.runs))
