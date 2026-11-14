# 高斯光束传输计算器

课题：高斯光束经简单光学系统的传输仿真与光斑质量分析软件设计。

当前版本为 **V3.0.0**，将 CUDA/响应式预览分支整理为正式 Windows x64 便携版，算法标识为 `fresnel-segments-v3`。本机附件位于 `releases/v3.0.0/`，无需 Python；首次 CUDA 需联网补充约 3.6 MB 固定官方头文件并建立缓存，失败时使用 CPU。V2.0.0 与 V0.1.0 历史文件保留。见 [V3 使用说明](docs/USER_GUIDE-v3.0.0.md)、[版本说明](docs/release-notes-v3.0.0.md)、[构建与发布验证](docs/release-validation-v3.0.0.md)。

源码启动默认在停止改参 400 ms 后自动更新预览；点击“计算光场”运行原始网格与焦区细化。左侧可关闭自动预览，或选择 CPU、自动、CUDA 优先。没有 CUDA 依赖或兼容设备时仍能使用 CPU。可选安装脚本为 `scripts/install_cuda_runtime.ps1`，不会修改系统驱动。

## 启动

**便携版运行：** 将 `releases/v3.0.0/GaussianLab-v3.0.0-Windows-x64.zip` 复制到其他 Windows x64 电脑，完整解压后双击 `GaussianLab.exe`。保留 `_internal`、使用说明与随附文件。操作见 [V3.0.0 便携版指南](docs/USER_GUIDE-v3.0.0.md)。运行包、Qt 对应源码、应用源码和 SHA256SUMS.txt 保持同一版本；发布状态见同版本验证记录。历史版本按其原记录追溯。

本机已创建独立 `.venv`（Python 3.10.11）。双击 **启动软件.cmd**，或在本目录执行：

```powershell
.\.venv\Scripts\python.exe -m gaussian_lab
```

也可运行 [启动软件.ps1](启动软件.ps1)。首次启动自动计算单透镜案例；切换顶部案例后点击“加载案例”。

