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


@dataclass
class Project:
    name: str = "单透镜聚焦"
    wavelength: float = 632.8e-9
    waist: float = 0.45e-3
    waist_z: float = 0.0
    length: float = 0.4
    window: float = 0.006
    grid: int = 512
    samples: int = 65
    elements: list[Element] = field(default_factory=lambda: [Element()])

    def validate(self):
        numbers = (self.wavelength, self.waist, self.waist_z, self.length, self.window)
        if not all(math.isfinite(x) for x in numbers):
            raise ValueError("光源与距离参数必须为有限数值")
        if min(self.wavelength, self.waist, self.length, self.window) <= 0:
            raise ValueError("波长、束腰、传播长度和窗口必须大于零")
        if self.grid not in (128, 256, 512, 1024):
            raise ValueError("网格须为 128、256、512 或 1024")
        if not isinstance(self.samples, int) or not 17 <= self.samples <= 161:
            raise ValueError("轴向采样须为 17—161 点")
        if len(self.elements) > 20:
            raise ValueError("第一版最多支持 20 个元件")
        if self.grid**2 * (self.samples + len(self.elements)) * 4 > 384 * 1024**2:
            raise ValueError("结果体积超过首版 384 MiB 限制，请减少网格或轴向采样点")
        for e in self.elements:
            if e.kind not in ("lens", "aperture"):
                raise ValueError("未知元件类型")
            if not all(math.isfinite(x) for x in (e.z, e.value)) or not 0 <= e.z <= self.length:
                raise ValueError("元件位置须位于传播区间，参数须为有限数值")
            if e.kind == "lens" and e.value == 0:
                raise ValueError("透镜焦距不能为零")
            if e.kind == "aperture" and e.value <= 0:
                raise ValueError("光阑直径必须大于零")
        return self

    def ordered(self):
        return sorted((e for e in self.elements if e.enabled), key=lambda e: e.z)

    def clone(self):
        return from_dict(asdict(self))


def from_dict(data):
    data = dict(data)
    data["elements"] = [Element(**e) for e in data.get("elements", [])]
    return Project(**data).validate()


def save_project(project, path):
    project.validate()
    Path(path).write_text(json.dumps({"schema_version": 1, "units": "SI", "project": asdict(project)},
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
