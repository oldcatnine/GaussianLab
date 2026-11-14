# Third-party software notices / 第三方组件说明

GaussianLab uses CPython, NumPy, SciPy, Matplotlib, PySide6/Shiboken6/Qt, PyVista,
PyVistaQt, VTK, Pillow and their dependencies. Copyright remains with the respective
authors. Full collected license and copyright texts accompany this distribution in
`THIRD_PARTY_LICENSES`. `INDEX.json` identifies distribution versions; the notice
collection conservatively includes some build-only environment packages.

## Qt and PySide6

This application uses unmodified Qt 6.12.0 and PySide6/Shiboken6 6.12.0 dynamic
libraries under the LGPL version 3 option. The full LGPL and GPL texts, plus upstream
third-party notices, are included in `THIRD_PARTY_LICENSES/Qt-upstream`.

The Qt DLLs and Python extension modules remain separate in `_internal`. You may
replace these LGPL libraries with compatible modified versions and run the
application with them. Reverse engineering for debugging modifications to these
LGPL libraries is permitted; no additional restriction on these LGPL rights is
imposed by this distribution. Preserve binary compatibility and the folder layout.
Application source, dependency versions and the PyInstaller spec are provided in
the same GitHub release tag to facilitate rebuilding/relinking.

Complete unmodified corresponding source archives for the Qt components used here
(qtbase, qtsvg, qtimageformats and pyside-setup, including Shiboken) are supplied as
the companion `GaussianLab-v0.1.0-Qt-Corresponding-Source.zip` release attachment.
`SOURCE-MANIFEST.json` contains the original download URLs and verified SHA-256
hashes. Source archives include upstream build instructions. This companion asset
is offered at the same release location as the executable, without additional fees.

Qt PDF, DataVisualization and VirtualKeyboard plugins are not required by this
Widgets application and are excluded from the executable distribution.

Upstream references:

- https://www.qt.io/development/open-source-lgpl-obligations
- https://download.qt.io/archive/qt/6.12/6.12.0/submodules/
- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/
- https://code.qt.io/cgit/

## Application and other components

This notice does not grant a new license over the user's original application
code. The public availability of project source does not by itself select a new
application license. The rights and conditions of third-party components remain
governed by their included licenses, including BSD/MIT/PSF/Matplotlib licenses and
the PyInstaller bootloader exception. The application is an educational simulation;
the included components' warranty disclaimers remain in effect.
