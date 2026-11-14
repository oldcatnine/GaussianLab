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

V0.1.0 已准备 Windows onedir 二进制发行：所需动态库与原始许可随运行包保存，Qt/PySide6 对应源码以独立附件提供。Qt PDF、DataVisualization、VirtualKeyboard 等非必需模块和插件排除。完整说明见 [发行第三方声明](THIRD-PARTY-NOTICES.md)；实际收集清单位于运行包 THIRD_PARTY_LICENSES/INDEX.json。本表不替代包内原始许可文本。


## 可选数值对照依赖

`requirements-validation.txt` 固定 LightPipes==2.1.5，用于独立卷积传播验证，不是桌面产品必需依赖。实际读取原仓库及随包 LICENSE.txt，按 BSD-3-Clause 管理；本项目只调用接口，未复制其算法源码。后续若将该包纳入二进制发行，应保留完整版权和许可，并更新依赖清单。当前 V0.1.0 发行附件保持原状。
