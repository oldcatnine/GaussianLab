"""共用界面控件：统一下拉样式，并让长说明按实际换行高度显示。"""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QListView, QStyle, QStyleOptionComboBox, QLabel, QSizePolicy


class WrappingLabel(QLabel):
    """按实际换行高度约束长说明，避免表单布局压缩并裁切文本。"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def fit_text_height(self):
        required = self.heightForWidth(max(1, self.width()))
        if required >= 0 and self.minimumHeight() != required:
            self.setMinimumHeight(required)
            self.updateGeometry()

    def setText(self, text):
        super().setText(text)
        self.fit_text_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_text_height()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self.fit_text_height()


class RefinedComboBox(QComboBox):
    """保留原生选择机制，仅替换粗重三角及弹出列表外观。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("refined", True)
        self.setCursor(Qt.PointingHandCursor)
        view = QListView()
        view.setSpacing(2)
        self.setView(view)
        self.setMaxVisibleItems(12)
        self.setStyleSheet("""
            QComboBox {padding:5px 30px 5px 10px;min-height:24px;
                border:1px solid #d6dce5;border-radius:8px;background:#fafbfc;color:#25344a;}
            QComboBox:hover {border-color:#a7bad5;background:#f1f5fa;}
            QComboBox:focus,QComboBox:on {border-color:#739bcf;background:#ffffff;}
            QComboBox:disabled {color:#b0b8c5;background:#f5f5f7;border-color:#e5e7eb;}
            QComboBox::drop-down {subcontrol-origin:border;subcontrol-position:right;
                width:26px;border:0;background:transparent;}
            QComboBox::down-arrow {image:none;width:0;height:0;}
            QAbstractItemView {background:#ffffff;color:#25344a;border:1px solid #dce2ea;
                border-radius:8px;padding:5px;outline:0;selection-background-color:#e8f0fc;
                selection-color:#174477;}
            QAbstractItemView::item {min-height:28px;padding:3px 8px;border-radius:5px;}
            QAbstractItemView::item:hover {background:#f1f5fa;}
            QAbstractItemView::item:selected {background:#e8f0fc;color:#174477;}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        rect = self.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxArrow, self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#64748b" if self.isEnabled() else "#cbd5e1"), 1.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        cx, cy = rect.center().x(), rect.center().y()
        path = QPainterPath()
        path.moveTo(cx-3.5, cy-1.5)
        path.lineTo(cx, cy+2)
        path.lineTo(cx+3.5, cy-1.5)
        painter.drawPath(path)
        painter.end()
