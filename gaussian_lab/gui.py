"""桌面界面及任务调度，连接输入、后台计算、图表和三维场景。"""
import os
os.environ.setdefault("QT_API", "pyside6")
import json
import copy
from dataclasses import asdict
from pathlib import Path
import threading
import sys
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer, QSettings
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QSlider, QFileDialog, QMessageBox, QProgressBar, QSplitter,
    QFormLayout, QGroupBox, QCheckBox, QAbstractItemView, QScrollArea, QStackedWidget,
    QStyle, QStyleOptionSpinBox, QAbstractSpinBox)
from . import __version__
from .model import Project, Element, Mode, preset, load_project, save_project, MODE_PRESET_KEYS, mode_preset
from .optics import simulate, scan, convergence, export_csv, export_result, ALGORITHM_VERSION, Cancelled
from .charts import PlotCanvas
from .backend import preview_project
from .session import ResultCache
from .memory import estimate_memory, system_memory, format_memory

STYLE = """
QMainWindow,QWidget {background:#f5f5f7;color:#1f2937;font-family:'Microsoft YaHei';font-size:12px;}
QWidget#workspaceHeader {background:#ffffff;border:1px solid #e5e5ea;border-radius:16px;}
QLabel#productTitle {font-size:22px;font-weight:700;color:#0f172a;}
QLabel#productCaption {font-size:11px;color:#475569;}
QGroupBox {border:1px solid #e2e8f0;border-radius:10px;margin-top:15px;padding:13px 10px 9px;}
QGroupBox::title {subcontrol-origin:margin;left:12px;color:#334155;font-weight:bold;}
QPushButton {background:#ffffff;border:1px solid #cbd5e1;border-radius:8px;padding:7px 11px;}
QPushButton:hover {background:#eff6ff;border-color:#60a5fa;}
QPushButton:disabled {color:#94a3b8;background:#f1f5f9;}
QPushButton#primary {background:#2563eb;border-color:#1d4ed8;color:white;font-weight:bold;}
QPushButton#primary:hover {background:#1d4ed8;}
QPushButton#primary:disabled {background:#e2e8f0;border-color:#e2e8f0;color:#64748b;}
QComboBox,QDoubleSpinBox,QSpinBox {background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;padding:5px;min-height:20px;}
QComboBox QAbstractItemView {background:#f8fafc;selection-background-color:#dbeafe;}
QDoubleSpinBox,QSpinBox {padding-right:27px;min-height:24px;}
QDoubleSpinBox::up-button,QSpinBox::up-button {subcontrol-origin:border;subcontrol-position:top right;width:23px;border:0;border-top-right-radius:8px;background:transparent;}
QDoubleSpinBox::down-button,QSpinBox::down-button {subcontrol-origin:border;subcontrol-position:bottom right;width:23px;border:0;border-bottom-right-radius:8px;background:transparent;}
QDoubleSpinBox::up-button:hover,QSpinBox::up-button:hover,QDoubleSpinBox::down-button:hover,QSpinBox::down-button:hover {background:#e8eef7;}
QDoubleSpinBox::up-button:pressed,QSpinBox::up-button:pressed,QDoubleSpinBox::down-button:pressed,QSpinBox::down-button:pressed {background:#dce7f6;}
QDoubleSpinBox::up-arrow,QSpinBox::up-arrow,QDoubleSpinBox::down-arrow,QSpinBox::down-arrow {image:none;width:0;height:0;}
QTableWidget {background:#ffffff;gridline-color:#e2e8f0;border:1px solid #cbd5e1;selection-background-color:#dbeafe;}
QHeaderView::section {background:#f1f5f9;color:#334155;padding:6px;border:0;}
QTabWidget::pane {border:1px solid #cbd5e1;border-radius:4px;}
QTabBar::tab {background:#f8fafc;color:#475569;padding:7px 13px;}
QTabBar::tab:selected {color:#1d4ed8;border-bottom:2px solid #2563eb;background:#eff6ff;}
QTabBar::tab:hover:!selected {background:#f1f5f9;}
QScrollArea {border:0;}
QSplitter::handle {background:#f1f5f9;}
QSlider::groove:horizontal {height:5px;background:#cbd5e1;border-radius:2px;}
QSlider::handle:horizontal {background:#2563eb;width:14px;margin:-5px 0;border-radius:6px;}
QProgressBar {border:0;border-radius:2px;background:#e2e8f0;max-height:4px;}
QProgressBar::chunk {background:#2563eb;}
QScrollBar:vertical {background:#f8fafc;width:9px;margin:0;}
QScrollBar::handle:vertical {background:#cbd5e1;min-height:28px;border-radius:4px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:none;}
QToolTip {background:#ffffff;color:#1f2937;border:1px solid #94a3b8;}
"""


class ChevronStepper:
    """用抗锯齿细线绘制步进符号，点击、长按、键盘及无障碍行为由 Qt 保持。"""

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for control, direction, flag in (
            (QStyle.SC_SpinBoxUp, -1, QAbstractSpinBox.StepUpEnabled),
            (QStyle.SC_SpinBoxDown, 1, QAbstractSpinBox.StepDownEnabled),
        ):
            rect = self.style().subControlRect(QStyle.CC_SpinBox, option, control, self)
            if rect.isEmpty():
                continue
            active = self.isEnabled() and bool(self.stepEnabled() & flag)
            pen = QPen(QColor("#64748b" if active else "#cbd5e1"), 1.4)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            cx, cy = rect.center().x(), rect.center().y()
            path = QPainterPath()
            path.moveTo(cx-3, cy-direction*1.5)
            path.lineTo(cx, cy+direction*1.5)
            path.lineTo(cx+3, cy-direction*1.5)
            painter.drawPath(path)
        painter.end()


class NumericSpinBox(ChevronStepper, QSpinBox):
    """采用细线步进按钮的整数输入框。"""


class NumericDoubleSpinBox(ChevronStepper, QDoubleSpinBox):
    """采用细线步进按钮的小数输入框。"""


class Job(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, kind, project, options=None, backend="cpu", revision=None, cache=None):
        super().__init__()
        self.kind, self.project, self.options = kind, project, options
        self.backend, self.revision, self.cache = backend, revision, cache
        self.request_project = project.clone()
        self.cache_hit = False
        self.cancel = threading.Event()
        self.cuda_fft_cache = None
        self.cuda_device = None

    def run(self):
        try:
            if self.kind == "scan":
                result = scan(self.project, *self.options, cancel=self.cancel, progress=self.progress.emit, backend=self.backend)
            elif self.kind == "convergence":
                result = convergence(self.project, self.cancel, backend=self.backend)
            else:
                key = self.cache.key(self.request_project, self.backend, self.kind == "preview") if self.cache else None
                result = self.cache.get(key) if self.cache else None
                self.cache_hit = result is not None
                if result is None:
                    result = simulate(self.project, self.cancel, self.progress.emit, backend=self.backend)
                    if self.kind == "preview":
                        result.provenance["quality"] = "preview"
                        result.provenance["requested_project"] = asdict(self.request_project)
                    else:
                        result.provenance["quality"] = "full"
                    if self.cache and not self.cancel.is_set():
                        self.cache.put(key, result)
                if self.cancel.is_set():
                    raise Cancelled()
            self.completed.emit(result)
        except Cancelled:
            self.failed.emit("计算已取消；保留上一次完成的结果")
        except MemoryError:
            self.failed.emit("实际可用内存不足：请降低网格或轴向采样、切换 2D/仅计算，或清空缓存与方案 A；保留上一次完成的结果")
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            # CuPy 的线程缓存析构会显式触发全局 GC；先持有引用，避免在工作线程回收 VTK 对象。
            cp = sys.modules.get("cupy")
            if cp is not None and self.backend != "cpu":
                try:
                    self.cuda_device = cp.cuda.runtime.getDevice()
                    self.cuda_fft_cache = cp.fft.config.get_plan_cache()
                except Exception:
                    pass

    def release_cuda_cache(self):
        """线程及其 TLS 完全退出后，在主界面线程释放 FFT 缓存和触发的循环回收。"""
        if self.cuda_fft_cache is None:
            return
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("CUDA 任务缓存必须在界面主线程释放")
        self.wait()
        cp = sys.modules.get("cupy")
        if cp is not None:
            with cp.cuda.Device(self.cuda_device):
                self.cuda_fft_cache.clear()
                self.cuda_fft_cache = None


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName("primary")
    return widget


