"""桌面界面及任务调度，连接输入、后台计算、图表和三维场景。"""
import os
os.environ.setdefault("QT_API", "pyside6")
import json
from pathlib import Path
import threading
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QSlider, QFileDialog, QMessageBox, QProgressBar, QSplitter,
    QFormLayout, QGroupBox, QCheckBox, QAbstractItemView)
from .model import Project, Element, preset, load_project, save_project
from .optics import simulate, scan, convergence, export_csv, Cancelled
from .scene import OpticalScene
from .charts import PlotCanvas

STYLE = """
QMainWindow,QWidget {background:#0b1322;color:#dce8f8;font-family:'Microsoft YaHei';font-size:12px;}
QGroupBox {border:1px solid #253650;border-radius:9px;margin-top:13px;padding:13px 9px 8px;}
QGroupBox::title {subcontrol-origin:margin;left:12px;color:#88aacd;}
QPushButton {background:#1c304b;border:1px solid #314967;border-radius:6px;padding:7px 13px;}
QPushButton:hover {background:#2c4866;border-color:#68cddd;}
QPushButton:disabled {color:#53647c;background:#152033;}
QPushButton#primary {background:#247e91;border-color:#45bbca;color:white;font-weight:bold;}
QComboBox,QDoubleSpinBox,QSpinBox {background:#142239;border:1px solid #30425d;border-radius:5px;padding:4px;min-height:20px;}
QComboBox QAbstractItemView {background:#142239;selection-background-color:#276379;}
QTableWidget {background:#101c2e;gridline-color:#273851;border:1px solid #263b57;selection-background-color:#20536d;}
QHeaderView::section {background:#192c44;color:#8ba9c9;padding:6px;border:0;}
QTabWidget::pane {border:1px solid #263851;border-radius:4px;}
QTabBar::tab {background:#132238;color:#8ba5c5;padding:7px 13px;}
QTabBar::tab:selected {color:#70dce6;border-bottom:2px solid #57c9d7;background:#1a2c44;}
QSlider::groove:horizontal {height:5px;background:#284057;border-radius:2px;}
QSlider::handle:horizontal {background:#6de1e5;width:14px;margin:-5px 0;border-radius:6px;}
QProgressBar {border:0;border-radius:3px;background:#1a2a40;text-align:center;max-height:15px;}
QProgressBar::chunk {background:#3bb6c4;}
QToolTip {background:#24374e;color:white;border:1px solid #6d9ab8;}
"""


class Job(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, kind, project, options=None):
        super().__init__()
        self.kind, self.project, self.options = kind, project, options
        self.cancel = threading.Event()

    def run(self):
        try:
            if self.kind == "scan":
                result = scan(self.project, *self.options, cancel=self.cancel, progress=self.progress.emit)
            elif self.kind == "convergence":
                result = convergence(self.project, self.cancel)
            else:
                result = simulate(self.project, self.cancel, self.progress.emit)
            self.completed.emit(result)
        except Cancelled:
            self.failed.emit("计算已取消；保留上一次完成的结果")
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName("primary")
    return widget


