# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, get_package_paths
from pathlib import Path

datas = collect_data_files('pyvista') + collect_data_files('pyvistaqt')
for package in ('pyvista', 'pyvistaqt', 'scipy', 'matplotlib'):
    datas += copy_metadata(package)

a = Analysis(
    ['app_entry.py'], pathex=[], binaries=[], datas=datas,
    hiddenimports=['vtkmodules.qt.QVTKRenderWindowInteractor', 'vtkmodules.vtkInteractionStyle',
                   'vtkmodules.vtkRenderingOpenGL2', 'vtkmodules.vtkRenderingFreeType',
                   'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_svg',
                   'matplotlib.backends.backend_pdf', 'scipy.fft._pocketfft'],
    hookspath=[], hooksconfig={'matplotlib': {'backends': ['QtAgg']}}, runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'tkinter', 'pytest', 'IPython',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
              'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
              'PySide6.QtDataVisualization', 'PySide6.QtVirtualKeyboard'],
    noarchive=False,
)
# Qt 图形界面钩子会发现可选的图像和输入插件。
# 仅保留本应用实际使用的模块，排除文档、声明式界面与虚拟键盘组件。
qt_libraries = {'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Network.dll', 'Qt6OpenGL.dll',
                'Qt6OpenGLWidgets.dll', 'Qt6Widgets.dll', 'Qt6Svg.dll'}
def required_binary(item):
    destination = item[0].replace('\\', '/')
    filename = destination.rsplit('/', 1)[-1]
    if filename.lower().startswith(('icudt', 'icuuc', 'icuin')) and filename.lower().endswith('.dll'):
        return False
    if destination.startswith('PySide6/') and filename.startswith('Qt6') and filename.endswith('.dll'):
        return filename in qt_libraries
    # Qt 应从 Windows 系统目录解析原生 ICU 接口；构建环境 PATH 中的
    # Poppler 版本导出符号不同，必须排除。
    return filename not in {'qpdf.dll', 'qtvirtualkeyboardplugin.dll', 'QtDataVisualization.pyd',
                            'icuuc.dll', 'icuin.dll', 'icudt.dll'}
a.binaries = [item for item in a.binaries if required_binary(item)]
# Python 3.10 自带的运行库较旧，加载器会优先读取包根目录的副本。
# 统一采用 Qt 安装包附带的较新兼容版本，避免动态库加载冲突。
pyside_path = Path(get_package_paths('PySide6')[1])
runtime_names = ('VCRUNTIME140.dll', 'VCRUNTIME140_1.dll')
a.binaries = [item for item in a.binaries if item[0].lower() not in {name.lower() for name in runtime_names}]
a.binaries += [(name, str(pyside_path / name), 'BINARY') for name in runtime_names]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='GaussianLab', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          disable_windowed_traceback=False, version='packaging/windows-version-info.txt')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='GaussianLab')
