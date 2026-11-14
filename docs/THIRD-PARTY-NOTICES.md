# 第三方组件说明

GaussianLab 使用 CPython、NumPy、SciPy、Matplotlib、PySide6、Shiboken6、Qt、PyVista、PyVistaQt、VTK、Pillow 及相关依赖。各组件版权属于原作者。发行目录 THIRD_PARTY_LICENSES 收录原始许可证与版权声明，INDEX.json 记录包名和版本；收集范围可能包含仅用于构建的包。

本文件是项目的中文解释，不替代各组件许可证原文。

## Qt 与 PySide6

应用使用未修改的 Qt 6.12.0、PySide6 6.12.0 和 Shiboken6 6.12.0 动态库，按 LGPL 第三版选项使用。完整 LGPL、GPL 及上游第三方许可文本位于 THIRD_PARTY_LICENSES/Qt-upstream。

Qt 动态库和 Python 扩展模块独立保留在 _internal 目录中。用户可以替换为兼容的修改版本并运行应用；为调试这些 LGPL 库的修改而进行逆向工程的权利不受本项目额外限制。替换时应保持二进制兼容性与目录结构。同一版本标签提供应用源码、依赖版本与打包配置，以支持重新构建和链接。

对应 Qt 组件的完整、未修改源码，包括 qtbase、qtsvg、qtimageformats、pyside-setup 及其中的 Shiboken，以 GaussianLab-v0.1.0-Qt-Corresponding-Source.zip 附件提供。SOURCE-MANIFEST.json 记录原始下载地址和经核验的 SHA-256。源码归档包含上游构建说明，与可执行附件在同一个版本发布位置提供。

本应用使用 Qt Widgets，不需要的 Qt PDF、DataVisualization、VirtualKeyboard 插件已从发行包排除。

上游参考：

- [Qt 开源许可义务说明](https://www.qt.io/development/open-source-lgpl-obligations)
- [Qt 6.12.0 模块源码](https://download.qt.io/archive/qt/6.12/6.12.0/submodules/)
- [PySide6 6.12.0 源码](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/)
- [Qt 源码仓库](https://code.qt.io/cgit/)

## 应用代码与其他组件

本声明不为用户原创应用代码选择新的许可证，源码可见不自动等同于采用某一开源许可。第三方组件按随附的 BSD、MIT、PSF、Matplotlib 等许可证及 PyInstaller 引导程序例外条款使用，其权利、条件和免责声明保持有效。
