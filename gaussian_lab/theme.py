"""白色绘图主题与共享强度色标；颜色映射不改变计算数据。"""
from matplotlib.colors import LinearSegmentedColormap

BACKGROUND = "#ffffff"
TEXT = "#1f2937"
BORDER = "#cbd5e1"
BLUE = "#2563eb"
ORANGE = "#c2410c"
INTENSITY_CMAP = LinearSegmentedColormap.from_list(
    "white_intensity", [(0, "#ffffff"), (.1, "#eff6ff"), (.35, "#93c5fd"),
                        (.65, "#2563eb"), (.85, "#f59e0b"), (1, "#dc2626")])
