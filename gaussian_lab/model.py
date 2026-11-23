"""可序列化的项目数据模型；内部采用国际单位制，不依赖图形界面。"""
from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path


@dataclass
class Element:
    kind: str = "lens"
    z: float = 0.1
    value: float = 0.12  # 透镜焦距或光阑直径，单位为米。
    label: str = "L1"
    enabled: bool = True
    clear_diameter: float | None = None  # 透镜有效通光直径，单位为米；空值表示不限口径。


@dataclass
class Mode:
    """同波长、同轴、共用束腰的相干横模；相位以入口面为参考，单位为度。"""

    family: str = "HG"
    n: int = 0
    m: int = 0
    amplitude: float = 1.0
    phase_deg: float = 0.0


@dataclass
class Project:
    name: str = "单透镜聚焦"
    wavelength: float = 632.8e-9
    waist: float = 0.45e-3
    waist_z: float = 0.0
    length: float = 0.4
    window: float = 0.006
    grid: int = 1024
    samples: int = 65
    elements: list[Element] = field(default_factory=lambda: [Element()])

    focus_refinement: int = 2
    modes: list[Mode] = field(default_factory=lambda: [Mode()])
    memory_limit_mib: int = 384

    def validate(self):
        numbers = (self.wavelength, self.waist, self.waist_z, self.length, self.window)
        if not all(math.isfinite(x) for x in numbers):
            raise ValueError("光源与距离参数必须为有限数值")
        if min(self.wavelength, self.waist, self.length, self.window) <= 0:
            raise ValueError("波长、束腰、传播长度和窗口必须大于零")
        if type(self.grid) is not int or self.grid not in (128, 256, 512, 1024, 2048):
            raise ValueError("网格须为 128、256、512、1024 或 2048")
        if type(self.samples) is not int or not 17 <= self.samples <= 641:
            raise ValueError("轴向采样须为 17—641 点")
        if type(self.focus_refinement) is not int or not 0 <= self.focus_refinement <= 4:
            raise ValueError("焦区细化级数须为 0—4")
        if len(self.elements) > 20:
            raise ValueError("第一版最多支持 20 个元件")
        if type(self.memory_limit_mib) is not int or not 32 <= self.memory_limit_mib <= 65536:
            raise ValueError("结果数据上限须为 32—65536 MiB 的整数")
        if not 1 <= len(self.modes) <= 8:
            raise ValueError("输入光须包含 1—8 个相干模式")
        for mode in self.modes:
            if mode.family not in ("HG", "LG"):
                raise ValueError("模式类型须为 HG 或 LG")
            if (type(mode.n) is not int or type(mode.m) is not int or not 0 <= mode.n <= 8
                    or not (-8 if mode.family == "LG" else 0) <= mode.m <= 8):
                raise ValueError("HG 阶数 m、n 和 LG 径向阶数 p 为 0—8，LG 方位阶数 l 为 -8—8")
            if (not math.isfinite(mode.amplitude) or not 0 <= mode.amplitude <= 100
                    or not math.isfinite(mode.phase_deg)):
                raise ValueError("模式振幅须为 0—100 的有限数，相位须为有限数")
        if not any(mode.amplitude > 0 for mode in self.modes):
            raise ValueError("至少一个输入模式的振幅须大于零")
        for e in self.elements:
            if e.kind not in ("lens", "aperture"):
                raise ValueError("未知元件类型")
            if not all(math.isfinite(x) for x in (e.z, e.value)) or not 0 <= e.z <= self.length:
                raise ValueError("元件位置须位于传播区间，参数须为有限数值")
            if e.kind == "lens" and e.value == 0:
                raise ValueError("透镜焦距不能为零")
            if e.kind == "aperture" and e.value <= 0:
                raise ValueError("光阑直径必须大于零")
            if e.clear_diameter is not None and (
                e.kind != "lens" or not math.isfinite(e.clear_diameter) or e.clear_diameter <= 0
            ):
                raise ValueError("透镜有效通光直径须为空或有限正数，仅适用于透镜")
        required = self.result_storage_bytes()
        if required > self.memory_limit_mib * 1024**2:
            raise ValueError(f"结果体积预计 {required / 1024**2:.1f} MiB，超过已设 {self.memory_limit_mib} MiB 上限；"
                             "请提高结果数据上限，或减少网格/轴向采样点")
        return self

    def sampling_positions(self):
        """统一观察面：均匀轴向面加启用元件面，同位置去重，端点精确取传播长度。"""
        step = self.length / (self.samples - 1)
        return sorted({*(i * step for i in range(self.samples - 1)), self.length,
                       *(e.z for e in self.elements if e.enabled)})

    def result_storage_bytes(self):
        """float32 强度体积的实际预分配字节数，包含一个额外焦面槽位。"""
        return self.grid**2 * (len(self.sampling_positions()) + 1) * 4

    def ordered(self):
        return sorted((e for e in self.elements if e.enabled), key=lambda e: e.z)

    def clone(self):
        return from_dict(asdict(self))


def from_dict(data):
    data = dict(data)
    data["elements"] = [Element(**e) for e in data.get("elements", [])]
    if "modes" in data:
        data["modes"] = [Mode(**m) for m in data["modes"]]
    return Project(**data).validate()


def save_project(project, path):
    project.validate()
    data = asdict(project)
    for element in data["elements"]:
        if element["clear_diameter"] is None:
            del element["clear_diameter"]
    Path(path).write_text(json.dumps({"schema_version": 1, "units": "SI", "project": data},
                                    ensure_ascii=False, indent=2), encoding="utf-8")


def load_project(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("units") != "SI":
        raise ValueError("不支持的项目版本或单位")
    return from_dict(data["project"])


def preset(name):
    if name == "双透镜扩束":
        return Project(name=name, waist=0.25e-3, length=0.5, window=0.008,
                       elements=[Element("lens", .06, -.05, "L1"), Element("lens", .16, .15, "L2")])
    if name == "光阑衍射":
        return Project(name=name, waist=.65e-3, length=.4,
                       elements=[Element("aperture", .06, .9e-3, "A1"), Element("lens", .1, .12, "L1")])
    return Project()
