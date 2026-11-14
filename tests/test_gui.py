"""真实 Qt/VTK 渲染与应用状态冒烟测试，需要可用桌面和图形驱动。"""
import pytest
import gc
import json
import time
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
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
    assert "横向放大 25 倍" in window.scene.toolTip()
    window.plane_slider.setValue(0)
    assert "0.00 mm" in window.plane_label.text()
    for i in range(4):
        window.tabs.setCurrentIndex(i)
        app.processEvents()
    assert window.surface_plot.ax.name == "3d"
    assert window.energy_plot.ax.get_ylim() == (0, 101)
    assert "括区宽" in window.cards[1].toolTip()
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
    metadata = json.loads((tmp_path/"data.csv.meta.json").read_text(encoding="utf-8"))
    assert metadata["project"]["waist"] == old
    assert metadata["metrics"]["theta86_rad"] == window.result.theta86
    assert metadata["convergence"] is None
    assert (tmp_path/"data.energy.csv").is_file()


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
    metadata = json.loads((tmp_path/"scan.csv.meta.json").read_text(encoding="utf-8"))
    assert metadata["metric"] == "末片透镜后粗搜索与局部细化的最小 r86；警告点需复核"


def test_gui_add_remove_and_validation(window):
    window.add_element("aperture")
    assert len(window.read_project().elements) == 2
    window.table.selectRow(1)
    window.remove_element()
    assert len(window.read_project().elements) == 1
    window.table.item(0, 2).setText("0")
    with pytest.raises(ValueError):
        window.read_project()


def test_scan_button_runs_worker_and_populates_both_tabs(window, app, monkeypatch):
    """验证单次光场计算与参数扫描是独立任务，并检查真实按钮触发链路。"""
    assert window.result is not None
    assert window.scan_rows == []
    assert window.scan_table.rowCount() == 0
    assert window.scan_plot.ax is None
    errors = []
    monkeypatch.setattr(window, 'show_error', errors.append)
    window.scan_count.setValue(3)
    window.scan_low.setValue(100)
    window.scan_high.setValue(140)
    QTest.mouseClick(window.scan_button, Qt.LeftButton)
    assert window.job.kind == 'scan'
    deadline = time.monotonic() + 15
    while (window.job.isRunning() or window.scan_table.rowCount() != 3) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)  # 显式释放全局解释器锁，使 Python 工作线程能够继续执行。
        if errors:
            break
    assert not errors
    assert not window.job.isRunning()
    assert window.scan_table.rowCount() == 3
    assert window.scan_table.columnCount() == 6
    assert window.scan_plot.ax is not None
    assert len(window.scan_plot.ax.lines[0].get_xdata()) == 3
    assert window.bottom.currentIndex() == 1
    window.bottom.setCurrentIndex(2)
    assert float(window.scan_table.item(0, 0).text()) == 100
    assert float(window.scan_table.item(2, 0).text()) == 140
    assert all(window.scan_table.item(i, 4).text() in ('ok', 'warning') for i in range(3))


def test_convergence_preserves_scene_snapshot_and_marks_its_scope(window):
    from gaussian_lab.optics import convergence
    p = window.result.project.clone()
    p.waist *= 1.2
    previous = window.result
    window.job = Job("convergence", p)
    window.job_done(convergence(p))
    assert window.result is previous
    assert "主场景仍为上次光场结果" in window.result_state.text()
    assert "焦区 r86" in window.status.text()



def test_active_energy_curve_can_be_exported(window, app, monkeypatch, tmp_path):
    window.tabs.setCurrentIndex(3)
    app.processEvents()
    path = tmp_path / "energy.png"
    monkeypatch.setattr(window, "choose_path", lambda *args, **kwargs: str(path))
    window.export_plot()
    assert path.is_file() and path.stat().st_size > 5000



def test_parameters_remain_accessible_at_minimum_window_height(window, app):
    window.resize(1180, 780)
    app.processEvents()
    assert window.height() <= 800
    window.parameter_scroll.ensureWidgetVisible(window.convergence_button)
    app.processEvents()
    scroll = window.parameter_scroll.verticalScrollBar()
    assert scroll.value() > 0
    viewport = window.parameter_scroll.viewport()
    position = window.convergence_button.mapTo(viewport, window.convergence_button.rect().center())
    assert viewport.rect().contains(position)



def test_all_plot_types_export_white_images_without_switching_tabs(window, app, monkeypatch, tmp_path):
    """逐类检查导出、白底和结果快照，包含未打开过的分析标签。"""
    import numpy as np
    from PIL import Image
    from gaussian_lab.theme import INTENSITY_CMAP
    p = window.result.project
    rows = scan(p, 0, .1, .14, 3)
    window.job = Job("scan", p, (0, .1, .14, 3))
    window.job_done(rows)
    window.tabs.setCurrentIndex(0)
    window.plane_slider.setValue(0)
    window.waist.setValue(1.2)
    errors = []
    monkeypatch.setattr(window, "show_error", errors.append)
    for key in ("spot", "profile", "surface", "energy", "beam", "scan"):
        window.export_target.setCurrentIndex(window.export_target.findData(key))
        path = tmp_path / (key + ".png")
        monkeypatch.setattr(window, "choose_path", lambda *args, selected=path, **kwargs: str(selected))
        window.export_plot()
        assert path.is_file(), (key, errors)
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            for point in ((0, 0), (image.width-1, 0), (0, image.height-1), (image.width-1, image.height-1)):
                assert rgba.getpixel(point) == (255, 255, 255, 255), key
            pixels = np.array(rgba)
            for edge in (pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]):
                assert np.all(edge == 255), (key, "文字或图形不应触及图片边界")
        assert window.tabs.currentIndex() == 0
    assert not errors
    np.testing.assert_allclose(INTENSITY_CMAP(0)[:3], [1, 1, 1])
    np.testing.assert_allclose(window.scene.background_color.float_rgb, [1, 1, 1])
    np.testing.assert_allclose(window.profile_plot.figure.get_facecolor(), [1, 1, 1, 1])
    intensity = window.result.intensity[0]
    np.testing.assert_allclose(window.profile_plot.ax.lines[0].get_ydata(), intensity[p.grid//2] / intensity.max())
    assert window.result.project.waist == p.waist


@pytest.mark.parametrize("suffix", ["svg", "pdf"])
def test_white_vector_plot_exports(window, monkeypatch, tmp_path, suffix):
    path = tmp_path / ("energy." + suffix)
    window.export_target.setCurrentIndex(window.export_target.findData("energy"))
    monkeypatch.setattr(window, "choose_path", lambda *args, **kwargs: str(path))
    window.export_plot()
    assert path.is_file() and path.stat().st_size > 1000
    if suffix == "svg":
        text = path.read_text(encoding="utf-8")
        assert "#ffffff" in text and "<svg" in text
    else:
        assert path.read_bytes().startswith(b"%PDF")


def test_plot_export_reports_missing_scan_and_cancel_does_not_write(window, monkeypatch, tmp_path):
    errors = []
    monkeypatch.setattr(window, "show_error", errors.append)
    window.export_target.setCurrentIndex(window.export_target.findData("scan"))
    window.export_plot()
    assert errors == ["请先完成参数扫描"]
    window.export_target.setCurrentIndex(window.export_target.findData("profile"))
    monkeypatch.setattr(window, "choose_path", lambda *args, **kwargs: "")
    window.export_plot()
    assert not list(tmp_path.iterdir())
