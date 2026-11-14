"""Real Qt/VTK rendering and application state smoke tests (requires desktop)."""
import pytest
import gc
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from gaussian_lab.gui import MainWindow, Job
from gaussian_lab.model import preset, load_project
from gaussian_lab.optics import simulate, scan


@pytest.fixture(scope="session")
def app():
    application = QApplication.instance() or QApplication([])
    yield application
    application.closeAllWindows()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    application.processEvents()
    gc.collect()


@pytest.fixture
def window(app):
    w = MainWindow(auto_compute=False)
    p = preset("单透镜聚焦")
    p.grid, p.samples = 128, 17
    w.fill_project(p)
    w.show()
    app.processEvents()
    w.job = Job("simulate", w.read_project())
    w.job_done(simulate(p))
    app.processEvents()
    yield w
    w.close()
    w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()
    gc.collect()


def test_render_tabs_observer_and_animation(window, app, tmp_path):
    assert window.result is not None
    assert not window.dirty
    assert window.scene.screen_actor is not None
    window.plane_slider.setValue(0)
    assert "0.00 mm" in window.plane_label.text()
    for i in range(3):
        window.tabs.setCurrentIndex(i)
        app.processEvents()
    assert window.surface_plot.ax.name == "3d"
    window.toggle_play()
    assert window.play_timer.isActive()
    window.advance_plane()
    assert window.plane_slider.value() > 0
    window.toggle_play()
    window.scene.screenshot(str(tmp_path/"scene.png"))
    assert (tmp_path/"scene.png").stat().st_size > 5000


def test_edits_save_and_export_snapshot(window, monkeypatch, tmp_path):
    old = window.result.project.waist
    window.waist.setValue(1.1)
    assert window.dirty
    assert window.result.project.waist == old
    path = tmp_path/"project.json"
    monkeypatch.setattr(window, "choose_path", lambda *a, **k: str(path))
    window.save_file()
    assert load_project(path).waist == pytest.approx(.0011)
    csv = tmp_path/"data.csv"
    monkeypatch.setattr(window, "choose_path", lambda *a, **k: str(csv))
    window.export_data()
    assert csv.is_file()
    assert load_project(tmp_path/"data.project.json").waist == old


def test_scan_gui_keeps_snapshot_and_exports(window, monkeypatch, tmp_path):
    p = window.result.project
    rows = scan(p, 0, .1, .14, 3)
    window.job = Job("scan", p, (0, .1, .14, 3))
    window.job_done(rows)
    assert window.scan_table.rowCount() == 3
    assert window.bottom.currentIndex() == 1
    assert "主场景" in window.result_state.text()
    assert window.scan_plot.figure.axes[1].get_ylim() == (0, 105)
    path = tmp_path/"scan.csv"
    monkeypatch.setattr(window, "choose_path", lambda *a, **k: str(path))
    window.export_data()
    assert (tmp_path/"scan.csv.meta.json").is_file()


def test_gui_add_remove_and_validation(window):
    window.add_element("aperture")
    assert len(window.read_project().elements) == 2
    window.table.selectRow(1)
    window.remove_element()
    assert len(window.read_project().elements) == 1
    window.table.item(0, 2).setText("0")
    with pytest.raises(ValueError):
        window.read_project()
