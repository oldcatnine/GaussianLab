"""生成可复现的数值记录和实际 Qt/VTK 场景截图证据。"""
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gaussian_lab.model import preset, save_project
from gaussian_lab.optics import simulate, convergence


def main():
    from gaussian_lab.gui import MainWindow, Job
    from PySide6.QtWidgets import QApplication
    import numpy, scipy, PySide6, pyvista, pyvistaqt
    app = QApplication.instance() or QApplication([])
    window = MainWindow(auto_compute=False, display_mode="3d")
    window.show()
    app.processEvents()
    assets = ROOT / "docs/assets"
    assets.mkdir(exist_ok=True)
    report = {"date": "2026-11-14", "python": platform.python_version(), "platform": platform.platform(),
              "versions": {"numpy": numpy.__version__, "scipy": scipy.__version__, "PySide6": PySide6.__version__,
                           "pyvista": pyvista.__version__, "pyvistaqt": pyvistaqt.__version__}, "cases": []}
    for name, slug in (("单透镜聚焦", "focus"), ("双透镜扩束", "expander"), ("光阑衍射", "diffraction")):
        p = preset(name)
        start = time.perf_counter()
        result = simulate(p)
        elapsed = time.perf_counter() - start
        k = result.focus_index
        report["cases"].append({"name": name, "grid": p.grid, "samples": len(result.z), "seconds": elapsed,
            "reference": result.reference, "min_r86_m": float(result.r86[k]), "focus_z_m": float(result.z[k]),
            "transmission": float(result.transmission[-1]), "theta86_rad": result.theta86,
            "warnings": result.warnings})
        save_project(p, assets / f"{slug}.json")
        window.fill_project(p)
        window.job = Job("simulate", window.read_project())
        window.job_done(result)
        if slug == "diffraction":
            window.log_scale.setChecked(True)
        app.processEvents()
        window.grab().save(str(assets / f"{slug}-desktop.png"))
        window.scene.screenshot(str(assets / f"{slug}-scene.png"))
    p = preset("单透镜聚焦")
    p.grid, p.samples = 256, 33
    report["endpoint_convergence"] = convergence(p)
    (ROOT / "docs/validation-v0.1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    window.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