def spin(value, low, high, decimals=3, suffix=""):
    widget = NumericDoubleSpinBox()
    widget.setRange(low, high)
    widget.setDecimals(decimals)
    widget.setValue(value)
    widget.setSuffix(suffix)
    widget.setKeyboardTracking(True)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, auto_compute=True, display_mode=None):
        super().__init__()
        self.settings = QSettings("GaussianLab", "GaussianLab") if display_mode is None else None
        self.initial_display_mode = display_mode or str(self.settings.value("display_mode", "2d"))
        self.scene = None
        self.setWindowTitle(f"GaussianLab · 高斯光束传输与光斑分析 V{__version__}")
        self.resize(1520, 980)
        self.setMinimumSize(1060, 700)
        self.result = None
        self.baseline = None
        self.comparison = None
        self.longitudinal_result = None
        self.scan_rows = []
        self.job = None
        self.loading = False
        self.dirty = True
        self.revision = 0
        self.pending_preview = False
        self.pending_full = False
        self.closing = False
        self.result_cache = ResultCache()
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(400)
        self.preview_timer.timeout.connect(self.request_preview)
        self.plane_timer = QTimer(self)
        self.plane_timer.setSingleShot(True)
        self.plane_timer.setInterval(40)
        self.plane_timer.timeout.connect(self.draw_plane)
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(200)
        self.play_timer.timeout.connect(self.advance_plane)
        self.last_directory = str(Path.cwd() / "outputs")
        self.setStyleSheet(STYLE)
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 12, 18, 10)
        root.setSpacing(10)
        header = QWidget()
        header.setObjectName("workspaceHeader")
        toolbar = QHBoxLayout(header)
        toolbar.setContentsMargins(14, 8, 12, 8)
        brand = QVBoxLayout()
        brand.setSpacing(1)
        title = QLabel("GaussianLab")
        title.setObjectName("productTitle")
        subtitle = QLabel("高斯光束仿真与实验对比")
        subtitle.setObjectName("productCaption")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        toolbar.addLayout(brand)
        toolbar.addStretch()
        self.workspace = QComboBox()
        self.workspace.addItems(["光路搭建", "结果分析", "参数扫描"])
        self.workspace.setAccessibleName("工作区")
        toolbar.addWidget(self.workspace)
        self.presets = QComboBox()
        self.presets.addItems(["单透镜聚焦", "双透镜扩束", "光阑衍射"])
        self.presets.setAccessibleName("预置案例")
        toolbar.addWidget(self.presets)
        toolbar.addWidget(button("加载案例", self.load_preset))
        toolbar.addWidget(button("打开", self.open_file))
        toolbar.addWidget(button("保存项目", self.save_file))
        self.run_button = button("完整计算", self.compute, True)
        toolbar.addWidget(self.run_button)
        self.cancel_button = button("取消", self.cancel_job)
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.cancel_button)
        root.addWidget(header)
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left.setMinimumWidth(310)
        left.setMaximumWidth(420)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        source_box = QGroupBox("光源与传播")
        form = QFormLayout(source_box)
        self.wave = spin(632.8, 100, 20000, 2, " nm")
        self.waist = spin(.45, .005, 10, 4, " mm")
        self.waist_z = spin(0, -5000, 5000, 2, " mm")
        self.length = spin(400, 10, 5000, 1, " mm")
        self.window_size = spin(6, .2, 100, 2, " mm")
        self.grid = QComboBox()
        self.grid.addItems(["128", "256", "512", "1024", "2048", "4096"])
        self.grid.setCurrentText("256")
        self.samples = NumericSpinBox()
        self.samples.setRange(17, 2049)
        self.samples.setValue(65)
        self.focus_refinement = NumericSpinBox()
        self.focus_refinement.setRange(0, 4)
        self.focus_refinement.setValue(2)
        for label, widget in (("波长 λ", self.wave), ("束腰半径 w₀", self.waist),
                              ("束腰位置 z₀", self.waist_z), ("传播长度", self.length),
                              ("计算窗口边长", self.window_size), ("横向网格 N×N", self.grid),
                              ("轴向采样点", self.samples), ("焦区细化级数", self.focus_refinement)):
            form.addRow(label, widget)
            widget.setAccessibleName(label)
            if isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self.mark_dirty)
            else:
                widget.valueChanged.connect(self.mark_dirty)
        left_layout.addWidget(source_box)
        self.sampling_info = QLabel()
        self.sampling_info.setWordWrap(True)
        for widget in (self.window_size, self.length, self.samples):
            widget.valueChanged.connect(self.update_sampling_info)
        self.grid.currentTextChanged.connect(self.update_sampling_info)
        left_layout.addWidget(self.sampling_info)
        mode_box = QGroupBox("相干输入光 / 横模")
        mode_layout = QVBoxLayout(mode_box)
        self.mode_preset = QComboBox()
        for key in MODE_PRESET_KEYS:
            self.mode_preset.addItem(key.replace("+", " + ") + (" 相干叠加" if "+" in key else ""), key)
        self.mode_preset.setCurrentIndex(self.mode_preset.findData("TEM00"))
        self.mode_preset.setToolTip("LG 编号为径向 p、方位 l；TEM 以 HG 横模计算。TEM01+TEM10 默认为等振幅、同相，可在表中修改相位。")
        mode_layout.addWidget(self.mode_preset)
        mode_layout.addWidget(button("应用输入光", self.apply_mode_preset))
        self.mode_table = QTableWidget(0, 5)
        self.mode_table.setHorizontalHeaderLabels(["类型", "n / p", "m / l", "振幅", "相位°"])
        self.mode_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mode_table.setMaximumHeight(160)
        self.mode_table.setMinimumHeight(110)
        self.mode_table.itemChanged.connect(self.mark_dirty)
        mode_layout.addWidget(self.mode_table)
        mode_buttons = QHBoxLayout()
        mode_buttons.addWidget(button("添加模式", lambda: self.add_mode(Mode("HG", 1, 0))))
        mode_buttons.addWidget(button("删除模式", self.remove_mode))
        mode_layout.addLayout(mode_buttons)
        mode_hint = QLabel("同波长、同轴、共用束腰。按复振幅相加，\n相位以入口面为参考；HG: n、m，LG: p、l。\n单模式等振幅具有相同理论功率；最多 8 项。")
        mode_hint.setWordWrap(True)
        mode_layout.addWidget(mode_hint)
        left_layout.addWidget(mode_box)
        performance_box = QGroupBox("计算与交互")
        performance_form = QFormLayout(performance_box)
        self.backend_choice = QComboBox()
        for text, key in (("自动选择", "auto"), ("CPU 兼容模式", "cpu"), ("CUDA 优先", "cuda")):
            self.backend_choice.addItem(text, key)
        self.backend_choice.setToolTip("CUDA 不可用时回退 CPU；自动模式小网格优先 CPU。便携版首次 CUDA 需联网补充约 3.6 MB 头文件并建立缓存。")
        self.backend_choice.currentIndexChanged.connect(self.mark_dirty)
        performance_form.addRow("计算后端", self.backend_choice)
        self.display_mode = QComboBox()
        for text, key in (("2D 光路示意（低占用）", "2d"), ("3D 光路", "3d"), ("仅计算（关闭绘图）", "none")):
            self.display_mode.addItem(text, key)
        performance_form.addRow("显示模式", self.display_mode)
        self.display_hint = QLabel("2D / 仅计算不创建 VTK 三维窗口。3D 额外占用 RAM/显存；切换后已加载库与驱动缓存可能保留。")
        self.display_hint.setWordWrap(True)
        performance_form.addRow(self.display_hint)
        self.memory_limit = NumericSpinBox()
        self.memory_limit.setRange(32, 65536)
        self.memory_limit.setSingleStep(128)
        self.memory_limit.setSuffix(" MiB")
        self.memory_limit.setValue(384)
        self.memory_limit.setAccessibleName("结果 RAM 预算")
        self.memory_limit.setToolTip("自动模式超预算转存磁盘；仅 RAM 模式超预算阻止计算。FFT 工作区、绘图及系统文件缓存另计。")
        self.memory_limit.valueChanged.connect(self.mark_dirty)
        performance_form.addRow("结果 RAM 预算", self.memory_limit)
        self.storage_mode = QComboBox()
        for text, key in (("自动：超预算用磁盘（推荐）", "auto"), ("始终使用磁盘缓存", "disk"), ("仅 RAM：超预算停止", "ram")):
            self.storage_mode.addItem(text, key)
        self.storage_mode.currentIndexChanged.connect(self.mark_dirty)
        performance_form.addRow("结果存储", self.storage_mode)
        self.spot_render = QCheckBox("平滑显示")
        self.spot_render.setChecked(True)
        self.spot_render.setToolTip("平滑不增加采样精度；鼠标读数、曲线和导出数值仍来自原始数据。")
        self.spot_render.toggled.connect(self.draw_plane)
        performance_form.addRow("二维光斑", self.spot_render)
        self.memory_info = QLabel()
        self.memory_info.setWordWrap(True)
        self.memory_info.setAccessibleName("内存估算")
        self.memory_info.setToolTip("运行范围为经验估算，FFT/驱动可能超出。显示的系统可用 RAM 会变化，不代表显存。")
        performance_form.addRow(self.memory_info)
        performance_form.addRow(button("刷新可用内存", self.update_sampling_info))
        performance_form.addRow(button("清空缓存与方案 A", self.release_memory_cache))
        self.auto_preview = QCheckBox("改参后自动预览")
        self.auto_preview.setChecked(auto_compute)
        self.auto_preview.setToolTip("停止输入 400 ms 后更新；预览最多 256 网格、33 个轴向点，不进行焦区细化。")
        self.auto_preview.toggled.connect(self.preview_toggled)
        performance_form.addRow(self.auto_preview)
        left_layout.insertWidget(2, performance_box)
        element_box = QGroupBox("光路元件")
        el = QVBoxLayout(element_box)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["类型", "位置", "参数", "名称", "启用", "口径"])
        self.table.setAlternatingRowColors(True)
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
        hint = QLabel("位置、参数和口径均用 mm。参数为焦距或光阑直径。\n透镜口径留空表示不限，同位置按列表顺序执行。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748b;font-size:10px;")
        el.addWidget(hint)
        left_layout.addWidget(element_box)
        scan_box = QGroupBox("单参数扫描")
        sf = QFormLayout(scan_box)
        self.scan_target = QComboBox()
        self.scan_target.currentIndexChanged.connect(self.scan_defaults)
        self.scan_low = spin(60, -2000, 2000, 3, " mm")
        self.scan_high = spin(180, -2000, 2000, 3, " mm")
        self.scan_count = NumericSpinBox()
        self.scan_count.setRange(3, 51)
        self.scan_count.setValue(9)
        sf.addRow("扫描元件", self.scan_target)
        sf.addRow("起点", self.scan_low)
        sf.addRow("终点", self.scan_high)
        sf.addRow("点数", self.scan_count)
        self.scan_button = button("开始扫描", self.start_scan)
        sf.addRow(self.scan_button)
        left_layout.addWidget(scan_box)
        self.convergence_button = button("检查多指标收敛", self.start_convergence)
        left_layout.addWidget(self.convergence_button)
        # 将常用光路置顶，专业设置按需展开。
        left_layout.removeWidget(element_box)
        left_layout.insertWidget(1, element_box)
        self.advanced_toggle = button("计算与性能设置 ▸", lambda: performance_box.setVisible(not performance_box.isVisible()))
        left_layout.insertWidget(2, self.advanced_toggle)
        performance_box.hide()
        self.mode_toggle = button("输入横模与相干叠加 ▸", lambda: mode_box.setVisible(not mode_box.isVisible()))
        left_layout.insertWidget(3, self.mode_toggle)
        mode_box.hide()
        self.sampling_toggle = QCheckBox("精细采样设置")
        for row_index in range(4, 8):
            form.setRowVisible(row_index, False)
        self.sampling_toggle.toggled.connect(lambda shown: [form.setRowVisible(i, shown) for i in range(4, 8)])
        form.addRow(self.sampling_toggle)
        self.scan_panel = scan_box
        self.source_panel = source_box
        self.element_panel = element_box
        self.performance_panel = performance_box
        self.mode_panel = mode_box
        left_layout.addStretch()
        self.parameter_scroll = QScrollArea()
        self.parameter_scroll.setWidgetResizable(True)
        self.parameter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.parameter_scroll.setMinimumWidth(330)
        self.parameter_scroll.setMaximumWidth(440)
        self.parameter_scroll.setWidget(left)
        splitter.addWidget(self.parameter_scroll)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        metrics = QHBoxLayout()
        self.cards = []
        for caption in ("高斯参考束腰 / 全局 z", "衍射最小 r86 / 采样点", "参考 θ / 衍射 θ86", "系统透过率 / 末端"):
            card = QLabel(caption + "\n—")
            card.setStyleSheet("background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;padding:10px;color:#1e3a5f;")
            card.setMinimumHeight(60)
            card.setAlignment(Qt.AlignCenter)
            self.cards.append(card)
            metrics.addWidget(card)
        rv.addLayout(metrics)
        main_views = QSplitter(Qt.Horizontal)
        self.scene_frame = QWidget()
        sv = QVBoxLayout(self.scene_frame)
        sv.setContentsMargins(0, 0, 0, 0)
        self.scene_stack = QStackedWidget()
        self.schematic_plot = PlotCanvas()
        self.compute_placeholder = QLabel("仅计算模式：已关闭绘图与三维渲染。\n计算强度数据仍保留，可保存项目或导出结果。")
        self.compute_placeholder.setAlignment(Qt.AlignCenter)
        self.compute_placeholder.setWordWrap(True)
        self.scene_stack.addWidget(self.schematic_plot)
        self.scene_stack.addWidget(self.compute_placeholder)
        sv.addWidget(self.scene_stack)
        scene_toolbar = QHBoxLayout()
        self.scene_caption = QLabel("2D 光路 · r86 示意")
        scene_toolbar.addWidget(self.scene_caption)
        scene_toolbar.addStretch()
        self.play_button = button("播放传播", self.toggle_play)
        scene_toolbar.addWidget(self.play_button)
        scene_toolbar.addWidget(button("侧视", lambda: self.scene.view_xy() if self.scene else None))
        scene_toolbar.addWidget(button("正看光斑", lambda: self.scene.view_yz() if self.scene else None))
        self.reset_view_button = button("复位视角", self.reset_scene_view)
        scene_toolbar.addWidget(self.reset_view_button)
        scene_toolbar.addWidget(button("场景截图", self.screenshot))
        sv.addLayout(scene_toolbar)
        main_views.addWidget(self.scene_frame)
        self.tabs = QTabWidget()
        self.spot_plot, self.profile_plot = PlotCanvas(), PlotCanvas()
        self.surface_plot = PlotCanvas(surface=True)
        self.tabs.addTab(self.spot_plot, "光斑")
        self.tabs.addTab(self.profile_plot, "剖面")
        self.tabs.addTab(self.surface_plot, "强度曲面")
        self.energy_plot = PlotCanvas()
        self.tabs.addTab(self.energy_plot, "包围能量")
        self.tabs.setMinimumWidth(300)
        self.tabs.currentChanged.connect(self.draw_plane)
        self.tabs.setCornerWidget(button("导出此图", lambda: self.export_named(("spot","profile","surface","energy")[self.tabs.currentIndex()])))
        main_views.addWidget(self.tabs)
        main_views.setSizes([720, 430])
        views = QSplitter(Qt.Vertical)
        views.setChildrenCollapsible(False)
        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addWidget(main_views, 1)
        views.addWidget(upper)
        observer = QHBoxLayout()
        observer.addWidget(QLabel("观察屏 z"))
        self.plane_slider = QSlider(Qt.Horizontal)
        self.plane_slider.setRange(0, 64)
        self.plane_slider.setAccessibleName("观察屏位置")
        self.plane_slider.valueChanged.connect(self.request_plane_draw)
        observer.addWidget(self.plane_slider, 1)
        self.plane_label = QLabel("— mm")
        self.plane_label.setMinimumWidth(155)
        observer.addWidget(self.plane_label)
        self.log_scale = QCheckBox("对数光斑")
        self.log_scale.toggled.connect(self.draw_plane)
        observer.addWidget(self.log_scale)
        observer.addWidget(button("定位最小光斑", self.locate_focus))
        upper_layout.addLayout(observer)
        self.bottom = QTabWidget()
        self.beam_plot, self.scan_plot = PlotCanvas(), PlotCanvas()
        self.bottom.addTab(self.beam_plot, "轴向传播")
        self.bottom.addTab(self.scan_plot, "参数扫描")
        self.scan_table = QTableWidget()
        self.scan_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.bottom.addTab(self.scan_table, "扫描数据")
        compare_panel = QWidget()
        compare_layout = QVBoxLayout(compare_panel)
        compare_controls = QHBoxLayout()
        self.baseline_label = QLabel("尚未固定方案 A")
        compare_controls.addWidget(self.baseline_label, 1)
        compare_controls.addWidget(button("固定当前为 A", self.pin_baseline))
        compare_controls.addWidget(button("清除 A", self.clear_baseline))
        self.compare_mode = QComboBox()
        self.compare_mode.addItems(["共用观察面", "各自最小光斑面"])
        compare_controls.addWidget(self.compare_mode)
        compare_controls.addWidget(button("与当前 B 对比", self.compare_results, True))
        compare_layout.addLayout(compare_controls)
        self.compare_plot = PlotCanvas()
        compare_layout.addWidget(self.compare_plot, 1)
        self.bottom.addTab(compare_panel, "A/B 对比")
        longitudinal_panel = QWidget()
        longitudinal_layout = QVBoxLayout(longitudinal_panel)
        longitudinal_layout.addWidget(button("从当前结果生成纵向强度图", self.show_longitudinal), 0, Qt.AlignLeft)
        self.longitudinal_plot = PlotCanvas()
        self.longitudinal_plot.mpl_connect("button_press_event", self.locate_longitudinal_plane)
        longitudinal_layout.addWidget(self.longitudinal_plot, 1)
        self.bottom.addTab(longitudinal_panel, "纵向强度")
        self.bottom.setCornerWidget(button("导出本页", self.export_bottom))
        self.bottom.setMinimumHeight(200)
        views.addWidget(self.bottom)
        views.setStretchFactor(0, 5)
        views.setStretchFactor(1, 3)
        self.main_views = main_views
        self.workspace_views = views
        rv.addWidget(views, 1)
        exports = QHBoxLayout()
        self.result_state = QLabel("尚未计算")
        self.result_state.setStyleSheet("color:#475569;")
        exports.addWidget(self.result_state, 1)
        exports.addWidget(button("导出 CSV", self.export_data))
        self.export_target = QComboBox()
        self.export_target.setAccessibleName("导出图像类型")
        for label, key in (("当前光斑分析", "current"), ("光斑图", "spot"), ("剖面强度曲线", "profile"),
                           ("强度曲面", "surface"), ("包围能量", "energy"), ("轴向传播", "beam"), ("参数扫描", "scan"),
                           ("A/B 对比", "compare"), ("纵向强度", "longitudinal")):
            self.export_target.addItem(label, key)
        exports.addWidget(self.export_target)
        exports.addWidget(button("导出图片", self.export_plot))
        rv.addLayout(exports)
        splitter.addWidget(right)
        splitter.setSizes([340, 1130])
        root.addWidget(splitter, 1)
        self.status = QLabel("标量近轴模型 · 所有数值结果需按网格与窗口验证 · 元件外形为示意")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#475569;font-size:11px;")
        root.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        root.addWidget(self.progress)
        self.setCentralWidget(central)
        self.workspace.currentIndexChanged.connect(self.change_workspace)
        self.change_workspace(0)
        self.scan_plot.figure.text(.5, .5, "选择左侧元件及范围，点击开始扫描", ha="center")
        self.scan_plot.draw_idle()
        self.display_mode.setCurrentIndex(max(0, self.display_mode.findData(self.initial_display_mode)))
        self.display_mode.currentIndexChanged.connect(self.apply_display_mode)
        self.apply_display_mode()
        self.fill_project(preset("单透镜聚焦"))
        self.memory_timer = QTimer(self)
        self.memory_timer.setInterval(5000)
        self.memory_timer.timeout.connect(self.update_sampling_info)
        self.memory_timer.start()
        if auto_compute:
            self.preview_timer.start()

    def change_workspace(self, index):
        """共享输入和结果，只切换任务布局，不触发重新求解。"""
        self.scene_frame.setVisible(index == 0)
        self.main_views.setVisible(index != 2)
        self.bottom.setVisible(index != 0)
        self.scan_panel.setVisible(index == 2)
        self.source_panel.setVisible(index != 2)
        self.element_panel.setVisible(index != 2)
        if index == 2:
            self.bottom.setCurrentIndex(1)
        elif index == 1 and self.bottom.currentIndex() in (1, 2):
            self.bottom.setCurrentIndex(0)

    def reset_scene_view(self):
        if self.scene is not None:
            self.scene.reset_view()

    def release_memory_cache(self):
        """显式释放可重建的结果和显卡缓存，保留当前计算结果供查看与导出。"""
        if self.job and self.job.isRunning():
            self.status.setText("请等待当前计算完成后清空缓存。")
            return
        self.result_cache.clear()
        self.clear_baseline()
        self.longitudinal_result = None
        self.longitudinal_plot.figure.clear()
        cp = sys.modules.get("cupy")
        if cp is not None:
            try:
                cp.fft.config.get_plan_cache().clear()
                cp.get_default_memory_pool().free_all_blocks()
                cp.get_default_pinned_memory_pool().free_all_blocks()
            except RuntimeError:
                self.status.setText("结果缓存已清空；部分 CUDA 缓存未能释放。")
                return
        self.update_sampling_info()
        self.status.setText("已清空缓存和方案 A，保留当前结果；系统和驱动可能保留部分内存。")

    def apply_display_mode(self, *_):
        """按需创建三维上下文；退出三维时释放场景，计算模式不自动绘图。"""
        mode = self.display_mode.currentData()
        if self.settings is not None:
            self.settings.setValue("display_mode", mode)
        if mode != "3d" and self.scene is not None:
            old, self.scene = self.scene, None
            self.scene_stack.removeWidget(old.interactor)
            old.result = None
            old.clear()
            old.close()
            old.deleteLater()
        if mode == "3d":
            if self.scene is None:
                from .scene import OpticalScene
                self.scene = OpticalScene(self.scene_stack)
                self.scene_stack.addWidget(self.scene.interactor)
                if self.result is not None:
                    self.scene.set_result(self.result)
            self.scene_stack.setCurrentWidget(self.scene.interactor)
        else:
            self.scene_stack.setCurrentWidget(self.schematic_plot if mode == "2d" else self.compute_placeholder)
        self.tabs.setVisible(mode != "none")
        self.bottom.setVisible(mode != "none" and self.workspace.currentIndex() != 0)
        self.reset_view_button.setEnabled(mode == "3d")
        self.scene_caption.setText({"3d":"3D 光路 · r86 示意 · 横向 ×25", "2d":"2D 光路 · 无 VTK 渲染", "none":"仅计算 · 保留数值结果"}[mode])
        if mode == "none":
            self.longitudinal_result = None
            self.comparison = None
            for plot in (self.schematic_plot, self.spot_plot, self.profile_plot, self.surface_plot,
                         self.energy_plot, self.beam_plot, self.scan_plot, self.compare_plot, self.longitudinal_plot):
                plot.hide_data()
                plot.figure.clear()
                plot.ax = None
                plot.beam_result = None
                plot.draw_idle()
        if self.result is not None:
            self.draw_plane()
        if hasattr(self, "project_name"):
            self.update_sampling_info()

    def mark_dirty(self, *_):
        if not self.loading:
            self.update_sampling_info()
            self.revision += 1
            self.dirty = True
            if hasattr(self, "result_state"):
                self.result_state.setText("参数已修改 · 当前图为上次结果")
            if hasattr(self, "auto_preview") and self.auto_preview.isChecked():
                self.pending_preview = True
                self.preview_timer.start()
                if self.job and self.job.isRunning() and self.job.kind in ("simulate", "preview"):
                    self.job.cancel.set()

    def preview_toggled(self, enabled):
        if enabled:
            self.mark_dirty()
        else:
            self.preview_timer.stop()
            self.pending_preview = False
            if self.job and self.job.isRunning() and self.job.kind == "preview":
                self.job.cancel.set()

    def request_preview(self):
        if self.closing or not self.auto_preview.isChecked():
            return
        self.pending_preview = True
        if not self.job or not self.job.isRunning():
            self.launch_job("preview", automatic=True)

    def fill_project(self, p):
        self.loading = True
        self.project_name = p.name
        if self.presets.findText(p.name) >= 0:
            self.presets.setCurrentText(p.name)
        for widget, value in ((self.wave, p.wavelength*1e9), (self.waist, p.waist*1e3),
                              (self.waist_z, p.waist_z*1e3), (self.length, p.length*1e3),
                              (self.window_size, p.window*1e3), (self.samples, p.samples),
                              (self.memory_limit, p.memory_limit_mib),
                              (self.focus_refinement, p.focus_refinement)):
            widget.setValue(value)
        self.grid.setCurrentText(str(p.grid))
        self.storage_mode.setCurrentIndex(self.storage_mode.findData(p.storage_mode))
        for key in MODE_PRESET_KEYS:
            if mode_preset(key) == p.modes:
                self.mode_preset.setCurrentIndex(self.mode_preset.findData(key))
                break
        else:
            self.mode_preset.setCurrentIndex(-1)
        self.mode_table.setRowCount(0)
        for mode in p.modes:
            self.add_mode(mode)
        self.table.setRowCount(0)
        for e in p.elements:
            self.insert_element(e)
        self.loading = False
        self.refresh_targets()
        self.mark_dirty()

    def update_sampling_info(self, *_):
        if self.loading or not hasattr(self, "table") or not hasattr(self, "memory_info"):
            return
        dx = self.window_size.value() * 1000 / int(self.grid.currentText())
        dz = self.length.value() / (self.samples.value() - 1)
        self.sampling_info.setText(f"完整计算：Δx={dx:.3f} μm，Δz={dz:.3f} mm。\n自动预览最多 256×256 / 33 点；精细结果请点计算光场。")
        try:
            p = self.read_project(validate=False)
            if not np.isfinite(p.length) or p.length <= 0 or any(not np.isfinite(e.z) for e in p.elements):
                raise ValueError()
            estimate = estimate_memory(p)
        except (ValueError, AttributeError):
            self.memory_info.setText("请完成有效的参数输入后查看内存估算。")
            return
        system = system_memory()
        fmt = format_memory
        cpu = f"{fmt(estimate['cpu_increment_low_bytes'])}—{fmt(estimate['cpu_increment_high_bytes'])}"
        host = f"{fmt(estimate['cuda_host_low_bytes'])}—{fmt(estimate['cuda_host_high_bytes'])}"
        device = f"{fmt(estimate['cuda_device_low_bytes'])}—{fmt(estimate['cuda_device_high_bytes'])}"
        message = (f"结果数据：{fmt(estimate['result_bytes'])} / RAM 预算 {fmt(p.memory_limit_mib * 1024**2)}\n"
                   f"存储：{'磁盘缓存' if estimate['storage_mode'] == 'disk' else 'RAM'}；写入批次约 {fmt(estimate['resident_result_bytes'])}\n"
                   f"磁盘文件：{fmt(estimate['disk_bytes'])}（文件页缓存由系统管理）\n"
                   f"CPU 计算新增 RAM 约 {cpu}\nCUDA 计算新增 RAM 约 {host}\nCUDA 显存工作区约 {device}\n"
                   f"当前进程 RAM：{fmt(system['process_bytes'])}\n"
                   f"系统可用 RAM：{fmt(system['available_bytes'])} / 总量 {fmt(system['total_bytes'])}")
        message += f"\n显示：{self.display_mode.currentText()}"
        if self.display_mode.currentData() == "3d":
            message += "\n3D 场景/帧缓冲额外占用 RAM 和显存，可改为 2D 或仅计算。"
        if system["process_bytes"] is not None:
            message += f"\nCPU 进程峰值估计约 {fmt(system['process_bytes'] + estimate['cpu_increment_high_bytes'])}"
        if p.storage_mode == "ram" and estimate["result_bytes"] > p.memory_limit_mib * 1024**2:
            message += "\n结果超出上限：提高上限或减少采样后才能完整计算。"
            color = "#b91c1c"
        elif system["available_bytes"] is not None and estimate["cpu_increment_high_bytes"] > system["available_bytes"]:
            message += "\nCPU 估算超过当前可用 RAM，可能内存不足。"
            color = "#92400e"
        else:
            message += "\n运行范围为估算；保留旧结果、A/B、缓存与绘图会额外占用。"
            color = "#334155"
        self.memory_info.setText(message)
        style = f"color:{color};font-size:11px;"
        if self.memory_info.styleSheet() != style:
            self.memory_info.setStyleSheet(style)

    def add_mode(self, mode):
        row = self.mode_table.rowCount()
        if row >= 8:
            return
        self.mode_table.insertRow(row)
        family = QComboBox()
        family.addItems(["HG", "LG"])
        family.setCurrentText(mode.family)
        family.currentTextChanged.connect(self.mark_dirty)
        self.mode_table.setCellWidget(row, 0, family)
        for col, value in enumerate((mode.n, mode.m, mode.amplitude, mode.phase_deg), 1):
            self.mode_table.setItem(row, col, QTableWidgetItem(f"{value:.12g}"))
        self.mark_dirty()

    def remove_mode(self):
        row = self.mode_table.currentRow()
        if row >= 0 and self.mode_table.rowCount() > 1:
            self.mode_table.removeRow(row)
            self.mark_dirty()

    def apply_mode_preset(self):
        key = self.mode_preset.currentData()
        if key is None:
            return
        self.loading = True
        self.mode_table.setRowCount(0)
        for mode in mode_preset(key):
            self.add_mode(mode)
        self.loading = False
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
        diameter = QTableWidgetItem("" if e.clear_diameter is None else f"{e.clear_diameter*1e3:.12g}")
        if e.kind != "lens":
            diameter.setFlags(diameter.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 5, diameter)

    def read_project(self, validate=True):
        elements = []
        modes = []
        try:
            for row in range(self.mode_table.rowCount()):
                modes.append(Mode(self.mode_table.cellWidget(row, 0).currentText(),
                                  int(self.mode_table.item(row, 1).text()), int(self.mode_table.item(row, 2).text()),
                                  float(self.mode_table.item(row, 3).text()), float(self.mode_table.item(row, 4).text())))
        except (ValueError, AttributeError) as exc:
            raise ValueError("模式阶数须为整数，振幅与相位须为数值") from exc
        try:
            for row in range(self.table.rowCount()):
                diameter = self.table.item(row, 5).text().strip()
                elements.append(Element("lens" if self.table.item(row, 0).text() == "透镜" else "aperture",
                    float(self.table.item(row, 1).text())/1e3, float(self.table.item(row, 2).text())/1e3,
                    self.table.item(row, 3).text(), self.table.item(row, 4).checkState() == Qt.Checked,
                    float(diameter)/1e3 if diameter else None))
        except (ValueError, AttributeError) as exc:
            raise ValueError("元件位置与焦距/直径须为数值，透镜口径可留空") from exc
        project = Project(self.project_name, self.wave.value()*1e-9, self.waist.value()*1e-3,
                       self.waist_z.value()*1e-3, self.length.value()*1e-3, self.window_size.value()*1e-3,
                       int(self.grid.currentText()), self.samples.value(), elements, self.focus_refinement.value(),
                       modes=modes, memory_limit_mib=self.memory_limit.value(), storage_mode=self.storage_mode.currentData())
        return project.validate() if validate else project

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

    def launch_job(self, kind, options=None, automatic=False):
        if self.job and self.job.isRunning():
            return
        if self.job:
            # finished 信号入队与线程 TLS 析构并不同时完成；替换任务引用前也必须等待。
            self.job.wait()
            self.job.release_cuda_cache()
        self.play_timer.stop()
        self.play_button.setText("播放传播")
        try:
            p = self.read_project()
        except Exception as exc:
            if automatic:
                self.status.setText("等待有效参数：" + str(exc))
                self.pending_preview = False
            else:
                self.show_error(str(exc))
            return
        self.preview_timer.stop()
        self.pending_preview = False
        self.pending_full = False
        actual = preview_project(p) if kind == "preview" else p
        self.job = Job(kind, actual, options, self.backend_choice.currentData(), self.revision, self.result_cache)
        self.job.request_project = p
        self.job.completed.connect(self.job_done, Qt.QueuedConnection)
        self.job.failed.connect(self.job_failed)
        self.job.progress.connect(self.progress.setValue)
        self.job.finished.connect(self.job_finished, Qt.QueuedConnection)
        self.run_button.setEnabled(kind == "preview")
        self.scan_button.setEnabled(False)
        self.convergence_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self.status.setText("预览更新中 · 可继续修改参数" if kind == "preview" else "完整任务计算中 · 可继续操作视图")
        self.job.start()

    def compute(self):
        self.preview_timer.stop()
        self.pending_preview = False
        if self.job and self.job.isRunning():
            self.pending_full = True
            self.job.cancel.set()
            return
        self.launch_job("simulate")

    def start_scan(self):
        self.launch_job("scan", (self.scan_target.currentIndex(), self.scan_low.value()*1e-3,
                                 self.scan_high.value()*1e-3, self.scan_count.value()))

    def start_convergence(self):
        self.launch_job("convergence")

    def cancel_job(self):
        self.preview_timer.stop()
        self.pending_preview = self.pending_full = False
        if self.job:
            self.job.cancel.set()

    @Slot()
    def job_finished(self):
        job = self.sender()
        if isinstance(job, Job):
            job.wait()
            job.release_cuda_cache()
        self.run_button.setEnabled(True)
        self.scan_button.setEnabled(True)
        self.convergence_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if not self.closing:
            if self.pending_full:
                QTimer.singleShot(0, self.compute)
            elif self.pending_preview and self.auto_preview.isChecked() and not self.preview_timer.isActive():
                self.preview_timer.start(1)

    def job_failed(self, message):
        self.status.setText(message)
        if "已取消" not in message and self.job.kind != "preview":
            self.show_error(message)

    @Slot(object)
    def job_done(self, result):
        if self.job.kind in ("simulate", "preview") and self.job.revision is not None and self.job.revision != self.revision:
            return
        try:
            self.dirty = self.read_project() != self.job.request_project
        except ValueError:
            self.dirty = True
        if self.job.kind == "scan":
            self.scan_rows = result
            self.scan_project = self.job.project.clone()
            self.scan_options = self.job.options
            kind = self.job.project.elements[self.job.options[0]].kind
            if self.display_mode.currentData() != "none":
                self.scan_plot.scanning(result, kind)
            self.scan_table.setColumnCount(6)
            self.scan_table.setHorizontalHeaderLabels(["参数/mm", "最小r86/μm", "焦点/mm", "透过率/%", "状态", "说明"])
            self.scan_table.setRowCount(len(result))
            for row, item in enumerate(result):
                for col, value in enumerate((f"{item['value_m']*1e3:.3f}", f"{item['min_r86_m']*1e6:.2f}",
                    f"{item['focus_z_m']*1e3:.2f}", f"{item['transmission']*100:.2f}", item["status"], item["note"])):
                    self.scan_table.setItem(row, col, QTableWidgetItem(value))
            self.scan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.workspace.setCurrentIndex(2)
            self.bottom.setCurrentIndex(1)
            self.status.setText(f"扫描完成 · {len(result)} 点 · 末片透镜后搜索并局部细化；警告点需复核 · CSV 保留警告")
        elif self.job.kind == "convergence":
            self.last_convergence = result
            changes = result["changes"]
            self.status.setText("焦区 r86 变化：" + "；".join(
                f"{label} {changes[key]['focus_r86_m_relative']:.2%} / 位置 {changes[key]['focus_z_absolute_m']*1e3:.3f} mm"
                for key, label in (("grid", "网格"), ("window", "窗口"), ("axial", "轴向"))) +
                "。远场、透过率与剖面见 outputs/convergence.json；变化不等于误差认证")
            Path("outputs").mkdir(exist_ok=True)
            Path("outputs/convergence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            changed = self.result is not result
            self.result = result
            if changed:
                if self.longitudinal_result is not None:
                    self.longitudinal_result = None
                    self.longitudinal_plot.reset()
                    self.longitudinal_plot.draw_idle()
                if self.scene is not None:
                    self.scene.set_result(result)
            ref = result.reference
            k = result.focus_index
            self.cards[0].setText(f"高斯参考束腰 / 全局 z\n{ref['waist']*1e6:.1f} μm  /  {ref['waist_z']*1e3:.1f} mm")
            self.cards[1].setText(f"最小光斑 r86 / 位置\n{result.r86[k]*1e6:.1f} μm  /  {result.z[k]*1e3:.1f} mm")
            self.cards[1].setToolTip(f"焦区细化 {result.focus['levels']} 级；括区宽 {result.focus['axial_bracket_width_m']*1e3:.4f} mm。横向分位平台仍需复核。")
            self.cards[2].setText(f"参考 θ / 衍射 θ86\n{ref['divergence']*1e3:.2f} / {result.theta86*1e3:.2f} mrad")
            self.cards[3].setText(f"系统透过率 / 末端\n{result.transmission[-1]*100:.2f} %")
            if changed:
                self.plane_slider.blockSignals(True)
                self.plane_slider.setRange(0, len(result.z)-1)
                self.plane_slider.setValue(k)
                self.plane_slider.blockSignals(False)
                self.draw_plane()
            self.status.setText("；".join(result.warnings) if result.warnings else
                                "计算完成 · 采样诊断无明显异常；尚需网格与窗口收敛验证 · 高斯与 r86 指标不同")
            self.bottom.setCurrentIndex(0)
        if self.job.kind == "scan":
            self.result_state.setText("扫描为任务参数快照 · 主场景与指标卡保留上次光场结果")
        elif self.job.kind == "convergence":
            self.result_state.setText("收敛检查使用独立参数快照 · 主场景仍为上次光场结果")
        else:
            backend = result.provenance.get("backend", {})
            quality = "快速预览 · 未完成精度验证" if self.job.kind == "preview" else "完整计算"
            self.result_state.setText("参数已修改 · 显示任务快照结果" if self.dirty else
                f"{quality} · N={result.project.grid} · {backend.get('used', 'cpu').upper()}" +
                (" · 复用缓存" if self.job.cache_hit else ""))
            self.result_state.setToolTip(backend.get("reason", ""))
        self.progress.setValue(100)

    def draw_plane(self, *_):
        if self.result is None:
            return
        r = self.result
        i = min(self.plane_slider.value(), len(r.z)-1)
        self.plane_label.setText(f"{r.z[i]*1e3:.2f} mm · r86={r.r86[i]*1e6:.1f} μm")
        mode = self.display_mode.currentData()
        if mode == "none":
            return
        if self.scene is not None:
            self.scene.set_plane(i, log=self.log_scale.isChecked(), smooth=self.spot_render.isChecked())
        elif mode == "2d":
            self.schematic_plot.schematic(r, i)
        if self.tabs.currentIndex() == 0:
            self.spot_plot.spot(r, i, self.log_scale.isChecked(), smooth=self.spot_render.isChecked())
        elif self.tabs.currentIndex() == 1:
            self.profile_plot.profile(r, i)
        elif self.tabs.currentIndex() == 2:
            self.surface_plot.intensity_surface(r, i)
        else:
            self.energy_plot.energy(r, i)
        self.beam_plot.beam(r, i)

    def request_plane_draw(self, *_):
        if self.result is None:
            return
        i = min(self.plane_slider.value(), len(self.result.z) - 1)
        self.plane_label.setText(f"{self.result.z[i]*1e3:.2f} mm · r86={self.result.r86[i]*1e6:.1f} μm")
        if self.plane_slider.isSliderDown():
            if not self.plane_timer.isActive():
                self.plane_timer.start()
        else:
            self.draw_plane()

    def locate_focus(self):
        if self.result is not None:
            if self.result.provenance.get("quality") == "preview":
                self.compute()
                self.status.setText("正在用完整采样计算焦面；快速预览不用于判断小光斑形状。")
                return
            self.plane_slider.setValue(self.result.focus_index)

    def full_snapshot(self):
        if (self.result is None or self.dirty or
                self.result.provenance.get("quality") == "preview"):
            raise ValueError("请先对当前参数完成一次光场计算")
        return self.result

    def pin_baseline(self):
        try:
            self.baseline = self.full_snapshot()
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.clear_comparison()
        self.baseline_label.setText(f"A · {self.baseline.project.name} · N={self.baseline.project.grid}")

    def clear_comparison(self):
        self.comparison = None
        self.compare_plot.figure.clear()
        self.compare_plot.draw_idle()

    def clear_baseline(self):
        self.baseline = None
        self.baseline_label.setText("尚未固定方案 A")
        self.clear_comparison()

    def compare_results(self):
        try:
            a, b = self.baseline, self.full_snapshot()
            if a is None:
                raise ValueError("请先固定方案 A")
            mode = self.compare_mode.currentText()
            if self.compare_mode.currentIndex() == 1:
                i, j = a.focus_index, b.focus_index
            else:
                # 只比较双方实际采样面；容差用于消除坐标浮点舍入差异。
                ia = np.abs(a.z[:, None] - b.z[None, :]).argmin(axis=0)
                common = np.flatnonzero(np.abs(a.z[ia] - b.z) <= 1e-12)
                if not len(common):
                    raise ValueError("没有共同采样面，请统一传播长度与轴向采样")
                target = b.z[self.plane_slider.value()]
                j = int(common[np.argmin(np.abs(b.z[common] - target))])
                i = int(ia[j])
            self.compare_plot.compare(a, i, b, j, mode)
            self.comparison = a, i, b, j, mode
            self.status.setText(f"对比已生成 · A {a.z[i]*1e3:.3f} mm · B {b.z[j]*1e3:.3f} mm")
        except ValueError as exc:
            self.status.setText(str(exc))

    def show_longitudinal(self):
        if self.result is None or self.dirty:
            self.status.setText("请先更新当前光场结果")
            return
        self.longitudinal_result = self.result
        self.longitudinal_plot.longitudinal(self.result)
        quality = "快速预览" if self.result.provenance.get("quality") == "preview" else "完整计算"
        self.longitudinal_plot.figure.suptitle(f"{quality} · N={self.result.project.grid}")

    def locate_longitudinal_plane(self, event):
        if event.inaxes is not self.longitudinal_plot.ax or event.xdata is None:
            return
        if self.longitudinal_result is not self.result:
            self.status.setText("请用当前结果重新生成纵向强度图")
            return
        self.plane_slider.setValue(int(np.argmin(abs(self.result.z - event.xdata * 1e-3))))

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
            if is_scan and not self.scan_rows:
                raise ValueError("当前扫描页没有结果，请先完成扫描")
            if not is_scan and self.result is None:
                raise ValueError("请先完成计算")
            snapshot = self.result
            preview = snapshot is not None and snapshot.provenance.get("quality") == "preview"
            filename = "scan.csv" if is_scan else "propagation-preview.csv" if preview else "propagation.csv"
            path = self.choose_path("导出计算快照数据", filename, "CSV (*.csv)")
            if path:
                if is_scan:
                    export_csv(self.scan_rows, path)
                    save_project(self.scan_project, str(Path(path).with_suffix(".project.json")))
                    Path(path + ".meta.json").write_text(json.dumps({"element_index": self.scan_options[0],
                        "low_m": self.scan_options[1], "high_m": self.scan_options[2], "count": self.scan_options[3],
                        "algorithm_version": ALGORITHM_VERSION,
                        "project": asdict(self.scan_project),
                        "metric": "末片透镜后粗搜索与局部细化的最小 r86；警告点需复核"},
                        ensure_ascii=False, indent=2), encoding="utf-8")
                else:
                    export_result(snapshot, path, getattr(self, "last_convergence", None))
                self.status.setText("已导出数据和对应参数快照：" + path)
        except Exception as exc:
            self.show_error(str(exc))

    def export_named(self, key):
        """就地图表导出指定对象，保留全局导出选择。"""
        previous = self.export_target.currentIndex()
        try:
            self.export_target.setCurrentIndex(self.export_target.findData(key))
            self.export_plot()
        finally:
            self.export_target.setCurrentIndex(previous)

    def export_bottom(self):
        """数据表导出 CSV，其余页导出所见图像。"""
        if self.bottom.currentIndex() == 2:
            self.export_data()
        else:
            self.export_named(("beam","scan","scan","compare","longitudinal")[self.bottom.currentIndex()])

    def export_plot(self):
        """按明确选择导出结果快照，支持未打开过的分析标签和白底矢量图。"""
        try:
            preview = False
            key = self.export_target.currentData()
            if key == "current":
                key = ("spot", "profile", "surface", "energy")[self.tabs.currentIndex()]
            labels = {"spot": "光斑图", "profile": "剖面强度曲线", "surface": "强度曲面",
                      "energy": "包围能量", "beam": "轴向传播", "scan": "参数扫描",
                      "compare": "A/B 对比", "longitudinal": "纵向强度"}
            if key == "compare":
                comparison = self.comparison
                if comparison is None:
                    raise ValueError("请先生成 A/B 对比")
                plot = self.compare_plot
            elif key == "longitudinal":
                r = self.longitudinal_result
                if r is None:
                    raise ValueError("请先生成纵向强度图")
                preview = r.provenance.get("quality") == "preview"
                plot = self.longitudinal_plot
            elif key == "scan":
                if not self.scan_rows:
                    raise ValueError("请先完成参数扫描")
                kind = self.scan_project.elements[self.scan_options[0]].kind
                scan_rows = self.scan_rows
                self.scan_plot.scanning(scan_rows, kind)
                plot = self.scan_plot
            else:
                if self.result is None:
                    raise ValueError("请先完成光场计算")
                r = self.result
                preview = r.provenance.get("quality") == "preview"
                logarithmic = self.log_scale.isChecked()
                smooth = self.spot_render.isChecked()
                index = min(self.plane_slider.value(), len(r.z) - 1)
                plot = {"spot": self.spot_plot, "profile": self.profile_plot, "surface": self.surface_plot,
                        "energy": self.energy_plot, "beam": self.beam_plot}[key]
                if key == "spot":
                    plot.spot(r, index, logarithmic, smooth=smooth)
                else:
                    method = {"profile": "profile", "surface": "intensity_surface", "energy": "energy", "beam": "beam"}[key]
                    getattr(plot, method)(r, index)
            axis_limits = copy.deepcopy(plot.axis_limits)
            path = self.choose_path("导出" + labels[key], key + ("-preview.png" if preview else ".png"), "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)")
            if path:
                # 文件对话框打开期间允许自动预览继续，导出使用独立画布固定调用时的快照。
                plot = PlotCanvas(surface=key == "surface")
                plot.axis_limits = axis_limits
                if key == "compare":
                    plot.figure.set_size_inches(10, 7)
                    plot.compare(*comparison)
                elif key == "longitudinal":
                    plot.longitudinal(r)
                elif key == "scan":
                    plot.scanning(scan_rows, kind)
                elif key == "spot":
                    plot.spot(r, index, logarithmic, smooth=smooth)
                else:
                    method = {"profile": "profile", "surface": "intensity_surface", "energy": "energy", "beam": "beam"}[key]
                    getattr(plot, method)(r, index)
                snapshot_title = plot.figure.suptitle(f"快速预览 · N={r.project.grid} · 未完成精度验证") if preview else None
                labels_to_keep = []
                for axes in plot.figure.axes:
                    labels_to_keep.extend((axes.xaxis.label, axes.yaxis.label, axes.title))
                    if hasattr(axes, "zaxis"):
                        labels_to_keep.append(axes.zaxis.label)
                if snapshot_title is not None:
                    labels_to_keep.append(snapshot_title)
                try:
                    plot.figure.savefig(path, dpi=300, facecolor="white", edgecolor="white", transparent=False,
                                        bbox_inches="tight", pad_inches=.15, bbox_extra_artists=labels_to_keep)
                finally:
                    plot.close()
                    plot.deleteLater()
                self.status.setText("已导出白底" + labels[key] + "：" + path)
        except Exception as exc:
            self.show_error(str(exc))

    def screenshot(self):
        if self.result is None:
            return
        path = self.choose_path("保存三维场景", "scene.png", "PNG (*.png)")
        if path:
            if self.scene is not None:
                self.scene.screenshot(path)
            elif self.display_mode.currentData() == "2d":
                self.schematic_plot.figure.savefig(path, dpi=300, facecolor="white")
            else:
                self.status.setText("仅计算模式没有场景图，可切换到 2D 或 3D。")
                return
            self.status.setText("已保存场景：" + path)

    def closeEvent(self, event):
        self.closing = True
        self.preview_timer.stop()
        self.plane_timer.stop()
        self.play_timer.stop()
        self.memory_timer.stop()
        if self.job and self.job.isRunning():
            self.job.cancel.set()
            self.job.wait()
        if self.job:
            self.job.release_cuda_cache()
        if self.scene is not None:
            self.scene.close()
        super().closeEvent(event)


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