def spin(value, low, high, decimals=3, suffix=""):
    widget = QDoubleSpinBox()
    widget.setRange(low, high)
    widget.setDecimals(decimals)
    widget.setValue(value)
    widget.setSuffix(suffix)
    widget.setKeyboardTracking(False)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, auto_compute=True):
        super().__init__()
        self.setWindowTitle("GaussianLab · 高斯光束传输与光斑分析 V0.1")
        self.resize(1520, 980)
        self.setMinimumSize(1180, 780)
        self.result = None
        self.scan_rows = []
        self.job = None
        self.loading = False
        self.dirty = True
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(200)
        self.play_timer.timeout.connect(self.advance_plane)
        self.last_directory = str(Path.cwd() / "outputs")
        self.setStyleSheet(STYLE)
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 12, 18, 10)
        root.setSpacing(10)
        toolbar = QHBoxLayout()
        title = QLabel("GAUSSIAN<span style='color:#64dce6'>LAB</span>  <small>光学传输实验台</small>")
        title.setStyleSheet("font-size:22px;font-weight:bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()
        self.presets = QComboBox()
        self.presets.addItems(["单透镜聚焦", "双透镜扩束", "光阑衍射"])
        self.presets.setAccessibleName("预置案例")
        toolbar.addWidget(self.presets)
        toolbar.addWidget(button("加载案例", self.load_preset))
        toolbar.addWidget(button("打开", self.open_file))
        toolbar.addWidget(button("保存项目", self.save_file))
        self.run_button = button("计算光场", self.compute, True)
        toolbar.addWidget(self.run_button)
        self.cancel_button = button("取消", self.cancel_job)
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.cancel_button)
        root.addLayout(toolbar)
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left.setMinimumWidth(310)
        left.setMaximumWidth(420)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        source_box = QGroupBox("01  光源与传播 · SI 内核")
        form = QFormLayout(source_box)
        self.wave = spin(632.8, 100, 20000, 2, " nm")
        self.waist = spin(.45, .005, 10, 4, " mm")
        self.waist_z = spin(0, -5000, 5000, 2, " mm")
        self.length = spin(400, 10, 5000, 1, " mm")
        self.window_size = spin(6, .2, 100, 2, " mm")
        self.grid = QComboBox()
        self.grid.addItems(["128", "256", "512", "1024"])
        self.grid.setCurrentText("256")
        self.samples = QSpinBox()
        self.samples.setRange(17, 161)
        self.samples.setValue(65)
        for label, widget in (("波长 λ", self.wave), ("束腰半径 w₀", self.waist),
                              ("束腰位置 z₀", self.waist_z), ("传播长度", self.length),
                              ("计算窗口边长", self.window_size), ("横向网格 N×N", self.grid),
                              ("轴向采样点", self.samples)):
            form.addRow(label, widget)
            widget.setAccessibleName(label)
            if isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self.mark_dirty)
            else:
                widget.valueChanged.connect(self.mark_dirty)
        left_layout.addWidget(source_box)
        element_box = QGroupBox("02  光路元件 · 按位置传播")
        el = QVBoxLayout(element_box)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["类型", "z/mm", "f或直径/mm", "名称", "启用"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setMinimumHeight(125)
        self.table.setMaximumHeight(220)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemChanged.connect(self.mark_dirty)
        el.addWidget(self.table)
        row = QHBoxLayout()
        row.addWidget(button("＋透镜", lambda: self.add_element("lens")))
        row.addWidget(button("＋光阑", lambda: self.add_element("aperture")))
        row.addWidget(button("移除选中", self.remove_element))
        el.addLayout(row)
        hint = QLabel("透镜参数为焦距，光阑参数为直径。\n同位置按列表先后执行；元件为理想薄元件。")
        hint.setStyleSheet("color:#829ab6;font-size:10px;")
        el.addWidget(hint)
        left_layout.addWidget(element_box)
        scan_box = QGroupBox("03  单参数扫描")
        sf = QFormLayout(scan_box)
        self.scan_target = QComboBox()
        self.scan_target.currentIndexChanged.connect(self.scan_defaults)
        self.scan_low = spin(60, -2000, 2000, 3, " mm")
        self.scan_high = spin(180, -2000, 2000, 3, " mm")
        self.scan_count = QSpinBox()
        self.scan_count.setRange(3, 51)
        self.scan_count.setValue(9)
        sf.addRow("扫描元件", self.scan_target)
        sf.addRow("起点", self.scan_low)
        sf.addRow("终点", self.scan_high)
        sf.addRow("点数", self.scan_count)
        self.scan_button = button("开始扫描", self.start_scan)
        sf.addRow(self.scan_button)
        left_layout.addWidget(scan_box)
        self.convergence_button = button("检查末端 r86 收敛", self.start_convergence)
        left_layout.addWidget(self.convergence_button)
        left_layout.addStretch()
        splitter.addWidget(left)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        metrics = QHBoxLayout()
        self.cards = []
        for caption in ("高斯参考束腰 / 全局 z", "衍射最小 r86 / 采样点", "参考 θ / 衍射 θ86", "系统透过率 / 末端"):
            card = QLabel(caption + "\n—")
            card.setStyleSheet("background:#15243a;border:1px solid #293e59;border-radius:8px;padding:10px;color:#a8c4df;")
            card.setMinimumHeight(60)
            card.setAlignment(Qt.AlignCenter)
            self.cards.append(card)
            metrics.addWidget(card)
        rv.addLayout(metrics)
        main_views = QSplitter(Qt.Horizontal)
        scene_frame = QWidget()
        sv = QVBoxLayout(scene_frame)
        sv.setContentsMargins(0, 0, 0, 0)
        self.scene = OpticalScene(scene_frame)
        sv.addWidget(self.scene.interactor)
        scene_toolbar = QHBoxLayout()
        scene_toolbar.addWidget(QLabel("3D 光路 · r86 包络 · 横向 ×25"))
        scene_toolbar.addStretch()
        self.play_button = button("播放传播", self.toggle_play)
        scene_toolbar.addWidget(self.play_button)
        scene_toolbar.addWidget(button("复位视角", self.scene.reset_view))
        scene_toolbar.addWidget(button("场景截图", self.screenshot))
        sv.addLayout(scene_toolbar)
        main_views.addWidget(scene_frame)
        self.tabs = QTabWidget()
        self.spot_plot, self.profile_plot = PlotCanvas(), PlotCanvas()
        self.surface_plot = PlotCanvas(surface=True)
        self.tabs.addTab(self.spot_plot, "光斑")
        self.tabs.addTab(self.profile_plot, "剖面")
        self.tabs.addTab(self.surface_plot, "强度曲面")
        self.tabs.setMinimumWidth(300)
        self.tabs.currentChanged.connect(self.draw_plane)
        main_views.addWidget(self.tabs)
        main_views.setSizes([720, 430])
        rv.addWidget(main_views, 5)
        observer = QHBoxLayout()
        observer.addWidget(QLabel("观察屏 z"))
        self.plane_slider = QSlider(Qt.Horizontal)
        self.plane_slider.setRange(0, 64)
        self.plane_slider.setAccessibleName("观察屏位置")
        self.plane_slider.valueChanged.connect(self.draw_plane)
        observer.addWidget(self.plane_slider, 1)
        self.plane_label = QLabel("— mm")
        self.plane_label.setMinimumWidth(155)
        observer.addWidget(self.plane_label)
        self.log_scale = QCheckBox("对数光斑")
        self.log_scale.toggled.connect(self.draw_plane)
        observer.addWidget(self.log_scale)
        observer.addWidget(button("定位最小光斑", self.locate_focus))
        rv.addLayout(observer)
        self.bottom = QTabWidget()
        self.beam_plot, self.scan_plot = PlotCanvas(), PlotCanvas()
        self.bottom.addTab(self.beam_plot, "轴向传播")
        self.bottom.addTab(self.scan_plot, "参数扫描")
        self.scan_table = QTableWidget()
        self.scan_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.bottom.addTab(self.scan_table, "扫描数据")
        self.bottom.setMinimumHeight(200)
        rv.addWidget(self.bottom, 3)
        exports = QHBoxLayout()
        self.result_state = QLabel("尚未计算")
        self.result_state.setStyleSheet("color:#92abc8;")
        exports.addWidget(self.result_state, 1)
        exports.addWidget(button("导出 CSV", self.export_data))
        exports.addWidget(button("导出当前曲线", self.export_plot))
        rv.addLayout(exports)
        splitter.addWidget(right)
        splitter.setSizes([340, 1130])
        root.addWidget(splitter, 1)
        self.status = QLabel("标量近轴模型 · 所有数值结果需按网格与窗口验证 · 元件外形为示意")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#8ba6c5;font-size:11px;")
        root.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)
        self.setCentralWidget(central)
        self.fill_project(preset("单透镜聚焦"))
        if auto_compute:
            QTimer.singleShot(300, self.compute)

    def mark_dirty(self, *_):
        if not self.loading:
            self.dirty = True
            if hasattr(self, "result_state"):
                self.result_state.setText("参数已修改 · 当前图为上次结果，请重新计算")

    def fill_project(self, p):
        self.loading = True
        self.project_name = p.name
        if self.presets.findText(p.name) >= 0:
            self.presets.setCurrentText(p.name)
        for widget, value in ((self.wave, p.wavelength*1e9), (self.waist, p.waist*1e3),
                              (self.waist_z, p.waist_z*1e3), (self.length, p.length*1e3),
                              (self.window_size, p.window*1e3), (self.samples, p.samples)):
            widget.setValue(value)
        self.grid.setCurrentText(str(p.grid))
        self.table.setRowCount(0)
        for e in p.elements:
            self.insert_element(e)
        self.loading = False
        self.refresh_targets()
        self.mark_dirty()

    def insert_element(self, e):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, text in enumerate(("透镜" if e.kind == "lens" else "光阑", f"{e.z*1e3:g}",
                                    f"{e.value*1e3:g}", e.label)):
            item = QTableWidgetItem(text)
            if col == 0:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, col, item)
        enabled = QTableWidgetItem()
        enabled.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
        enabled.setCheckState(Qt.Checked if e.enabled else Qt.Unchecked)
        self.table.setItem(row, 4, enabled)

    def read_project(self):
        elements = []
        try:
            for row in range(self.table.rowCount()):
                elements.append(Element("lens" if self.table.item(row, 0).text() == "透镜" else "aperture",
                    float(self.table.item(row, 1).text())/1e3, float(self.table.item(row, 2).text())/1e3,
                    self.table.item(row, 3).text(), self.table.item(row, 4).checkState() == Qt.Checked))
        except (ValueError, AttributeError) as exc:
            raise ValueError("元件位置与焦距/直径须为数值，不得为空") from exc
        return Project(self.project_name, self.wave.value()*1e-9, self.waist.value()*1e-3,
                       self.waist_z.value()*1e-3, self.length.value()*1e-3, self.window_size.value()*1e-3,
                       int(self.grid.currentText()), self.samples.value(), elements).validate()

    def add_element(self, kind):
        n = self.table.rowCount() + 1
        self.insert_element(Element(kind, min(.1, self.length.value()/2000),
                                    .1 if kind == "lens" else .001, ("L" if kind == "lens" else "A")+str(n)))
        self.refresh_targets()

    def remove_element(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.mark_dirty()
            self.refresh_targets()

    def refresh_targets(self):
        self.scan_target.clear()
        for i in range(self.table.rowCount()):
            self.scan_target.addItem(f"{i+1} · {self.table.item(i, 3).text()} / {self.table.item(i, 0).text()}", i)
        self.scan_defaults()

    def scan_defaults(self, *_):
        i = self.scan_target.currentIndex()
        if i < 0 or not self.table.item(i, 2):
            return
        try:
            value = float(self.table.item(i, 2).text())
            a, b = sorted([value*.5, value*1.5])
            self.scan_low.setValue(a)
            self.scan_high.setValue(b)
        except ValueError:
            pass

    def load_preset(self):
        if self.job and self.job.isRunning():
            return
        self.fill_project(preset(self.presets.currentText()))
        self.compute()

    def launch_job(self, kind, options=None):
        if self.job and self.job.isRunning():
            return
        self.play_timer.stop()
        self.play_button.setText("播放传播")
        try:
            p = self.read_project()
        except Exception as exc:
            self.show_error(str(exc))
            return
        self.job = Job(kind, p, options)
        self.job.completed.connect(self.job_done)
        self.job.failed.connect(self.job_failed)
        self.job.progress.connect(self.progress.setValue)
        self.job.finished.connect(self.job_finished)
        self.run_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.convergence_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self.status.setText("计算中 · 可旋转场景 · 参数修改后须重新计算")
        self.job.start()

    def compute(self):
        self.launch_job("simulate")

    def start_scan(self):
        self.launch_job("scan", (self.scan_target.currentIndex(), self.scan_low.value()*1e-3,
                                 self.scan_high.value()*1e-3, self.scan_count.value()))

    def start_convergence(self):
        self.launch_job("convergence")

    def cancel_job(self):
        if self.job:
            self.job.cancel.set()

    def job_finished(self):
        self.run_button.setEnabled(True)
        self.scan_button.setEnabled(True)
        self.convergence_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def job_failed(self, message):
        self.status.setText(message)
        if "已取消" not in message:
            self.show_error(message)

    def job_done(self, result):
        try:
            self.dirty = self.read_project() != self.job.project
        except ValueError:
            self.dirty = True
        if self.job.kind == "scan":
            self.scan_rows = result
            self.scan_project = self.job.project.clone()
            self.scan_options = self.job.options
            kind = self.job.project.elements[self.job.options[0]].kind
            self.scan_plot.scanning(result, kind)
            self.scan_table.setColumnCount(6)
            self.scan_table.setHorizontalHeaderLabels(["参数/mm", "最小r86/μm", "焦点/mm", "透过率/%", "状态", "说明"])
            self.scan_table.setRowCount(len(result))
            for row, item in enumerate(result):
                for col, value in enumerate((f"{item['value_m']*1e3:.3f}", f"{item['min_r86_m']*1e6:.2f}",
                    f"{item['focus_z_m']*1e3:.2f}", f"{item['transmission']*100:.2f}", item["status"], item["note"])):
                    self.scan_table.setItem(row, col, QTableWidgetItem(value))
            self.scan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.bottom.setCurrentIndex(1)
            self.status.setText(f"扫描完成 · {len(result)} 点 · 最小值仅在末片透镜后离散采样区间内搜索 · CSV 保留警告")
        elif self.job.kind == "convergence":
            self.last_convergence = result
            self.status.setText(f"末端 r86 检查：加密网格变化 {result['grid_change']:.2%}；扩大窗口变化 {result['window_change']:.2%}。{result['note']}")
            Path("outputs").mkdir(exist_ok=True)
            Path("outputs/convergence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            self.result = result
            self.scene.set_result(result)
            ref = result.reference
            k = result.focus_index
            self.cards[0].setText(f"高斯参考束腰 / 全局 z\n{ref['waist']*1e6:.1f} μm  /  {ref['waist_z']*1e3:.1f} mm")
            self.cards[1].setText(f"衍射最小 r86 / 采样点\n{result.r86[k]*1e6:.1f} μm  /  {result.z[k]*1e3:.1f} mm")
            self.cards[2].setText(f"参考 θ / 衍射 θ86\n{ref['divergence']*1e3:.2f} / {result.theta86*1e3:.2f} mrad")
            self.cards[3].setText(f"系统透过率 / 末端\n{result.transmission[-1]*100:.2f} %")
            self.plane_slider.setRange(0, len(result.z)-1)
            self.plane_slider.setValue(k)
            self.draw_plane()
            self.status.setText("；".join(result.warnings) if result.warnings else
                                "计算完成 · 采样诊断无明显异常；尚需网格与窗口收敛验证 · 高斯与 r86 指标不同")
            self.bottom.setCurrentIndex(0)
        if self.job.kind == "scan":
            self.result_state.setText("扫描为任务参数快照 · 主场景与指标卡保留上次光场结果")
        else:
            self.result_state.setText("参数已修改 · 显示任务快照结果" if self.dirty else
                                      f"任务完成 · N={self.job.project.grid} · 标量近轴 / 轴向离散采样")
        self.progress.setValue(100)

    def draw_plane(self, *_):
        if self.result is None:
            return
        r = self.result
        i = min(self.plane_slider.value(), len(r.z)-1)
        self.plane_label.setText(f"{r.z[i]*1e3:.2f} mm · r86={r.r86[i]*1e6:.1f} μm")
        self.scene.set_plane(i)
        if self.tabs.currentIndex() == 0:
            self.spot_plot.spot(r, i, self.log_scale.isChecked())
        elif self.tabs.currentIndex() == 1:
            self.profile_plot.profile(r, i)
        else:
            self.surface_plot.intensity_surface(r, i)
        self.beam_plot.beam(r, i)

    def locate_focus(self):
        if self.result is not None:
            self.plane_slider.setValue(self.result.focus_index)

    def toggle_play(self):
        if self.result is None:
            return
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.play_button.setText("播放传播")
        else:
            self.play_timer.start()
            self.play_button.setText("暂停播放")

    def advance_plane(self):
        self.plane_slider.setValue((self.plane_slider.value()+1) % (self.plane_slider.maximum()+1))

    def show_error(self, text):
        QMessageBox.warning(self, "参数或计算提示", text)

    def choose_path(self, title, filename, filters, saving=True):
        Path(self.last_directory).mkdir(parents=True, exist_ok=True)
        method = QFileDialog.getSaveFileName if saving else QFileDialog.getOpenFileName
        path, _ = method(self, title, str(Path(self.last_directory) / filename), filters)
        if path:
            self.last_directory = str(Path(path).parent)
        return path

    def save_file(self):
        try:
            p = self.read_project()
            path = self.choose_path("保存光学项目", "optical-project.json", "JSON (*.json)")
            if path:
                save_project(p, path)
                self.status.setText("已保存项目：" + path)
        except Exception as exc:
            self.show_error(str(exc))

    def open_file(self):
        if self.job and self.job.isRunning():
            return
        path = self.choose_path("打开光学项目", "", "JSON (*.json)", False)
        if path:
            try:
                self.fill_project(load_project(path))
                self.compute()
            except Exception as exc:
                self.show_error(str(exc))

    def export_data(self):
        try:
            is_scan = self.bottom.currentIndex() in (1, 2)
            if is_scan and self.scan_rows:
                rows, project = self.scan_rows, self.scan_project
            elif self.result is not None:
                r = self.result
                rows = [{"z_m": float(z), "gaussian_w_m": float(w), "r86_m": float(s), "transmission": float(t)}
                        for z, w, s, t in zip(r.z, r.gaussian_w, r.r86, r.transmission)]
                project = r.project
            else:
                raise ValueError("请先完成计算或扫描")
            path = self.choose_path("导出计算快照数据", "scan.csv" if is_scan else "propagation.csv", "CSV (*.csv)")
            if path:
                export_csv(rows, path)
                save_project(project, str(Path(path).with_suffix(".project.json")))
                if is_scan:
                    Path(path + ".meta.json").write_text(json.dumps({"element_index": self.scan_options[0],
                        "low_m": self.scan_options[1], "high_m": self.scan_options[2], "count": self.scan_options[3],
                        "metric": "末片透镜后轴向离散采样点中的最小 r86"}, ensure_ascii=False, indent=2), encoding="utf-8")
                self.status.setText("已导出数据和对应参数快照：" + path)
        except Exception as exc:
            self.show_error(str(exc))

    def export_plot(self):
        plot = self.scan_plot if self.bottom.currentIndex() == 1 else self.beam_plot
        if plot.ax is None:
            return
        path = self.choose_path("导出当前定量曲线", "curve.png", "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)")
        if path:
            plot.figure.savefig(path, dpi=180, facecolor=plot.figure.get_facecolor())
            self.status.setText("已导出曲线：" + path)

    def screenshot(self):
        if self.result is None:
            return
        path = self.choose_path("保存三维场景", "scene.png", "PNG (*.png)")
        if path:
            self.scene.screenshot(path)
            self.status.setText("已保存场景：" + path)

    def closeEvent(self, event):
        self.play_timer.stop()
        if self.job and self.job.isRunning():
            self.job.cancel.set()
            self.job.wait()
        self.scene.close()
        super().closeEvent(event)


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
