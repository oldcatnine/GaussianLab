"""三维场景：显示纵轴对应物理 z，横向坐标按视觉倍率放大。"""
import numpy as np
from pathlib import Path
import os
from scipy.ndimage import map_coordinates
import pyvista as pv
from pyvistaqt import QtInteractor
from .theme import BACKGROUND, TEXT, INTENSITY_CMAP
from .model import input_mode_label


class OpticalScene(QtInteractor):
    def __init__(self, parent=None):
        super().__init__(parent, auto_update=False)
        self.set_background(BACKGROUND)
        self.scale_transverse = 25
        self.result = None
        self.screen_actor = None
        self.screen_options = None
        font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc"
        self.text_font = {"font_file": str(font)} if font.is_file() else {}

    def set_result(self, result):
        previous = self.suppress_rendering
        self.suppress_rendering = True
        try:
            index = getattr(self,"plane_index",None)
            self._set_result(result)
            self.update_mode_volume()
            self.update_input_screen()
            self.set_plane(min(index if index is not None else result.focus_index,len(result.z)-1))
        finally:
            self.suppress_rendering = previous
        self.render()

    def _set_result(self, result):
        camera = self.camera_position if self.result is not None and self.result.project.length == result.project.length else None
        self.result = result
        self.plane_index = None
        p = result.project
        z = result.z * 1e3
        angle = np.linspace(0, 2 * np.pi, 48)
        zz, aa = np.meshgrid(z, angle, indexing="ij")
        # 由计算得到的包围能量半径构造轮廓，适用于截断后的显示。
        radii = result.r86 * 1e3 * self.scale_transverse
        yy = radii[:, None] * np.cos(aa)
        hh = radii[:, None] * np.sin(aa)
        signature = (p.length, len(z), tuple((e.kind, e.z, e.value if e.kind == "aperture" else None, e.label)
                                            for e in p.ordered()))
        if getattr(self, "geometry_signature", None) == signature:
            for mesh, fraction in self.envelope_meshes:
                mesh.points = np.column_stack((zz.ravel(order="F"), (yy*fraction).ravel(order="F"),
                                               (hh*fraction).ravel(order="F")))
            self.envelope_meshes[0][0]["energy"] = np.broadcast_to(result.transmission[:, None], zz.shape).ravel(order="F")
            self.focus_actor.SetPosition(float(z[result.focus_index] - self.focus_origin_z), 0, 0)
            return
        self.geometry_signature = signature
        self.clear()
        self.screen_actor = None
        mesh = pv.StructuredGrid(zz, yy, hh)
        self.envelope_meshes = [(mesh, 1.0)]
        mesh["energy"] = np.broadcast_to(result.transmission[:, None], zz.shape).ravel(order="F")
        self.add_mesh(mesh, color="#0284c7", opacity=.06, smooth_shading=True,
                      show_edges=False, name="energy_envelope")
        floor = pv.Plane(center=(p.length*500, 0, -36), direction=(0, 0, 1),
                         i_size=p.length*1100, j_size=140, i_resolution=32, j_resolution=12)
        self.add_mesh(floor, color="#94a3b8", style="wireframe", opacity=.35, line_width=.7)
        self.add_mesh(pv.Line((0, 0, 0), (p.length * 1e3, 0, 0)), color="#64748b", opacity=.5)
        for e in p.ordered():
            center = (e.z * 1e3, 0, 0)
            if e.kind == "lens":
                self.add_mesh(pv.Cylinder(center=center, direction=(1, 0, 0), radius=22, height=3,
                                          resolution=80), color="#60a5fa", opacity=.3,
                              smooth_shading=True)
                ring = pv.Disc(center=center, inner=21.5, outer=23, normal=(1, 0, 0), c_res=80)
                self.add_mesh(ring, color="#3b82f6", opacity=.8)
            else:
                hole = max(e.value * 1e3 / 2 * self.scale_transverse, .3)
                disc = pv.Disc(center=center, inner=hole, outer=max(hole+5, 24),
                               normal=(1, 0, 0), c_res=100)
                self.add_mesh(disc, color="#64748b", metallic=.7, roughness=.4)
            self.add_point_labels([(center[0], 0, 30)], [e.label], font_size=13,
                                  text_color=TEXT, point_size=0, shape=None, always_visible=True)
            self.add_mesh(pv.Cylinder(center=(center[0], 0, -29), direction=(0, 0, 1),
                                      radius=1.5, height=12), color="#475569")
            self.add_mesh(pv.Cube(center=(center[0], 0, -36), x_length=14, y_length=26,
                                  z_length=2), color="#334155")
        focus = result.focus_index
        self.focus_origin_z = z[focus]
        self.focus_actor = self.add_mesh(pv.Sphere(radius=.8, center=(z[focus], 0, -32)), color="#c2410c",
                      ambient=.7, name="focus")
        self.add_axes(xlabel="z", ylabel="x", zlabel="y", line_width=2, color=TEXT)
        self.add_text("横向放大 25 倍；浅蓝外罩为 r86 参考\n彩色主体为逐面峰值归一化强度的抽样等值面",
                      position="upper_left", font_size=9, color=TEXT, name="scale_label", **self.text_font)
        self.setToolTip("三维浅蓝轮廓表示 r86；横向放大 25 倍。彩色主体来自实际强度的抽样等值面，入口屏与当前屏来自原始强度；不是矢量场或相位图。")
        if camera is None:
            self.reset_view()
        else:
            self.camera_position = camera
            self.render()

    def plane_samples(self, index, maximum=257):
        """与二维光斑同视野，从原始像素选取坐标，保留光轴并限制渲染点数。"""
        r = self.result
        dx = r.project.window / r.project.grid
        limit = min(max(float(r.r86[index])*2.2, 4*dx), r.project.window/2)
        indices = np.flatnonzero(np.abs(r.x) <= limit)
        if len(indices) > maximum:
            indices = indices[np.unique(np.linspace(0,len(indices)-1,maximum,dtype=int))]
        indices = np.unique(np.append(indices,r.project.grid//2))
        image = r.intensity[index]
        peak = max(float(image.max()),1e-30)
        return indices, np.asarray(image[np.ix_(indices,indices)] / peak)

    def update_mode_volume(self):
        """用有界抽样网格提取真实多瓣/空心形状，不复制完整三维强度体积。"""
        r = self.result
        indices = np.unique(np.r_[np.linspace(0,len(r.z)-1,min(33,len(r.z)),dtype=int),r.focus_index,
                                   [int(np.argmin(abs(r.z-e.z))) for e in r.project.ordered()]]).astype(int)
        count = 65
        shape = (len(indices),count,count)
        zz, xx, yy = (np.empty(shape) for _ in range(3))
        values = np.empty(shape,dtype=np.float32)
        dx = r.project.window / r.project.grid
        for k, index in enumerate(indices):
            limit = min(max(float(r.r86[index])*2.2,4*dx),r.project.window/2)
            coords = np.linspace(-limit,limit,count)
            a,b = np.meshgrid(coords,coords,indexing="xy")
            pixel_a, pixel_b = (a-r.x[0])/dx, (b-r.x[0])/dx
            image = map_coordinates(r.intensity[index], [pixel_b,pixel_a], order=1, mode="constant", cval=0, prefilter=False)
            values[k] = image / max(float(image.max()),1e-30)
            zz[k] = r.z[index]*1e3
            xx[k], yy[k] = a*1e3*self.scale_transverse, b*1e3*self.scale_transverse
        self.mode_volume = pv.StructuredGrid(zz,xx,yy)
        self.mode_volume["Intensity"] = values.ravel(order="F")
        self.mode_plane_indices = indices
        self.mode_surface = self.mode_volume.contour([.15,.5],scalars="Intensity")
        self.remove_actor("mode_intensity",reset_camera=False,render=False)
        if self.mode_surface.n_points:
            self.add_mesh(self.mode_surface,scalars="Intensity",cmap=INTENSITY_CMAP,clim=(0,1),
                          opacity=.45,lighting=False,show_scalar_bar=False,name="mode_intensity",reset_camera=False,render=False)

    def make_screen(self, index, name, log=False, smooth=True):
        """观察屏点值对应原始采样；零强度透明，避免黑底平面遮住多瓣主体。"""
        r = self.result
        indices,image = self.plane_samples(index)
        coords = r.x[indices]*1e3*self.scale_transverse
        a,b = np.meshgrid(coords,coords,indexing="xy")
        mesh = pv.StructuredGrid(np.full_like(a,r.z[index]*1e3),a,b)
        if log:
            image = 10*np.log10(np.maximum(image,1e-6))
        mesh["Intensity"] = image.ravel(order="F")
        actor = self.add_mesh(mesh,scalars="Intensity",cmap=INTENSITY_CMAP,clim=(-50,0) if log else (0,1),
                              opacity=[0,.12,.35,.7,1],lighting=False,show_scalar_bar=False,
                              interpolate_before_map=smooth,name=name,reset_camera=False,render=False)
        return actor, mesh, indices

    def update_input_screen(self, log=False, smooth=True):
        self.remove_actor("input_screen",reset_camera=False,render=False)
        self.input_actor,self.input_mesh,self.input_indices = self.make_screen(0,"input_screen",log,smooth)

    def set_plane(self, index, log=False, smooth=True):
        r = self.result
        if r is None:
            return
        if getattr(self, "plane_index", None) == index and self.screen_options == (log,smooth):
            return
        if self.screen_options != (log,smooth):
            self.update_input_screen(log,smooth)
        self.plane_index = index
        self.screen_options = (log,smooth)
        if self.screen_actor is not None:
            self.remove_actor(self.screen_actor, reset_camera=False, render=False)
        self.screen_actor,self.screen_mesh,self.screen_indices = self.make_screen(index,"observation_screen",log,smooth)
        self.input_actor.SetVisibility(index != 0)
        self.add_text(f"输入：{input_mode_label(r.project)}\n入口屏 z={r.z[0]*1e3:.4f} mm；当前屏 z={r.z[index]*1e3:.4f} mm\n当前屏与右侧二维图同一观察面、同一峰值归一化" + (" / dB" if log else ""),
                      position="lower_left",font_size=9,color=TEXT,name="mode_label",render=False,**self.text_font)
        self.render()

    def reset_view(self):
        if self.result is None:
            return
        length = self.result.project.length * 1e3
        self.camera_position = [(length * 1.3, -length * .85, length * .6),
                                (length * .48, 0, 0), (0, 0, 1)]
        self.reset_camera()
        self.camera.zoom(1.35)
        self.render()
