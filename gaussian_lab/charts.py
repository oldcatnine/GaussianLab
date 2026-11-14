import numpy as np
from matplotlib import rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
                 "axes.unicode_minus": False, "font.size": 9})


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, surface=False):
        self.figure = Figure(facecolor="#101b2c", layout="constrained")
        super().__init__(self.figure)
        self.surface = surface
        self.ax = None

    def reset(self):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111, projection="3d" if self.surface else None)
        self.ax.set_facecolor("#101b2c")
        self.ax.tick_params(colors="#9eb3cd", labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color("#30425b")
        self.ax.xaxis.label.set_color("#a8bbd5")
        self.ax.yaxis.label.set_color("#a8bbd5")
        self.ax.title.set_color("#dceaff")
        return self.ax

    def beam(self, r, index):
        ax = self.reset()
        ax.plot(r.z * 1e3, r.gaussian_w * 1e6, color="#64dcea", lw=1.7, label="理想高斯参考 w")
        ax.plot(r.z * 1e3, r.r86 * 1e6, color="#ffc477", lw=1.5, label="衍射 r86")
        ax.axvline(r.z[index] * 1e3, color="#c5d8ed", ls="--", lw=.9)
        for e in r.project.ordered():
            ax.axvline(e.z * 1e3, color="#52627b", alpha=.5, lw=.7)
        ax.set(xlabel="传播位置 z / mm", ylabel="半径 / μm")
        ax.grid(alpha=.12, color="#b0c3df")
        ax.legend(facecolor="#17253a", edgecolor="#30425b", labelcolor="#d0ddef", fontsize=8)
        self.draw_idle()

    def spot(self, r, index, log=False):
        ax = self.reset()
        image = r.intensity[index]
        image = image / max(float(image.max()), 1e-30)
        if log:
            image = 10 * np.log10(np.maximum(image, 1e-6))
        extent = [r.x[0] * 1e3, (r.x[-1] + r.project.window/r.project.grid) * 1e3] * 2
        plot = ax.imshow(image, origin="lower", extent=extent, cmap="inferno",
                         vmin=-50 if log else 0, vmax=0 if log else 1, interpolation="bilinear")
        limit = max(r.r86[index] * 2.2 * 1e3, .15)
        limit = min(limit, r.project.window * 500)
        ax.set(xlim=(-limit, limit), ylim=(-limit, limit), xlabel="x / mm", ylabel="y / mm",
               title=f"z = {r.z[index]*1e3:.1f} mm · 峰值归一化" + (" / dB" if log else ""))
        cb = self.figure.colorbar(plot, ax=ax, shrink=.8, pad=.025)
        cb.ax.tick_params(colors="#9eb3cd", labelsize=7)
        self.draw_idle()

    def profile(self, r, index):
        ax = self.reset()
        center = r.project.grid // 2
        image = r.intensity[index]
        peak = max(float(image.max()), 1e-30)
        ax.plot(r.x * 1e3, image[center] / peak, color="#62dced", label="x 剖面")
        ax.plot(r.x * 1e3, image[:, center] / peak, color="#ffbd81", ls="--", label="y 剖面")
        limit = min(max(r.r86[index] * 2.2 * 1e3, .15), r.project.window * 500)
        ax.set(xlim=(-limit, limit), xlabel="横向位置 / mm", ylabel="峰值归一化强度")
        ax.grid(alpha=.12)
        ax.legend(facecolor="#17253a", labelcolor="white")
        self.draw_idle()

    def intensity_surface(self, r, index):
        ax = self.reset()
        image = r.intensity[index]
        limit = min(max(r.r86[index] * 2 * 1e3, .15), r.project.window * 500)
        m = np.abs(r.x * 1e3) <= limit
        step = max(1, int(m.sum()) // 50)
        xx, yy = np.meshgrid(r.x[m][::step] * 1e3, r.x[m][::step] * 1e3)
        ii = image[np.ix_(m, m)][::step, ::step]
        ax.plot_surface(xx, yy, ii / max(float(ii.max()), 1e-30), cmap="inferno",
                        linewidth=0, antialiased=True, rcount=60, ccount=60)
        ax.set(xlabel="x / mm", ylabel="y / mm", zlabel="I / Imax", title="强度曲面（非传播轨迹）")
        ax.view_init(28, -55)
        self.draw_idle()

    def scanning(self, rows, kind):
        ax = self.reset()
        values = np.array([r["value_m"] for r in rows]) * 1e3
        sizes = np.array([r["min_r86_m"] for r in rows]) * 1e6
        ax.plot(values, sizes, "o-", color="#ffc477", ms=4, label="末片透镜后最小 r86")
        ax.set(xlabel=("焦距 f / mm" if kind == "lens" else "光阑直径 / mm"), ylabel="最小 r86 / μm")
        ax.grid(alpha=.13)
        ax2 = ax.twinx()
        ax2.plot(values, [r["transmission"] * 100 for r in rows], color="#64dcea", ls="--", label="透过率")
        ax2.set_ylabel("透过率 / %", color="#64dcea")
        ax2.set_ylim(0, 105)
        ax2.tick_params(colors="#64dcea", labelsize=8)
        self.draw_idle()
