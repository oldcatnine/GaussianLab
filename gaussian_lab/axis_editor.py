"""各图独立的中文坐标范围编辑器；范围仅用于显示，不修改物理输入。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
                              QLineEdit, QLabel, QPushButton, QHBoxLayout)


class AxisEditor(QDialog):
    def __init__(self, plot):
        super().__init__(plot)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.plot = plot
        self.setWindowTitle("坐标轴范围")
        layout = QVBoxLayout(self)
        self.selector = QComboBox()
        layout.addWidget(self.selector)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        self.fields = {}
        for name, title in (("x", "横轴"), ("y", "纵轴"), ("z", "高度轴")):
            row = QHBoxLayout()
            auto = QCheckBox("自动")
            low, high = QLineEdit(), QLineEdit()
            for edit in (low, high):
                edit.setMaximumWidth(150)
                auto.toggled.connect(edit.setDisabled)
            row.addWidget(auto)
            row.addWidget(low)
            row.addWidget(QLabel("至"))
            row.addWidget(high)
            label = QLabel(title)
            self.form.addRow(label, row)
            self.fields[name] = (auto, low, high, label, row)
        self.error = QLabel("范围单位与图中坐标轴一致，可输入科学计数法。")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QHBoxLayout()
        self.apply_button = QPushButton("应用")
        self.reset_button = QPushButton("恢复本图全部自动范围")
        close = QPushButton("关闭")
        for button in (self.apply_button, self.reset_button, close):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.apply_button.clicked.connect(self.apply)
        self.reset_button.clicked.connect(self.restore)
        close.clicked.connect(self.close)
        self.refresh_axes()
        self.selector.currentIndexChanged.connect(self.load_values)

    def refresh_axes(self):
        """选择双纵轴或 A/B 子图；不列出颜色条。"""
        self.selector.blockSignals(True)
        self.selector.clear()
        for i, ax in enumerate(self.plot.data_axes()):
            self.selector.addItem(f"{i+1}：{ax.get_title() or ax.get_ylabel() or '数据图'}")
        self.selector.blockSignals(False)
        self.load_values()

    def load_values(self, *_):
        axes = self.plot.data_axes()
        index = self.selector.currentIndex()
        if not 0 <= index < len(axes):
            return
        ax = axes[index]
        for name, (auto, low, high, label, row) in self.fields.items():
            visible = name != "z" or ax.name == "3d"
            label.setVisible(visible)
            for j in range(row.count()):
                row.itemAt(j).widget().setVisible(visible)
            if not visible:
                continue
            label.setText(getattr(ax, f"get_{name}label")() or name)
            a, b = getattr(ax, f"get_{name}lim")()
            low.setText(f"{a:.12g}")
            high.setText(f"{b:.12g}")
            auto.setChecked(name not in self.plot.axis_limits.get(index, {}))
            low.setDisabled(auto.isChecked())
            high.setDisabled(auto.isChecked())

    def apply(self):
        index = self.selector.currentIndex()
        axes = self.plot.data_axes()
        if not 0 <= index < len(axes):
            self.error.setText("图表已更新，请重新打开坐标轴设置。")
            return
        names = ("x", "y", "z") if axes[index].name == "3d" else ("x", "y")
        try:
            ranges = {name: None if self.fields[name][0].isChecked() else
                      (float(self.fields[name][1].text()), float(self.fields[name][2].text())) for name in names}
            self.plot.set_axis_ranges(index, ranges)
        except ValueError as exc:
            self.error.setText("无法应用：" + str(exc))
            return
        self.error.setText("已应用；重绘及图片导出会保留范围，不改变计算数据。")

    def restore(self):
        self.plot.axis_limits.clear()
        self.plot.draw_idle()
        self.refresh_axes()
