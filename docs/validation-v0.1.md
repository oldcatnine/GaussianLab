# V0.1 验证与交付记录

日期：2026-11-14。版本关联提交主题：`feat: deliver GaussianLab v0.1 desktop optics simulator`。

## 环境与执行方式

实际使用本机已有 Python 3.10.11 创建独立 .venv，安装 NumPy 2.2.6、SciPy 1.15.3、PySide6 6.12.0、PyVista 0.49.2、PyVistaQt 0.13.2，完整版本见 requirements-lock.txt。平台标识与数值数据见 [机器可读验证结果](validation-v0.1.json)。本轮未安装原计划的 Python 3.12。

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m pytest tests -q -p no:faulthandler
& .\tests\Test-Agents.ps1
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/validate_v1.py
git diff --cached --check
```

## 自动化验证

- 23 项数值/数据测试：解析束腰与瑞利长度、正负束腰偏移、多透镜组合矩阵、数值聚焦、圆孔透过率、光阑远场展宽、远场定义、非法参数、配置往返、扫描逐点一致性、取消、功率守恒、末端收敛及 CSV。
- 4 项真实 Qt/VTK 冒烟测试：画布渲染、三种光斑标签、观察屏、传播播放、参数变更和快照隔离、保存、扫描表/图及 CSV 元数据、元件增删和校验；对透过率轴固定范围增加断言。
- 7 项文档测试：需求覆盖、链接、设计边界、汇总方案与持续记录。
- 合计 34 项通过，已核对正常退出码 0；规则脚本 PASS，pip check 未发现依赖冲突。

测试不是任意参数精度认证；GUI 用低网格缩短冒烟耗时，精度验证使用独立数值基准。

## 数值案例与截图

| 案例 | 参考高斯束腰 | 离散最小 r86 | 对应全局 z | 末端透过率 |
| --- | --- | --- | --- | --- |
| 单透镜聚焦 | 53.70 μm，z=219.72 mm | 52.41 μm | 218.75 mm | 约 100% |
| 双透镜扩束 | 750.00 μm，回推 z=-680.00 mm | 775.92 μm | 160.00 mm | 约 100% |
| 光阑衍射 | 无截断参考 37.18 μm，z=219.93 mm | 78.61 μm | 218.75 mm | 61.66% |

上述 w 与 r86 定义不同，不能直接把差值视为误差。各案例横向网格 512，轴向 65 个均匀点并补入元件位置。单次纯 simulate 计算耗时约 1.66—1.74 s，不含 UI 绘制、启动和文件导出；仅为本机单次记录，不构成性能保证。

末端 r86 示例检查使用聚焦案例 N=256、33 个均匀轴向点：加密网格相对变化约 0.0152%，扩大窗口相对变化为 0。该零变化是离散能量分位点的测量结果，不表示全部指标精确无误，尤其不覆盖焦区或远场收敛。

真实 Qt/VTK 运行生成的素材（通过软件自身截图接口保存，不是设计效果图）：

- [聚焦桌面](assets/focus-desktop.png)、[聚焦三维场景](assets/focus-scene.png)、[输入](assets/focus.json)。
- [扩束桌面](assets/expander-desktop.png)、[扩束三维场景](assets/expander-scene.png)、[输入](assets/expander.json)。
- [光阑衍射桌面](assets/diffraction-desktop.png)、[光阑三维场景](assets/diffraction-scene.png)、[输入](assets/diffraction.json)。

## 插件自测

使用 [computer-use Skill](C:/Users/11795/.codex/plugins/cache/openai-bundled/computer-use/26.1106.51428/skills/computer-use/SKILL.md)，通过 node_repl 导入 @oai/sky，以返回的真实窗口对象操作，读取可访问性树及截图。

已实际操作并观察：

1. 单透镜启动自动计算，显示参考束腰 53.7 μm / 219.7 mm，数值最小 r86 为 52.4 μm / 218.8 mm。
2. 选择并加载双透镜扩束，显示两片透镜、扩束包络与回推束腰提示。
3. 对扩束案例的首片透镜执行 9 点焦距扫描，观察完成状态及扫描曲线。
4. 切换强度曲面标签，看到真实强度曲面；拖动三维画布，确认视角发生变化。
5. 改变观察屏，数值由 160.00 mm / 775.9 μm 更新为 406.25 mm / 797.5 μm。
6. 更新版本重新启动后观察到实验台网格、支座、分层光束与传播播放入口；选择并加载光阑衍射案例，观察到 r86=78.6 μm、透过率 61.66%。
7. 在更新版本中执行 0.45—1.35 mm 的 9 点光阑扫描，观察到完成状态、最小 r86 曲线及 0—105% 范围的透过率轴，验证图表修复。

插件截图和可访问性结果用于交互核查；文件截图由独立证据脚本生成，不混称为插件截图。保存/导出及取消的自动化证据来自 Qt 测试和内核测试，尚未把所有文件对话框逐一通过插件操作。

## 发现的问题与修复

- 扫描图透过率接近常数时自动放大浮点误差：固定百分比轴为 0—105%，增加回归断言。
- 后台启动尝试未维持窗口：改用已验证的前台模块启动，提供 CMD/PowerShell 启动器。
- 图形测试曾出现“断言全部通过但进程退出码异常”：修复测试中窗口生命周期，显式 close、deleteLater 并处理 DeferredDelete，使用 session 范围 QApplication；修复后默认及对照命令均 34 项通过且退出码 0。
- 默认 pytest faulthandler 仍可能打印 Windows COM 0x8001010d 诊断。[PyVistaQt 上游同类报告](https://github.com/pyvista/pyvistaqt/issues/13)及 [pytest-qt 讨论](https://github.com/pytest-dev/pytest-qt/issues/426)支持将其作为独立环境诊断调查；本机对照关闭 faulthandler 后测试正常。本轮未声称修复底层 COM 问题，也未在产品运行中关闭诊断。
- 插件初次窗口访问超时、一次弹出菜单截图出现 no monitor found：重新枚举并绑定窗口后恢复，未继续使用失效坐标。

## 首版交付边界

已交付源码、本机隔离环境、启动器、多透镜与两个指定案例、附加光阑案例、3D 观察屏和传播播放、两类扫描、保存导出与验证素材。

仍待完善：独立 EXE、透镜自身有效口径（当前可用同位置独立光阑表示）、显示状态保存、光路行拖动排序、扫描动画、焦点局部细化、完整多指标收敛。硬孔径长尾及周期窗口可能影响结果，当前诊断提示不能替代收敛实验。
