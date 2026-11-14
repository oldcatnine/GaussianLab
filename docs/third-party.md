# 第三方依赖与参考说明

本版未复制 RayTracing、LightPipes、GaussianBeam 的实现代码；解析与 Fresnel 内核由本项目编写，并通过解析基准验证。外部参考来源及学习范围见 research.md。

直接运行依赖为 NumPy、SciPy、Matplotlib、PySide6、PyVista、PyVistaQt，三维底层依赖 VTK；测试使用 pytest。精确版本见 requirements-lock.txt，相关许可证以实际安装包中的 LICENSE/NOTICE 为准。

| 项目 | 上游许可方向 | 使用方式 |
| --- | --- | --- |
| NumPy / SciPy | BSD | 数组、FFT |
| Matplotlib | Matplotlib/PSF 系列许可 | 绘图、桌面画布 |
| PySide6 / Qt | LGPL/GPL/商业许可并存，按实际模块核对 | Qt Widgets 桌面界面 |
| PyVista | MIT | 三维数据与渲染封装 |
| PyVistaQt | MIT | Qt 三维画布 |
| VTK | BSD | 三维渲染 |
| pytest | MIT | 自动测试 |

当前交付为源码与本机独立环境，未制作二进制安装包。分发 EXE 前需逐项核对打包使用的 Qt 模块、许可证与必要声明，整理随包许可证；本表不替代完整的二进制分发许可清单。
