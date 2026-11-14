"""VTK scene: longitudinal X axis is physical z; transverse axes are magnified."""
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor


class OpticalScene(QtInteractor):
    def __init__(self, parent=None):
        super().__init__(parent, auto_update=False)
        self.set_background("#080e1d", top="#15243b")
        self.scale_transverse = 25
        self.result = None
        self.screen_actor = None

    def set_result(self, result):
        self.result = result
        self.clear()
        self.screen_actor = None
        p = result.project
        z = result.z * 1e3
        angle = np.linspace(0, 2 * np.pi, 48)
        zz, aa = np.meshgrid(z, angle, indexing="ij")
        # Use measured energy radius, not a fictional ray solution after clipping.
        radii = result.r86 * 1e3 * self.scale_transverse
        yy = radii[:, None] * np.cos(aa)
        hh = radii[:, None] * np.sin(aa)
        mesh = pv.StructuredGrid(zz, yy, hh)
        mesh["energy"] = np.broadcast_to(result.transmission[:, None], zz.shape).ravel(order="F")
        self.add_mesh(mesh, color="#55ddec", opacity=.23, smooth_shading=True,
                      show_edges=False, name="energy_envelope")
        for fraction, opacity in ((.68, .15), (.32, .25)):
            core = pv.StructuredGrid(zz, yy*fraction, hh*fraction)
            self.add_mesh(core, color="#92f8ff", opacity=opacity, lighting=False)
        floor = pv.Plane(center=(p.length*500, 0, -36), direction=(0, 0, 1),
                         i_size=p.length*1100, j_size=140, i_resolution=32, j_resolution=12)
        self.add_mesh(floor, color="#1c4057", style="wireframe", opacity=.35, line_width=.7)
        self.add_mesh(pv.Line((0, 0, 0), (p.length * 1e3, 0, 0)), color="#6b8fa7", opacity=.5)
        for e in p.ordered():
            center = (e.z * 1e3, 0, 0)
            if e.kind == "lens":
                self.add_mesh(pv.Cylinder(center=center, direction=(1, 0, 0), radius=22, height=3,
                                          resolution=80), color="#79bfff", opacity=.3,
                              smooth_shading=True)
                ring = pv.Disc(center=center, inner=21.5, outer=23, normal=(1, 0, 0), c_res=80)
                self.add_mesh(ring, color="#b7d8f2", opacity=.8)
            else:
                hole = max(e.value * 1e3 / 2 * self.scale_transverse, .3)
                disc = pv.Disc(center=center, inner=hole, outer=max(hole+5, 24),
                               normal=(1, 0, 0), c_res=100)
                self.add_mesh(disc, color="#8e9caf", metallic=.7, roughness=.4)
            self.add_point_labels([(center[0], 0, 30)], [e.label], font_size=13,
                                  text_color="#dbe7ff", point_size=0, shape=None, always_visible=True)
            self.add_mesh(pv.Cylinder(center=(center[0], 0, -29), direction=(0, 0, 1),
                                      radius=1.5, height=12), color="#5d7797")
            self.add_mesh(pv.Cube(center=(center[0], 0, -36), x_length=14, y_length=26,
                                  z_length=2), color="#344b68")
        focus = result.focus_index
        self.add_mesh(pv.Sphere(radius=2, center=(z[focus], 0, 0)), color="#ffd17a",
                      ambient=.7, name="focus")
        self.add_axes(xlabel="z", ylabel="x", zlabel="y", line_width=2)
        self.add_text("r86 ENERGY ENVELOPE  |  transverse x25\nOptical elements: schematic geometry",
                      position="upper_left", font_size=10, color="#8ca7c7", name="scale_label")
        self.reset_view()

    def set_plane(self, index):
        r = self.result
        if r is None:
            return
        if self.screen_actor is not None:
            self.remove_actor(self.screen_actor, reset_camera=False)
        # Display a cropped slice to keep it legible relative to the longitudinal bench.
        crop = max(float(r.r86[index] * 1.7), .25e-3)
        mask = np.abs(r.x) <= min(crop, r.project.window * .48)
        coords = r.x[mask][::2] * 1e3 * self.scale_transverse
        if len(coords) < 3:
            coords = r.x[mask] * 1e3 * self.scale_transverse
            step = 1
        else:
            step = 2
        a, b = np.meshgrid(coords, coords, indexing="xy")
        plane = pv.StructuredGrid(np.full_like(a, r.z[index] * 1e3), a, b)
        image = r.intensity[index][np.ix_(mask, mask)][::step, ::step]
        peak = max(float(image.max()), 1e-30)
        plane["Intensity"] = (image / peak).ravel(order="F")
        self.screen_actor = self.add_mesh(plane, scalars="Intensity", cmap="inferno", clim=(0, 1),
                                          opacity=.92, lighting=False, show_scalar_bar=False,
                                          name="observation_screen", reset_camera=False)
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
