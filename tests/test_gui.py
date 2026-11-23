"""真实 Qt/VTK 渲染与应用状态冒烟测试，需要可用桌面和图形驱动。"""
import pytest
import gc
import json
import time
import numpy as np
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
    w = MainWindow(auto_compute=False, display_mode="3d")
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


def wait_until(app, predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    app.processEvents()
    assert predicate()


def test_auto_preview_coalesces_edits_and_reuses_identical_result(window, app, monkeypatch):
    errors = []
    monkeypatch.setattr(window, "show_error", errors.append)
    window.auto_preview.setChecked(True)
    for value in (.6, .7):
        window.waist.setValue(value)
    window.waist.lineEdit().setFocus()
    window.waist.lineEdit().selectAll()
    QTest.keyClicks(window.waist.lineEdit(), "0.8")
    revision = window.revision
    wait_until(app, lambda: window.result.project.waist == .0008 and not window.job.isRunning())
    assert window.job.revision == revision and window.job.kind == "preview"
    assert "快速预览" in window.result_state.text()
    assert window.result.provenance["quality"] == "preview"
    window.compute()
    wait_until(app, lambda: window.job.kind == "simulate" and not window.job.isRunning())
    assert "完整计算" in window.result_state.text()
    window.compute()
    wait_until(app, lambda: not window.job.isRunning())
    assert window.job.cache_hit and "复用缓存" in window.result_state.text()
    assert not errors


def test_late_preview_cannot_overwrite_newer_inputs(window):
    previous = window.result
    old = window.read_project()
    revision = window.revision
    window.waist.setValue(.9)
    window.job = Job("preview", old, revision=revision)
    window.job_done(simulate(old))
    assert window.result is previous
    assert window.dirty


def test_running_preview_is_cancelled_and_only_latest_inputs_are_presented(window, app, monkeypatch):
    import gaussian_lab.gui as gui
    import threading
    entered = threading.Event()
    release = threading.Event()
    original = gui.simulate
    def delayed(p, cancel, progress, backend):
        if not entered.is_set():
            entered.set()
            release.wait(5)
        return original(p, cancel, progress, backend=backend)
    monkeypatch.setattr(gui, "simulate", delayed)
    window.auto_preview.setChecked(True)
    window.request_preview()
    try:
        wait_until(app, entered.is_set)
        old = window.job
        window.waist.setValue(.85)
        assert old.cancel.is_set()
    finally:
        release.set()
    wait_until(app, lambda: window.result.project.waist == .00085 and not window.job.isRunning())
    assert window.job is not old and window.job.revision == window.revision


def test_invalid_auto_input_waits_without_dialog_and_can_be_disabled(window, app, monkeypatch):
    errors = []
    monkeypatch.setattr(window, "show_error", errors.append)
    window.auto_preview.setChecked(True)
    window.table.item(0, 2).setText("")
    window.request_preview()
    assert "等待有效参数" in window.status.text()
    assert not errors
    window.auto_preview.setChecked(False)
    assert not window.preview_timer.isActive() and not window.pending_preview


def test_observer_reuses_beam_axes_and_unchanged_scene_plane(window):
    axes = window.beam_plot.ax
    window.plane_slider.setValue(0)
    assert window.beam_plot.ax is axes
    actor = window.scene.screen_actor
    window.draw_plane()
    assert window.scene.screen_actor is actor


def test_source_edits_reuse_scene_geometry_and_preserve_camera(window):
    camera = np.array(list(window.scene.camera_position), dtype=float)
    p = window.result.project.clone()
    p.waist *= 1.2
    p.focus_refinement = 0
    first = simulate(p)
    window.scene.set_result(first)
    actor = window.scene.actors["energy_envelope"]
    old_points = window.scene.envelope_meshes[0][0].points.copy()
    p.waist *= 1.2
    window.scene.set_result(simulate(p))
    assert window.scene.actors["energy_envelope"] is actor
    assert not np.array_equal(old_points, window.scene.envelope_meshes[0][0].points)
    np.testing.assert_allclose(list(window.scene.camera_position), camera)


def test_preview_vector_export_carries_quality_label(window, app, monkeypatch, tmp_path):
    window.auto_preview.setChecked(True)
    window.request_preview()
    wait_until(app, lambda: window.result.provenance.get("quality") == "preview" and not window.job.isRunning())
    target = tmp_path / "preview.svg"
    def choose_while_new_result_arrives(*args, **kwargs):
        p = window.read_project()
        p.grid = 256
        window.job = Job("simulate", p)
        window.job_done(simulate(p))
        return str(target)
    monkeypatch.setattr(window, "choose_path", choose_while_new_result_arrives)
    window.export_target.setCurrentIndex(window.export_target.findData("profile"))
    window.export_plot()
    exported = target.read_text(encoding="utf-8")
    assert "快速预览" in exported and "N=128" in exported
    assert window.result.project.grid == 256


def test_comparison_pins_full_result_and_exports_joint_scale(window, app, monkeypatch, tmp_path):
    window.pin_baseline()
    a = window.result
    window.table.item(0, 5).setText("0.8")
    assert window.read_project().elements[0].clear_diameter == pytest.approx(.0008)
    window.compare_results()
    assert window.comparison is None
    window.compute()
    deadline = time.monotonic() + 10
    while not window.run_button.isEnabled() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert window.run_button.isEnabled()
    assert window.baseline is a and window.result is not a
    window.compare_results()
    first, i, second, j, _ = window.comparison
    assert first.z[i] == pytest.approx(second.z[j], abs=1e-12)
    assert second.transmission[j] < first.transmission[i]
    spot_a, spot_b = window.compare_plot.figure.axes[:2]
    assert spot_a.images[0].get_clim() == spot_b.images[0].get_clim()
    window.compare_mode.setCurrentIndex(1)
    window.compare_results()
    assert window.comparison[1:4:2] == (a.focus_index, second.focus_index)
    path = tmp_path / "comparison.png"
    monkeypatch.setattr(window, "choose_path", lambda *args: str(path))
    window.export_target.setCurrentIndex(window.export_target.findData("compare"))
    window.export_plot()
    assert path.stat().st_size > 5000
    window.clear_baseline()
    assert window.baseline is None and window.comparison is None


def test_longitudinal_uses_computed_slices_and_links_observer(window, monkeypatch, tmp_path):
    from types import SimpleNamespace
    r = window.result
    window.show_longitudinal()
    ax = window.longitudinal_plot.ax
    cross_section = r.intensity[:, r.project.grid // 2, :]
    expected = 10 * np.log10(np.maximum(cross_section / cross_section.max(), 1e-5))
    np.testing.assert_allclose(np.asarray(ax.collections[0].get_array()).reshape(expected.T.shape), expected.T)
    window.locate_longitudinal_plane(SimpleNamespace(inaxes=ax, xdata=r.z[3]*1e3))
    assert window.plane_slider.value() == 3
    path = tmp_path / "longitudinal.svg"
    monkeypatch.setattr(window, "choose_path", lambda *args: str(path))
    window.export_target.setCurrentIndex(window.export_target.findData("longitudinal"))
    window.export_plot()
    assert path.stat().st_size > 5000



def test_mode_controls_sampling_roundtrip_and_worker(window, app, tmp_path):
    """从模式控件经真实后台线程到结果和项目文件验证完整链路。"""
    from gaussian_lab.model import Mode
    window.mode_preset.setCurrentIndex(window.mode_preset.findData("TEM01+TEM10"))
    window.apply_mode_preset()
    assert window.read_project().modes == [Mode("HG", 0, 1), Mode("HG", 1, 0)]
    window.mode_table.item(1, 4).setText("90")
    window.compute()
    wait_until(app, lambda: window.job is not None and not window.job.isRunning() and not window.dirty)
    assert window.result.project.modes[1].phase_deg == 90
    assert any("高阶/相干" in w for w in window.result.warnings)
    assert "256×256" in window.sampling_info.text()
    p = window.read_project()
    path = tmp_path / "coherent.json"
    from gaussian_lab.model import save_project
    save_project(p, path)
    window.fill_project(load_project(path))
    assert window.read_project() == p
    window.samples.setValue(641)
    window.grid.setCurrentText("2048")
    assert window.grid.currentText() == "2048"
    window.storage_mode.setCurrentIndex(window.storage_mode.findData("ram"))
    with pytest.raises(ValueError, match="384 MiB"):
        window.read_project()
    window.samples.setValue(17)
    assert window.read_project().grid == 2048
    assert "Δx=" in window.sampling_info.text()



def test_memory_options_prediction_and_saved_project(window, app, tmp_path, monkeypatch):
    """超限配置仍显示预测，调整上限后可保存；元件编辑与系统低内存提示同步。"""
    from gaussian_lab.model import save_project
    import gaussian_lab.gui as gui
    window.grid.setCurrentText("2048")
    window.samples.setValue(65)
    window.storage_mode.setCurrentIndex(window.storage_mode.findData("ram"))
    assert "1.03 GiB" in window.memory_info.text()
    assert "结果超出上限" in window.memory_info.text()
    with pytest.raises(ValueError, match="384 MiB"):
        window.read_project()
    window.memory_limit.setValue(1536)
    p = window.read_project()
    assert p.memory_limit_mib == 1536
    assert "结果超出上限" not in window.memory_info.text()
    assert "CUDA 显存工作区" in window.memory_info.text()
    path = tmp_path / "memory-options.json"
    save_project(p, path)
    window.memory_limit.setValue(384)
    window.fill_project(load_project(path))
    assert window.memory_limit.value() == 1536
    assert window.read_project() == p
    monkeypatch.setattr(gui, "system_memory", lambda: {"total_bytes": 1024**3, "available_bytes": 1, "process_bytes": 1024**2})
    window.update_sampling_info()
    assert "超过当前可用 RAM" in window.memory_info.text()
    assert window.memory_timer.isActive()
    window.grid.setCurrentText("128")
    window.samples.setValue(17)
    window.table.item(0, 1).setText("111")
    assert "结果数据：1.2 MiB" in window.memory_info.text()
    window.compute()
    wait_until(app, lambda: window.job is not None and not window.job.isRunning() and not window.dirty)
    assert window.result.project.memory_limit_mib == 1536
    assert window.result.provenance["memory_estimate"]["result_bytes"] == window.result.intensity.base.nbytes
    assert window.memory_timer.isActive()



def test_display_modes_release_3d_and_keep_calculation(window, app, monkeypatch):
    """显示切换不重新求解；仅计算无新图形，二维无需三维场景。"""
    original = window.result
    revision = window.revision
    window.display_mode.setCurrentIndex(window.display_mode.findData("2d"))
    app.processEvents()
    assert window.scene is None
    assert window.result is original and window.revision == revision
    assert window.schematic_plot.ax is not None
    assert "二维光路" in window.schematic_plot.ax.get_title()
    window.display_mode.setCurrentIndex(window.display_mode.findData("none"))
    assert window.scene is None and not window.tabs.isVisible()
    assert not window.bottom.isVisible()
    assert all(not p.figure.axes for p in (window.spot_plot, window.beam_plot, window.schematic_plot))
    window.compute()
    wait_until(app, lambda: not window.job.isRunning() and not window.dirty)
    assert window.result.r86.min() > 0
    assert not window.spot_plot.figure.axes
    window.display_mode.setCurrentIndex(window.display_mode.findData("2d"))
    assert window.scene is None and window.spot_plot.ax.images
    window.pin_baseline()
    assert window.baseline is not None
    window.release_memory_cache()
    assert window.baseline is None and not window.result_cache.entries
    window.display_mode.setCurrentIndex(window.display_mode.findData("3d"))
    assert window.scene is not None and window.scene.screen_actor is not None


def test_focal_image_pixel_centers_zoom_and_raw_intensity(window, app):
    """焦点原始像素与物理光轴对齐，显示值不靠插值伪造亚像素结构。"""
    from gaussian_lab.model import Project, Element
    from gaussian_lab.optics import analytic
    p = Project(grid=512, samples=17, window=.003, length=.18, elements=[Element("lens", .1, .04)])
    r = simulate(p)
    k = r.focus_index
    window.spot_plot.spot(r, k, smooth=False)
    plot = window.spot_plot.ax.images[0]
    extent = plot.get_extent()
    dx = p.window / p.grid * 1e3
    midpoint = extent[0] + (p.grid//2 + .5)*dx
    assert midpoint == pytest.approx(0, abs=1e-12)
    np.testing.assert_allclose(plot.get_array(), r.intensity[k]/r.intensity[k].max())
    assert plot.get_interpolation() == "nearest"
    assert window.spot_plot.ax.get_xlim()[1] < .15
    assert any("像素" in t.get_text() for t in window.spot_plot.ax.texts)
    width = analytic(p, [r.z[k]])[0]
    expected = np.exp(-2 * (r.x / width)**2)
    np.testing.assert_allclose(r.intensity[k, p.grid//2]/r.intensity[k].max(), expected, atol=.02)


def test_requested_presets_smoothing_and_automatic_disk_worker(window, app, tmp_path):
    """新预设可应用保存；平滑不改数据/触发求解，超预算可完成真实后台计算。"""
    from gaussian_lab.model import MODE_PRESET_KEYS, mode_preset, save_project
    for key in MODE_PRESET_KEYS:
        window.mode_preset.setCurrentIndex(window.mode_preset.findData(key))
        window.apply_mode_preset()
        assert window.read_project().modes == mode_preset(key)
    window.fill_project(window.result.project)
    assert window.mode_preset.currentData() == "TEM00"
    original, revision = window.result, window.revision
    window.spot_render.setCurrentIndex(1)
    window.spot_render.setCurrentIndex(0)
    assert window.result is original and window.revision == revision
    assert window.spot_plot.ax.images[0].get_interpolation() == "bilinear"
    k = window.plane_slider.value()
    np.testing.assert_array_equal(window.spot_plot.ax.images[0].get_array(), original.intensity[k]/original.intensity[k].max())
    window.grid.setCurrentText("4096")
    window.samples.setValue(2049)
    assert window.read_project().selected_storage() == "disk"
    assert "磁盘缓存" in window.memory_info.text()
    assert "结果超出上限" not in window.memory_info.text()
    window.grid.setCurrentText("128")
    window.samples.setValue(641)
    window.memory_limit.setValue(32)
    window.display_mode.setCurrentIndex(window.display_mode.findData("2d"))
    window.compute()
    wait_until(app, lambda: not window.job.isRunning() and not window.dirty)
    assert window.result.provenance["memory_estimate"]["storage_mode"] == "disk"
    assert window.result.intensity.shape[1:] == (128,128)
    path = tmp_path/"automatic-disk.json"
    save_project(window.read_project(), path)
    window.fill_project(load_project(path))
    assert window.storage_mode.currentData() == "auto"


def test_all_curve_hover_points_dual_axis_and_image_pixels(window, app):
    """发送真实 Matplotlib 鼠标事件，核验各曲线和双纵轴的点值与单位。"""
    from matplotlib.backend_bases import MouseEvent
    p, r = window.result.project, window.result
    rows = scan(p, 0, .1, .14, 3)
    charts = [(window.beam_plot, lambda: window.beam_plot.beam(r, 0)),
              (window.profile_plot, lambda: window.profile_plot.profile(r, 0)),
              (window.energy_plot, lambda: window.energy_plot.energy(r, 0)),
              (window.scan_plot, lambda: window.scan_plot.scanning(rows, "lens")),
              (window.compare_plot, lambda: window.compare_plot.compare(r, 0, r, 1, "对比")),
              (window.schematic_plot, lambda: window.schematic_plot.schematic(r, 0))]
    for canvas, draw in charts:
        draw()
        canvas.draw()
        seen = 0
        for ax in canvas.figure.axes:
            if ax.name == "3d": continue
            for line in ax.lines:
                if line.get_transform() is not ax.transData: continue
                values = line.get_xydata()
                xy = ax.transData.transform(values)
                candidates = [i for i, (x,y) in enumerate(xy) if np.isfinite([x,y]).all() and ax.bbox.contains(x,y)]
                if not candidates: continue
                i = candidates[len(candidates)//2]
                x,y = xy[i]
                event = MouseEvent("motion_notify_event", canvas, x, y)
                canvas.callbacks.process("motion_notify_event", event)
                assert canvas.hover_data is not None
                assert canvas.hover_data["xlabel"]
                assert abs(canvas.hover_data["x"] - values[i,0]) <= max(abs(values[i,0])*.01, .01)
                seen += 1
        assert seen > 0
        canvas.callbacks.process("figure_leave_event", MouseEvent("figure_leave_event", canvas, -1, -1))
        assert canvas.hover_data is None
    window.spot_plot.spot(r, 0)
    window.spot_plot.draw()
    x,y = window.spot_plot.ax.transData.transform((0,0))
    window.spot_plot.callbacks.process("motion_notify_event", MouseEvent("motion_notify_event", window.spot_plot, x,y))
    assert window.spot_plot.hover_data["label"] == "像素强度"


def test_locating_focus_from_preview_requests_full_calculation(window, app):
    window.result.provenance["quality"] = "preview"
    window.locate_focus()
    wait_until(app, lambda: window.job is not None and not window.job.isRunning() and not window.dirty)
    assert window.result.provenance["quality"] == "full"
    assert window.plane_slider.value() == window.result.focus_index



@pytest.mark.parametrize("mode", ["none", "2d"])
def test_cold_start_without_vtk_for_low_memory_modes(mode):
    """独立进程证明低占用启动没有预先导入 VTK，不只是隐藏已创建的窗口。"""
    import subprocess
    import sys
    from pathlib import Path
    code = "from PySide6.QtWidgets import QApplication; from gaussian_lab.gui import MainWindow; import sys; app=QApplication([]); w=MainWindow(auto_compute=False, display_mode=sys.argv[1]); assert w.scene is None; assert not any(n.startswith('vtkmodules') for n in sys.modules); w.close()"
    result = subprocess.run([sys.executable, "-c", code, mode], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, timeout=40)
    assert result.returncode == 0, result.stderr.decode(errors="replace")



def test_actual_out_of_memory_has_actionable_chinese_message(app, monkeypatch):
    import gaussian_lab.gui as gui
    from gaussian_lab.model import Project
    def allocation_failure(*args, **kwargs):
        raise MemoryError("fixture allocation failure")
    monkeypatch.setattr(gui, "simulate", allocation_failure)
    job = Job("simulate", Project(grid=128, samples=17))
    failures = []
    job.failed.connect(failures.append)
    job.run()
    assert len(failures) == 1
    assert "实际可用内存不足" in failures[0]
    assert "保留上一次" in failures[0]
