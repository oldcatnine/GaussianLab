"""二维分析图和强度曲面，读取计算结果并生成可导出的图像。"""
import numpy as np
from .optics import radial_energy
from .theme import BACKGROUND, TEXT, BORDER, BLUE, ORANGE, INTENSITY_CMAP
from matplotlib import rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
                 "axes.unicode_minus": False, "font.size": 9})


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, surface=False):
        self.figure = Figure(facecolor=BACKGROUND, layout="constrained")
        super().__init__(self.figure)
        self.surface = surface
        self.ax = None

    def reset(self):
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

    def spot(self, r, index, log=False):
        ax = self.reset()
        image = r.intensity[index]
        image = image / max(float(image.max()), 1e-30)
        if log:
            image = 10 * np.log10(np.maximum(image, 1e-6))
        extent = [r.x[0] * 1e3, (r.x[-1] + r.project.window/r.project.grid) * 1e3] * 2
        plot = ax.imshow(image, origin="lower", extent=extent, cmap=INTENSITY_CMAP,
                         vmin=-50 if log else 0, vmax=0 if log else 1, interpolation="bilinear")
        limit = max(r.r86[index] * 2.2 * 1e3, .15)
        limit = min(limit, r.project.window * 500)
        ax.set(xlim=(-limit, limit), ylim=(-limit, limit), xlabel="x / mm", ylabel="y / mm",
               title=f"z = {r.z[index]*1e3:.1f} mm · 峰值归一化" + (" / dB" if log else ""))
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
        limit = min(max(r.r86[index] * 2.2 * 1e3, .15), r.project.window * 500)
        ax.set(xlim=(-limit, limit), xlabel="横向位置 / mm", ylabel="峰值归一化强度",
               title=f"z = {r.z[index]*1e3:.2f} mm · 中心剖面")
        ax.grid(alpha=.45)
        ax.legend(facecolor=BACKGROUND, labelcolor=TEXT)
        self.draw_idle()

    def intensity_surface(self, r, index):
        ax = self.reset()
        image = r.intensity[index]
        limit = min(max(r.r86[index] * 2 * 1e3, .15), r.project.window * 500)
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
        ax.plot(radii * 1e6, fraction * 100, color=BLUE)
        ax.axhline(86, color=ORANGE, ls="--", lw=.9)
        ax.axvline(r.r86[index] * 1e6, color=ORANGE, ls="--", lw=.9)
        ax.set(xlabel="距光轴半径 / μm", ylabel="包围能量 / %", ylim=(0, 101),
               xlim=(0, min(r.project.window / 2, r.r86[index] * 4) * 1e6),
               title=f"z = {r.z[index]*1e3:.2f} mm · 虚线为 r86")
        ax.grid(alpha=.45)
        self.draw_idle()