新机器需要 Python 3.10 或更新的兼容版本；建议先使用已实测的 Python 3.10：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m gaussian_lab
```

requirements-lock.txt 是本次 Windows/Python 3.10 的运行环境版本快照；requirements.txt 是直接依赖范围。Windows EXE 采用 PyInstaller 文件夹模式，构建依赖见 requirements-build.txt；其他 Python/系统组合尚未验证。

当前白色界面、观察屏、图片导出与常见问题见 [当前源码版使用说明](docs/USER_GUIDE.md)；原理与逐文件学习见 [项目学习手册](docs/项目学习手册.html)。

## 使用与边界

- 左侧设置光源和光路。表格中的透镜数值为焦距、光阑数值为直径，单位 mm；元件按 z 排序，同位置按表格顺序执行。
- 软件界面、三维场景及分析图采用白色背景；光斑色标从低强度白色过渡至高强度红色。右下选择图像类型后点击“导出图片”，可导出光斑图、剖面强度曲线、强度曲面、包围能量、轴向传播或参数扫描。支持 300 dpi PNG 以及 SVG/PDF，均为不透明白底；图片使用当前观察面和已计算的结果快照。
- 三维场景可鼠标拖动旋转、滚轮缩放；“播放传播”让观察屏沿光轴移动，联动二维光斑、剖面或强度曲面。
- 选择扫描元件与起止值，点击“开始扫描”。曲线显示末片透镜后粗搜索与局部细化得到的最小 r86；数据表与 CSV 区分正常、警告及失败点，记录焦区括宽。
- JSON 保存可恢复光路和计算参数。CSV 同步导出参数快照；单次计算额外导出指标、警告、源码摘要、匹配的收敛记录和焦面包围能量曲线；扫描额外记录扫描范围。当前支持分析图 PNG/SVG/PDF 和白底场景 PNG，尚未保存相机、观察屏等显示状态。
- 所有图形基于单色同轴、标量近轴、理想薄透镜与圆孔模型。解析 w 为高斯参考；衍射 r86 为 86% 包围能量半径，二者定义不同。
- **本版是可验证的首版，不是任意光路的高精度保证**：Fresnel FFT 使用有限周期窗口，焦点采用粗搜索与局部离散细化；高 NA、复杂像差与 M² 不在当前范围。“多指标收敛”分别比较网格、窗口、轴向采样下的末端/焦区 r86、焦点位置、远场角、透过率与焦面剖面，但不自动给出精度认证。
- 三维横向尺寸放大 25 倍，透镜外形及支座为示意；透明包络是 r86 轮廓，内部亮芯为展示辅助，不能当作三维强度测量。
- 光阑目前为独立元件；透镜有效口径、光路行拖动排序和扫描动画播放留待后续版本。

## 项目文档

- [项目学习手册（离线网页）](docs/项目学习手册.html)：从基础概念、操作与架构到逐文件用途、计算原理和技术自测问答；可直接打开、复制或打印。维护源文件为 [Markdown 手册](docs/项目学习手册.md)。
- [V2.0.0 发布说明](docs/release-notes-v2.0.0.md)与[便携版验证](docs/release-validation-v2.0.0.md)：附件、版本属性、解压与隔离运行结果。
- [当前源码版使用说明](docs/USER_GUIDE.md)：说明自动预览、完整计算、后端切换、六类图像导出、扫描和数据文件。
- [需求记录](docs/requirements.md)：用户已提出的需求、建议补充参数与验收规划。
- [开源与 Skill 调研](docs/research.md)：来源、源码学习、许可和适用边界。
- [产品设计草案](docs/product-design.md)：拟议界面、计算路线和待讨论事项。
- [产品设计方案 V1.0](docs/product-plan.md)：汇总需求、功能、3D 视觉、架构、开发阶段及验收标准，作为当前完整设计入口。
- [开发过程与能力方法记录](docs/development-log.md)：随每次工作同步更新，积累毕业设计报告所需的过程、工具方法、验证和问题处理证据。
- [V0.1 验证与交付记录](docs/validation-v0.1.md)：自动化测试、插件自测、数值结果、实际截图和首版局限。
- [V0.1.0 EXE 与 GitHub 发布验证](docs/release-validation-v0.1.0.md)：便携包、GitHub 构建及最终下载版 EXE 的复测证据。

- [数值增强验证与验收矩阵](docs/validation-v2.md)：新算法、独立对照、孔径取舍、内存记录与当前限制。
- [项目检查与改进建议](docs/project-review-2026-11-14.md)：阶段评价、焦区采样复核、问题优先级与后续验证建议。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
& .\tests\Test-Agents.ps1
git diff --check
```

test_optics.py 为数值和数据验证；test_independent_optics.py 为可选的固定版本 LightPipes 对照；test_gui.py 为真实 Qt/VTK 冒烟测试，需可用桌面与渲染环境；test_project_docs.py 为文档验证。Windows 上 pytest faulthandler 可能打印 COM 0x8001010d 诊断，复核方式与本次结果见后续验证记录；不要仅据该行或隐藏诊断判断成功，需检查退出码和断言。

源码与测试由本项目编写，第三方依赖及参考见 [第三方说明](docs/third-party.md)。

独立衍射对照与数值实验：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-validation.txt
.\.venv\Scripts\python.exe scripts/validate_numerics.py
```

输出默认位于 outputs，包含原始参数、数值表和孔径取舍图；归档记录见 docs/numerical-validation-v2.json。LightPipes 仅用于验证，不是应用运行依赖。普通提交的无 GUI 测试工作流已配置，真实 GUI 测试可手动触发；远端尚未执行本次新工作流。

## 构建 Windows 便携版

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
& .\scripts\install_cuda_runtime.ps1
& .\scripts\build_release.ps1
```

输出位于当前版本的 `releases/v3.0.0/`，不进入源码 Git。构建脚本优先复核已缓存的 Qt 对应源码，缺失时按固定官方 URL 和 SHA-256 下载；同时生成含随包 CUDA 的运行包、Qt 对应源码包、应用源码包和 SHA-256 清单。构建和发布过程见 [开发记录](docs/development-log.md)。
