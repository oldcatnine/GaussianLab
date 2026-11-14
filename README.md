# 高斯光束传输计算器

课题：高斯光束经简单光学系统的传输仿真与光斑质量分析软件设计。

采用 Python 开发，当前版本为 **V0.1 首个可运行版本**：已实现多透镜解析参考、二维 Fresnel 衍射、3D 光路、观察屏联动、轴向与焦距/孔径扫描、配置保存和数据导出。

## 启动

**发给老师：** 下载 [V0.1.0 Release](https://github.com/oldcatnine/GaussianLab/releases/tag/v0.1.0) 的 `GaussianLab-v0.1.0-Windows-x64.zip`，完整解压后双击 `GaussianLab.exe`，无需 Python。保留 `_internal` 文件夹。仓库当前按私有创建，直接在线访问需要授权；也可下载 ZIP 后转发。详见 [便携版使用说明](docs/USER_GUIDE-v0.1.0.md)。

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

## 使用与边界

- 左侧设置光源和光路。表格中的透镜数值为焦距、光阑数值为直径，单位 mm；元件按 z 排序，同位置按表格顺序执行。
- 三维场景可鼠标拖动旋转、滚轮缩放；“播放传播”让观察屏沿光轴移动，联动二维光斑、剖面或强度曲面。
- 选择扫描元件与起止值，点击“开始扫描”。曲线显示末片透镜后离散采样点中的最小 r86；数据表与 CSV 保留警告/失败点。
- JSON 保存可恢复光路和计算参数。CSV 同步导出参数快照；扫描额外记录扫描范围。当前支持曲线 PNG/SVG/PDF 和场景 PNG，尚未保存相机、观察屏等显示状态。
- 所有图形基于单色同轴、标量近轴、理想薄透镜与圆孔模型。解析 w 为高斯参考；衍射 r86 为 86% 包围能量半径，二者定义不同。
- **本版是可验证的首版，不是任意光路的高精度保证**：Fresnel FFT 使用有限周期窗口，焦点为轴向离散搜索；高 NA、复杂像差与 M² 不在当前范围。“收敛检查”仅比较末端 r86，不能替代焦区、能量和远场的全面验证。
- 三维横向尺寸放大 25 倍，透镜外形及支座为示意；透明包络是 r86 轮廓，内部亮芯为展示辅助，不能当作三维强度测量。
- 光阑目前为独立元件；透镜有效口径、光路行拖动排序和扫描动画播放留待后续版本。

## 项目文档

- [需求记录](docs/requirements.md)：用户已提出的需求、建议补充参数与验收规划。
- [开源与 Skill 调研](docs/research.md)：来源、源码学习、许可和适用边界。
- [产品设计草案](docs/product-design.md)：拟议界面、计算路线和待讨论事项。
- [产品设计方案 V1.0](docs/product-plan.md)：汇总需求、功能、3D 视觉、架构、开发阶段及验收标准，作为当前完整设计入口。
- [开发过程与能力方法记录](docs/development-log.md)：随每次工作同步更新，积累毕业设计报告所需的过程、工具方法、验证和问题处理证据。
- [V0.1 验证与交付记录](docs/validation-v0.1.md)：自动化测试、插件自测、数值结果、实际截图和首版局限。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
& .\tests\Test-Agents.ps1
git diff --check
.\.venv\Scripts\python.exe scripts/validate_v1.py
```

test_optics.py 为数值和数据验证；test_gui.py 为真实 Qt/VTK 冒烟测试，需可用桌面与渲染环境；test_project_docs.py 为文档验证。Windows 上 pytest faulthandler 可能打印 COM 0x8001010d 诊断，复核方式与本次结果见后续验证记录；不要仅据该行或隐藏诊断判断成功，需检查退出码和断言。

源码与测试由本项目编写，第三方依赖及参考见 [第三方说明](docs/third-party.md)。

## 构建 Windows 便携版

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
& .\scripts\build_release.ps1
```

输出位于 `releases/v0.1.0/`，不进入源码 Git。构建脚本下载并校验 Qt 对应源码，需要联网；Release 将运行包、对应源码包和 SHA-256 清单作为独立附件。构建和发布过程见 [开发记录](docs/development-log.md)。
