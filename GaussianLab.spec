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
                   'matplotlib.backends.backend_qtagg', 'scipy.fft._pocketfft'],
    hookspath=[], hooksconfig={'matplotlib': {'backends': ['QtAgg']}}, runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'tkinter', 'pytest', 'IPython',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
              'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
              'PySide6.QtDataVisualization', 'PySide6.QtVirtualKeyboard'],
    noarchive=False,
)
# The Qt GUI hook discovers optional image/input plugins. Keep only the modules
# actually used by this Widgets application, without PDF/QML/virtual-keyboard.
qt_libraries = {'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Network.dll', 'Qt6OpenGL.dll',
                'Qt6OpenGLWidgets.dll', 'Qt6Widgets.dll', 'Qt6Svg.dll'}
def required_binary(item):
    destination = item[0].replace('\\', '/')
    filename = destination.rsplit('/', 1)[-1]
    if filename.lower().startswith(('icudt', 'icuuc', 'icuin')) and filename.lower().endswith('.dll'):
        return False
    if destination.startswith('PySide6/') and filename.startswith('Qt6') and filename.endswith('.dll'):
        return filename in qt_libraries
    # Qt's native Windows ICU API must resolve from System32. A third-party
    # Poppler ICU found on the build host's PATH exports incompatible symbols.
    return filename not in {'qpdf.dll', 'qtvirtualkeyboardplugin.dll', 'QtDataVisualization.pyd',
                            'icuuc.dll', 'icuin.dll', 'icudt.dll'}
a.binaries = [item for item in a.binaries if required_binary(item)]
# Python 3.10 ships an older MSVC runtime. The bootloader loads the root copy
# first; use the newer, backwards-compatible runtime supplied by the Qt wheel.
pyside_path = Path(get_package_paths('PySide6')[1])
runtime_names = ('VCRUNTIME140.dll', 'VCRUNTIME140_1.dll')
a.binaries = [item for item in a.binaries if item[0].lower() not in {name.lower() for name in runtime_names}]
a.binaries += [(name, str(pyside_path / name), 'BINARY') for name in runtime_names]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='GaussianLab', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='GaussianLab')
