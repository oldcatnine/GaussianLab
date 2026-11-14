# 第三方依赖与参考说明

本版未复制 RayTracing、LightPipes、GaussianBeam 的实现代码；解析与 Fresnel 内核由本项目编写，并通过解析基准验证。外部参考来源及学习范围见 research.md。

基础运行依赖为 NumPy、SciPy、Matplotlib、PySide6、PyVista、PyVistaQt，三维底层依赖 VTK；测试使用 pytest。V3 可选 CUDA 另用 CuPy 与 NVIDIA 运行组件。基础版本见 requirements-lock.txt，可选源码环境版本见 requirements-cuda.txt；相关许可证以实际组件的 LICENSE/NOTICE 为准。

| 项目 | 上游许可方向 | 使用方式 |
| --- | --- | --- |
| NumPy / SciPy | BSD | 数组、FFT |
| Matplotlib | Matplotlib/PSF 系列许可 | 绘图、桌面画布 |
| PySide6 / Qt | LGPL/GPL/商业许可并存，按实际模块核对 | Qt Widgets 桌面界面 |
| PyVista | MIT | 三维数据与渲染封装 |
| PyVistaQt | MIT | Qt 三维画布 |
| VTK | BSD | 三维渲染 |
| pytest | MIT | 自动测试 |
| CuPy 14.2.0 | MIT | V3 CUDA 数组与 FFT |
| cuda-pathfinder 1.8.3 | Apache-2.0 | NVIDIA 组件路径查找 |
| cudart / NVRTC / cuFFT / nvJitLink | NVIDIA 随包许可/EULA | 应用私有运行组件，不包含系统驱动 |

V3.0.0 已发布 Windows onedir 便携包：Qt 动态库保持可替换结构，Qt/PySide6 对应源码与应用源码分别提供附件。非必需的 Qt PDF、DataVisualization、VirtualKeyboard 模块排除。基础许可清单为 THIRD_PARTY_LICENSES/INDEX.json，CUDA 原始许可另存 THIRD_PARTY_LICENSES/CUDA，文件摘要为 _internal/cuda_runtime/RUNTIME-MANIFEST.json。完整说明见 [发行第三方声明](THIRD-PARTY-NOTICES.md)。本表不替代原始许可文本。

便携版首次 CUDA 从固定官方 PyPI wheel 补齐编译头文件，核验大小和 SHA-256 后提取到私有缓存；配置为 packaging/cuda-headers-wheel.json，随包名为 CUDA-HEADERS.json。源码安装与便携初始化是两条流程，便携版用户无需手动安装 Python 或完整 Toolkit。


## 可选数值对照依赖

`requirements-validation.txt` 固定 LightPipes==2.1.5，用于独立卷积传播验证，不是桌面产品必需依赖。实际读取原仓库及随包 LICENSE.txt，按 BSD-3-Clause 管理；本项目只调用接口，未复制其算法源码。后续若将该包纳入二进制发行，应保留完整版权和许可，并更新依赖清单。当前 V0.1.0 发行附件保持原状。
