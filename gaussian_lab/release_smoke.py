"""由冻结可执行程序执行的冒烟断言，包含实际 Qt/VTK 场景渲染。"""
import json
from pathlib import Path
import sys
import time
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from .model import preset, save_project, load_project
from .optics import simulate, scan, export_csv
from .gui import MainWindow, Job


def run(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    window = MainWindow(auto_compute=False)
    window.show()
    app.processEvents()
    report = {"version": "0.1.0", "frozen": bool(getattr(sys, "frozen", False)), "cases": []}
    try:
        for name, slug in (("单透镜聚焦", "focus"), ("双透镜扩束", "expander"), ("光阑衍射", "diffraction")):
            p = preset(name)
            start = time.perf_counter()
            result = simulate(p)
            assert result.intensity.shape[1:] == (512, 512)
            assert result.r86.min() > 0
            assert .1 < result.transmission[-1] < 1.000001
            if slug == "focus":
                assert abs(result.reference['waist_z'] - .21971515816) < 1e-8
            if slug == "diffraction":
                assert .60 < result.transmission[-1] < .63
            window.fill_project(p)
            window.job = Job("simulate", window.read_project())
            window.job_done(result)
            window.tabs.setCurrentIndex(2)
            app.processEvents()
            window.scene.screenshot(str(output / f"{slug}-scene.png"))
            assert (output / f"{slug}-scene.png").stat().st_size > 5000
            save_project(p, output / f"{slug}.json")
            assert load_project(output / f"{slug}.json") == p
            report["cases"].append({"name": name, "seconds": time.perf_counter()-start,
                                     "transmission": float(result.transmission[-1])})
        p.grid, p.samples = 128, 17
        rows = scan(p, 0, .0006, .0012, 3)
        assert all(r["status"] == "ok" for r in rows)
        assert rows[0]["transmission"] < rows[-1]["transmission"]
        export_csv(rows, output / "scan.csv")
        window.plane_slider.setValue(0)
        window.advance_plane()
        assert window.plane_slider.value() == 1
        report.update({"scan_points": len(rows), "status": "passed"})
        (output / "smoke-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:
        report.update({"status": "failed", "error": str(exc)})
        (output / "smoke-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()
