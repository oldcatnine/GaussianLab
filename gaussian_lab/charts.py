"""二维分析图和强度曲面，读取计算结果并生成可导出的图像。"""
import numpy as np
import weakref
from .optics import radial_energy
from .model import input_mode_label
from .theme import BACKGROUND, TEXT, BORDER, BLUE, ORANGE, INTENSITY_CMAP
from matplotlib import rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QToolTip, QPushButton
from PySide6.QtGui import QCursor

rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
                 "axes.unicode_minus": False, "font.size": 9})


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, surface=False):
        self.figure = Figure(facecolor=BACKGROUND, layout="constrained")
        super().__init__(self.figure)
        self.surface = surface
        self.ax = None
        self.hover_data = None
        self.axis_limits = {}
        self._axis_defaults = weakref.WeakKeyDictionary()
        self.axes_button = QPushButton("坐标轴…", self)
        self.axes_button.setToolTip("调整本图各子图的横轴、纵轴范围；支持恢复自动范围。")
        self.axes_button.clicked.connect(self.edit_axes)
        self.axes_button.setGeometry(max(0, self.width()-86), 2, 82, 26)
        self.mpl_connect("motion_notify_event", self.show_nearest_data)
        self.mpl_connect("figure_leave_event", self.hide_data)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "axes_button"):
            self.axes_button.move(max(0, self.width()-86), 2)

    def data_axes(self):
        """仅编辑数据坐标，不将颜色条当作曲线子图。"""
        return [ax for ax in self.figure.axes if ax.get_label() != "<colorbar>"]

    def draw_idle(self):
        """每次重绘恢复本次自动范围，再应用会话内独立的用户范围。"""
        axes = self.data_axes()
        # 先读取全部自动范围，避免共享轴在逐个应用时污染后续子图的默认值。
        for ax in axes:
            names = ("x", "y", "z") if ax.name == "3d" else ("x", "y")
            if ax not in self._axis_defaults:
                self._axis_defaults[ax] = {name: getattr(ax, f"get_{name}lim")() for name in names}
        for index, ax in enumerate(axes):
            names = ("x", "y", "z") if ax.name == "3d" else ("x", "y")
            for name in names:
                limits = self.axis_limits.get(index, {}).get(name, self._axis_defaults[ax][name])
                getattr(ax, f"set_{name}lim")(*limits)
        super().draw_idle()

    def set_axis_ranges(self, index, ranges):
        """先校验所有输入再应用；共享坐标同步，防止双轴覆盖冲突。"""
        axes = self.data_axes()
        ax = axes[index]
        parsed = {}
        for name, limits in ranges.items():
            if name not in (("x", "y", "z") if ax.name == "3d" else ("x", "y")):
                raise ValueError("未知坐标轴")
            if limits is None:
                continue
            low, high = map(float, limits)
            if not np.isfinite([low, high]).all() or low >= high:
                raise ValueError("坐标范围须为有限数值，且最小值小于最大值")
            if getattr(ax, f"get_{name}scale")() == "log" and low <= 0:
                raise ValueError("对数坐标的最小值须大于零")
            parsed[name] = (low, high)
        for name in ranges:
            for other_index, other in enumerate(axes):
                shared = name in ("x", "y") and getattr(ax, f"get_shared_{name}_axes")().joined(ax, other)
                if other is ax or shared:
                    self.axis_limits.setdefault(other_index, {}).pop(name, None)
                    if name in parsed:
                        self.axis_limits[other_index][name] = parsed[name]
        self.draw_idle()

    def edit_axes(self):
        """以非模态中文窗口编辑各数据子图，关闭窗口不影响计算。"""
        if not self.data_axes():
            QToolTip.showText(QCursor.pos(), "请先生成此图的数据。", self)
            return
        from .axis_editor import AxisEditor
        if getattr(self, "axis_editor", None) is not None:
            self.axis_editor.close()
        self.axis_editor = AxisEditor(self)
        editor = self.axis_editor
        editor.destroyed.connect(lambda: setattr(self, "axis_editor", None)
                                if self.axis_editor is editor else None)
        self.axis_editor.show()

    def hide_data(self, event=None):
        """悬停提示使用 Qt 浮窗，不写进导出的图形。"""
        self.hover_data = None
        QToolTip.hideText()

    def show_nearest_data(self, event):
        """按屏幕像素距离查找真实曲线采样点，兼容双纵轴和多子图。"""
        if event.inaxes is None or event.x is None or event.y is None:
            self.hide_data()
            return
        best = None
        for ax in self.figure.axes:
            if ax.name == "3d" or not ax.bbox.contains(event.x, event.y):
                continue
            for line in ax.lines:
                if not line.get_visible() or line.get_transform() is not ax.transData:
                    continue
                values = np.asarray(line.get_xydata(), dtype=float)
                valid = np.isfinite(values).all(axis=1)
                if not valid.any():
                    continue
                points = values[valid]
                screen = ax.transData.transform(points)
                distances = np.hypot(screen[:, 0] - event.x, screen[:, 1] - event.y)
                k = int(np.argmin(distances))
                if distances[k] <= 12 and (best is None or distances[k] < best[0]):
                    label = line.get_label()
                    if label.startswith("_"):
                        label = "曲线"
                    best = float(distances[k]), ax, label, points[k]
        if best is None:
            if event.inaxes.images and event.xdata is not None and event.ydata is not None:
                image = event.inaxes.images[0]
                data = image.get_array()
                left, right, bottom, top = image.get_extent()
                col = int(np.floor((event.xdata - left) / (right - left) * data.shape[1]))
                row = int(np.floor((event.ydata - bottom) / (top - bottom) * data.shape[0]))
                if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                    x = left + (col + .5) * (right - left) / data.shape[1]
                    y = bottom + (row + .5) * (top - bottom) / data.shape[0]
                    value = float(data[row, col])
                    self.hover_data = {"label": "像素强度", "x": x, "y": y, "value": value, "row": row, "col": col}
                    QToolTip.showText(QCursor.pos(), f"采样点 x={x:.7g}，y={y:.7g}\n显示强度={value:.7g}\n"
                                     f"{event.inaxes.get_xlabel()} / {event.inaxes.get_ylabel()}", self)
                    return
            self.hide_data()
            return
        _, ax, label, (x, y) = best
        xlabel = ax.get_xlabel() or next((a.get_xlabel() for a in ax.get_shared_x_axes().get_siblings(ax) if a.get_xlabel()), "横坐标")
        self.hover_data = {"label": label, "x": float(x), "y": float(y),
                           "xlabel": xlabel, "ylabel": ax.get_ylabel()}
        QToolTip.showText(QCursor.pos(), f"{label}\n{xlabel}：{x:.7g}\n"
                          f"{ax.get_ylabel() or '纵坐标'}：{y:.7g}", self)

    def reset(self):
        self.hide_data()
        self.figure.clear()
        self.ax = self.figure.add_subplot(111, projection="3d" if self.surface else None)
        self.ax.set_facecolor(BACKGROUND)
        self.ax.tick_params(colors=TEXT, labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(BORDER)
        self.ax.xaxis.label.set_color(TEXT)
        self.ax.yaxis.label.set_color(TEXT)
        self.ax.title.set_color(TEXT)
        if self.surface:
            for axis in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
                axis.set_pane_color((1, 1, 1, 1))
                axis.line.set_color(BORDER)
                axis.label.set_color(TEXT)
            self.ax.tick_params(axis="z", colors=TEXT)
        return self.ax

    def beam(self, r, index):
        if getattr(self, "beam_result", None) is r and self.ax is not None:
            self.beam_cursor.set_xdata([r.z[index] * 1e3] * 2)
            self.draw_idle()
            return
        ax = self.reset()
        self.beam_result = r
        ax.plot(r.z * 1e3, r.gaussian_w * 1e6, color=BLUE, lw=1.7, label="理想高斯参考 w")
        ax.plot(r.z * 1e3, r.r86 * 1e6, color=ORANGE, lw=1.5, label="衍射 r86")
        self.beam_cursor = ax.axvline(r.z[index] * 1e3, color="#64748b", ls="--", lw=.9)
        for e in r.project.ordered():
            ax.axvline(e.z * 1e3, color="#94a3b8", alpha=.5, lw=.7)
        ax.set(xlabel="传播位置 z / mm", ylabel="半径 / μm")
        ax.grid(alpha=.45, color=BORDER)
        ax.legend(facecolor=BACKGROUND, edgecolor=BORDER, labelcolor=TEXT, fontsize=8)
        self.draw_idle()

    def spot(self, r, index, log=False, smooth=True):
        ax = self.reset()
        image = r.intensity[index]
        image = image / max(float(image.max()), 1e-30)
        if log:
            image = 10 * np.log10(np.maximum(image, 1e-6))
        dx = r.project.window / r.project.grid
        extent = [(r.x[0] - dx / 2) * 1e3, (r.x[-1] + dx / 2) * 1e3] * 2
        plot = ax.imshow(image, origin="lower", extent=extent, cmap=INTENSITY_CMAP,
                         vmin=-50 if log else 0, vmax=0 if log else 1,
                         interpolation="bilinear" if smooth else "nearest", interpolation_stage="data", aspect="equal")
        limit = max(r.r86[index] * 2.2, 4 * dx) * 1e3
        limit = min(limit, r.project.window * 500)
        ax.set(xlim=(-limit, limit), ylim=(-limit, limit), xlabel="x / mm", ylabel="y / mm",
               title=f"{input_mode_label(r.project)}\nz = {r.z[index]*1e3:.4f} mm · 峰值归一化" + (" / dB" if log else ""))
        diameter_pixels = 2 * r.r86[index] / dx
        quality = "平滑仅改善显示；计算值未改变" if smooth else "原始像素，不做平滑插值"
        if diameter_pixels < 8:
            quality += "；采样偏粗，请完整计算/加密网格"
        ax.text(.02, .02, f"Δx={dx*1e6:.3f} μm · 2r86≈{diameter_pixels:.1f} 像素\n{quality}",
                transform=ax.transAxes, fontsize=7, va="bottom", bbox={"facecolor":"white", "alpha":.85, "edgecolor":"none"})
        cb = self.figure.colorbar(plot, ax=ax, shrink=.8, pad=.025)
        cb.ax.tick_params(colors=TEXT, labelsize=7)
        self.draw_idle()

    def profile(self, r, index):
        ax = self.reset()
        center = r.project.grid // 2
        image = r.intensity[index]
        peak = max(float(image.max()), 1e-30)
        ax.plot(r.x * 1e3, image[center] / peak, color=BLUE, label="x 剖面")
        ax.plot(r.x * 1e3, image[:, center] / peak, color=ORANGE, ls="--", label="y 剖面")
        limit = min(max(r.r86[index] * 2.2, 4 * r.project.window/r.project.grid) * 1e3, r.project.window * 500)
        ax.set(xlim=(-limit, limit), xlabel="横向位置 / mm", ylabel="峰值归一化强度",
               title=f"z = {r.z[index]*1e3:.2f} mm · 中心剖面")
        ax.grid(alpha=.45)
        ax.legend(facecolor=BACKGROUND, labelcolor=TEXT)
        self.draw_idle()

    def intensity_surface(self, r, index):
        ax = self.reset()
        image = r.intensity[index]
        limit = min(max(r.r86[index] * 2, 4 * r.project.window/r.project.grid) * 1e3, r.project.window * 500)
        m = np.abs(r.x * 1e3) <= limit
        step = max(1, int(m.sum()) // 50)
        xx, yy = np.meshgrid(r.x[m][::step] * 1e3, r.x[m][::step] * 1e3)
        ii = image[np.ix_(m, m)][::step, ::step]
        ax.plot_surface(xx, yy, ii / max(float(ii.max()), 1e-30), cmap=INTENSITY_CMAP,
                        linewidth=0, antialiased=True, rcount=60, ccount=60)
        ax.set(xlabel="x / mm", ylabel="y / mm", zlabel="I / Imax", title=f"z = {r.z[index]*1e3:.2f} mm · 强度曲面")
        ax.view_init(28, -55)
        self.draw_idle()

    def scanning(self, rows, kind):
        ax = self.reset()
        values = np.array([r["value_m"] for r in rows]) * 1e3
        sizes = np.array([r["min_r86_m"] for r in rows]) * 1e6
        ax.plot(values, sizes, "o-", color=ORANGE, ms=4, label="末片透镜后最小 r86")
        ax.set(xlabel=("焦距 f / mm" if kind == "lens" else "光阑直径 / mm"), ylabel="最小 r86 / μm")
        ax.grid(alpha=.45)
        ax2 = ax.twinx()
        ax2.plot(values, [r["transmission"] * 100 for r in rows], color=BLUE, ls="--", label="透过率")
        ax2.set_ylabel("透过率 / %", color=BLUE)
        ax2.set_ylim(0, 105)
        ax2.tick_params(colors=BLUE, labelsize=8)
        self.draw_idle()


    def energy(self, r, index):
        """显示包围能量分布，用于比较光阑引起的主斑与外侧能量变化。"""
        ax = self.reset()
        radius = np.sqrt(np.add.outer(r.x**2, r.x**2))
        radii, fraction = radial_energy(r.intensity[index], radius)
        ax.plot(radii * 1e6, fraction * 100, color=BLUE, label="包围能量")
        ax.axhline(86, color=ORANGE, ls="--", lw=.9)
        ax.axvline(r.r86[index] * 1e6, color=ORANGE, ls="--", lw=.9)
        ax.set(xlabel="距光轴半径 / μm", ylabel="包围能量 / %", ylim=(0, 101),
               xlim=(0, min(r.project.window / 2, r.r86[index] * 4) * 1e6),
               title=f"z = {r.z[index]*1e3:.2f} mm · 虚线为 r86")
        ax.grid(alpha=.45)
        self.draw_idle()

    def compare(self, a, i, b, j, mode, view=0):
        """采用相同入射功率标尺，并保留各方案独立的包围能量百分比。"""
        self.hide_data()
        self.figure.clear()
        self.ax = None
        pairs = ((a, i, "A", BLUE), (b, j, "B", ORANGE))
        images = [r.intensity[k] / r.provenance["input_power_integral"] / 1e6
                  for r, k, _, _ in pairs]
        peak = max(float(image.max()) for image in images)
        limit = max(min(max(r.r86[k] * 3, .15e-3), r.project.window / 2)
                    for r, k, _, _ in pairs) * 1e3
        if view == 0:
            axes = self.figure.subplots(1, 2, sharex=True, sharey=True)
            for (r, k, name, _), image, ax in zip(pairs, images, axes):
                dx = r.project.window / r.project.grid
                extent = [(r.x[0] - dx / 2) * 1e3, (r.x[-1] + dx / 2) * 1e3] * 2
                plot = ax.imshow(image, origin="lower", extent=extent, cmap=INTENSITY_CMAP,
                                 vmin=0, vmax=peak, interpolation="nearest")
                ax.set(xlim=(-limit, limit), ylim=(-limit, limit), xlabel="x / mm", ylabel="y / mm",
                       title=f"{name} · z={r.z[k]*1e3:.3f} mm · 透过率 {r.transmission[k]:.1%}")
            self.figure.colorbar(plot, ax=axes, label=r"单位入射功率的强度 / $\mathrm{mm}^{-2}$")
        else:
            ax = self.figure.subplots()
            for (r, k, name, color), image in zip(pairs, images):
                if view == 1:
                    ax.plot(r.x * 1e3, image[r.project.grid // 2], color=color, label=name)
                else:
                    radii, fraction = radial_energy(image, np.sqrt(np.add.outer(r.x**2, r.x**2)))
                    ax.plot(radii * 1e3, fraction * 100, color=color, label=f"{name} · r86 {r.r86[k]*1e6:.1f} μm")
            if view == 1:
                ax.set(xlim=(-limit, limit), xlabel="x / mm", ylabel=r"中心剖面 / $\mathrm{mm}^{-2}$")
            else:
                ax.set(xlim=(0, limit), ylim=(0, 101), xlabel="距光轴半径 / mm", ylabel="各自观察面的包围能量 / %")
            ax.grid(alpha=.35)
            ax.legend()
        self.figure.suptitle(mode)
        self.draw_idle()

    def longitudinal(self, r):
        """从已计算场提取中心剖面，保持轴向采样的实际间距。"""
        ax = self.reset()
        image = r.intensity[:, r.project.grid // 2, :]
        db = 10 * np.log10(np.maximum(image / max(float(image.max()), 1e-30), 1e-5))
        plot = ax.pcolormesh(r.z * 1e3, r.x * 1e3, db.T, shading="nearest",
                             cmap=INTENSITY_CMAP, vmin=-50, vmax=0)
        ax.set(xlabel="传播位置 z / mm", ylabel="横向位置 x / mm",
               title="中心剖面 · 全图峰值归一化")
        self.figure.colorbar(plot, ax=ax, label="相对强度 / dB")
        self.draw_idle()

    def schematic(self, r, index):
        """轻量二维光路示意，不使用 VTK；轮廓为 r86，不能替代真实光斑。"""
        ax = self.reset()
        z, radius = r.z * 1e3, r.r86 * 1e3
        ax.fill_between(z, -radius, radius, color=BLUE, alpha=.12)
        ax.plot(z, radius, color=BLUE, label="r86 上边界")
        ax.plot(z, -radius, color=BLUE, label="r86 下边界")
        ax.axhline(0, color="#94a3b8", lw=.7)
        for e in r.project.ordered():
            ax.axvline(e.z*1e3, color=ORANGE if e.kind == "aperture" else "#64748b", ls="--", lw=1)
            ax.text(e.z*1e3, .95, e.label, transform=ax.get_xaxis_transform(), ha="center", va="top")
        ax.axvline(z[index], color=ORANGE, label="观察面")
        ax.set(xlabel="传播位置 z / mm", ylabel="距光轴 / mm", title="二维光路 · r86 示意，真实光斑见右侧")
        ax.grid(alpha=.3)
        self.draw_idle()
