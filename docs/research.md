# 开源与 Skill 调研

2026-11-20 续查了市售光束分析软件、商用传播仿真和开源光斑测量算法。产品资料、与 V3.1 的差距和分阶段开发建议集中在 [V3.2 迭代计划](iteration-plan-v3.2.md)。

首轮调研日期：2026-11-14。方法：GitHub 连接器检索与获取原仓库、文件、Releases；网页检索原仓库和官方文档。首轮当时未运行第三方实现或安装候选软件，不将该阶段状态当作当前结论。后续实际采用 LightPipes 独立对照、PyInstaller 打包与 CuPy CUDA，见下方分阶段复核及 development-log.md；V3 交付证据见 [发行验证](release-validation-v3.0.0.md)。

首轮兼容性和数值正确性均未实测；这一历史限制与后续实际验证记录分别阅读。

## Skill 查找

- 已阅读并使用本机 `find-skills` 工作流，先查看 [skills.sh](https://skills.sh/) 再按领域搜索。
- `npx skills find gaussian optics` 因 `registry.npmjs.org` 域名解析失败（ENOTFOUND）未完成；转用网页查找，不视为“没有相关 skill”。
- [matplotlib / k-dense-ai](https://www.skills.sh/k-dense-ai/scientific-agent-skills/matplotlib)：科学曲线、多面板、GUI 嵌入和图像导出相关。页面快照显示约 2.4K 安装，来源仓库约 57K stars；仅作为候选，尚未安装或执行，尚未完成源码级安全审查。
- [pyside6-engineer / vosslab](https://www.skills.sh/vosslab/vosslab-skills/pyside6-engineer)：检索命中桌面 GUI 方向，页面集合显示约 20 安装；证据较少，暂不作为主推荐。
- 目前未核实到专门覆盖高斯光束与光阑衍射的软件开发 skill。通用绘图 skill 不能代替物理模型验证。

## 仓库比较

| 项目 | 已核实功能与适用性 | 许可 | 维护与发布快照 | 本项目判断 |
| --- | --- | --- | --- | --- |
| [DCC-Lab/RayTracing](https://github.com/DCC-Lab/RayTracing) | ABCD、GaussianBeam、LaserPath；README 提及桌面 GUI，提醒其 Python 版本限制 | MIT，已读 LICENSE | 非归档，pushed_at 2026-07-08；Releases 首项 v1.4.7，2026-04-16 | 适合学习 q 参数及交叉验证；高斯模式不能计算光阑衍射 |
| [opticspy/lightpipes](https://github.com/opticspy/lightpipes) | 二维复振幅、光阑、透镜、Fresnel/FFT 衍射；官方说明测试过 Windows、macOS、Linux | BSD-3-Clause，已读 LICENSE.txt | 非归档，pushed_at 2026-02-26；GitHub Releases 首项 v2.1.3，官方文档标为 2.1.5 | 优先评估为衍射引擎或对照库；发布渠道版本存在差异，需核验后锁定 |
| [jzli559/GaussianBeam](https://github.com/jzli559/GaussianBeam) | README 展示 ABCD、NumPy/SymPy、PySide6+pyqtgraph、元素列表、单位、JSON 保存 | Apache-2.0，仓库元数据及 pyproject 一致 | 非归档，pushed_at 2026-08-03；pyproject 0.1.0 / Alpha；GitHub Releases 为空 | 功能与 GUI 很贴近；参考交互和模块拆分，不能据此认定成熟稳定 |
| [Diffractio 原仓库](https://github.com/aocg-ucm/diffractio) | 标量/矢量衍射及多种传播算法，README 指向迁移地址 | 旧 README 声明 GPLv3；新仓库 API 返回 NOASSERTION | 原 README 指向 [optbrea/diffractio](https://github.com/optbrea/diffractio)，新仓库 pushed_at 2026-11-03 | 功能范围较大；新仓库许可待逐文件核实，本轮不纳入首选依赖 |

时间使用 API 返回的 pushed_at，不等同于最后一次实质性算法修改。以上是调研快照，并非包安装兼容性承诺。

## 源码学习记录

### RayTracing：q 参数与模型边界

已阅读 [raytracing/gaussianbeam.py](https://github.com/DCC-Lab/RayTracing/blob/master/raytracing/gaussianbeam.py)。

- 构造函数允许以 q 或 w、R 初始化，二者同时提供时检查一致性；可借鉴为输入互斥模式与校验。
- 使用 `1/q = 1/R - i λ/(π n w²)`；束腰相对当前面的位置为 `-Re(q)`，瑞利长度由 `Im(q)` 提取。
- `isClipped` 只是截断状态标记；源码注释及 README 明确说明高斯形式不处理真实光阑截断。不能把几何光线的孔径阻挡能力套用到高斯衍射上。
- 项目应统一内部 SI 单位；不能照搬外部示例中的数值而忽略其单位约定。首版空气模型 n=1；若以后加入介质，需要重新审查所有束腰公式中的 n。

### LightPipes：复振幅传播

已阅读 [LightPipes/propagators.py](https://github.com/opticspy/lightpipes/blob/master/LightPipes/propagators.py) 的 Fresnel 实现入口与说明，参阅 [官方命令手册](https://opticspy.github.io/lightpipes/command-reference.html)。

- 传播对象包含复振幅、采样间距和波长；衍射引擎应保留场数据，而非只传递一个光斑半径。
- Fresnel 采用卷积传播；入口拒绝负距离，零距离返回副本，避免隐式共享状态。这些边界适合纳入后续测试。
- 真实光阑需通过场遮罩处理，再传播；应验证采样、计算窗口、功率归一化和焦区分辨率。
- 模型需暴露网格与窗口收敛状态；“结果有图像”不能作为数值正确的证据。

### GaussianBeam：GUI 与依赖

已阅读 README 与 [pyproject.toml](https://github.com/jzli559/GaussianBeam/blob/main/pyproject.toml)，检查目录；GUI 源文件本轮未成功取得，以下交互结论来自 README，不宣称已审查 GUI 实现。

- 光路元素列表、单位选择、轴向包络探针、束腰结果及 JSON 保存适合作为本项目交互参考。
- pyproject 声明依赖 NumPy、SymPy、PySide6、pyqtgraph，GUI 入口为 `gaussianbeam.gui:main`。
- 首版不必引入符号计算和两套绘图库：建议数值内核与 GUI 解耦，先用 Matplotlib 完成论文图、光斑图及桌面嵌入。

## 复用策略与下一步

### 3D 展示补充调研

- 用户确认多透镜与扫描需求后，提出优先使用有视觉冲击力的 3D 展示。
- [PyVistaQt 原仓库](https://github.com/pyvista/pyvistaqt)：README 定位为 Qt 应用中的 PyVista 集成，仓库显示 MIT 许可；适合评估 PySide6 桌面中的交互三维场景。
- [PyVista 官方体渲染示例](https://docs.pyvista.org/examples/02-plot/volume_rendering)：展示体数据的颜色及透明度映射，可参考用于光场强度可视化；光学传播仍由独立计算内核负责。
- 本轮为文档与仓库能力调研，未安装或运行 PyVista/VTK，未做性能、显卡兼容性或许可证依赖链的完整审查。此方案为优先候选，不宣称已完成选型验证。

- 建议自主编写规模较小、可解释的 ABCD 解析核心，使用外部库作为独立对照；衍射部分优先评估 LightPipes，评估后决定依赖还是自主实现。
- 本轮仅记录知识与来源，未复制第三方实现代码。以后复制或修改代码时保留对应版权、许可证与必要 NOTICE；依赖发布另核对分发义务。
- 拟采用 Python 3.12 环境进行依赖验证；本机 `python --version` 为 3.15.2，不能由此推定科学计算和 Qt 依赖可用，尚未创建环境。
- 开发前选定上游发布版本或 commit，完成 Windows 安装、无光阑基准、焦区精度、GUI 嵌入与打包冒烟测试。未通过前不把候选写成已选定依赖。


## 数值增强阶段补充核验（2026-11-14）

再次读取 LightPipes 原仓库 README、LICENSE.txt 与 propagators.py，沿用前期 GitHub 调研。实际安装 PyPI 的 LightPipes==2.1.5 到项目 .venv；包内 LICENSE.txt 为 BSD-3-Clause，METADATA 同时存在 MIT 分类标签，许可判断以随包完整 LICENSE 为依据。仅作为可选验证依赖，不替换产品内核，也不加入运行依赖快照；未复制第三方算法源码。

采用 `Begin` 后显式赋予标准高斯复振幅，再调用 `Fresnel`、`Lens`、`CircAperture`，避免高斯解析快捷分支。已核对坐标数组与内部 SI 网格一致。外部对照使用卷积传播，本项目使用周期窗口频域传递函数，算法和有限窗口处理不同；差异需结合案例与分辨率分析，不把外部程序视为无误差真值。源码中的 legacy 采样处理也提示不能只按接口名称假定离散结果完全一致。

原始来源：[仓库说明](https://github.com/opticspy/lightpipes)、[传播源码](https://github.com/opticspy/lightpipes/blob/master/LightPipes/propagators.py)、[许可证](https://github.com/opticspy/lightpipes/blob/master/LICENSE.txt)。本次版本、输入、实测结果与限制见 [数值增强验证](validation-v2.md)。


## V2.0.0 便携构建复核

沿用已有 PyInstaller 目录模式与 Qt 动态库分发方案，再读取 [PyInstaller 原仓库](https://github.com/pyinstaller/pyinstaller)和 [6.22.3 使用说明](https://pyinstaller.org/en/stable/usage.html)，本次继续使用已锁定的 6.22.3。EXE 版本资源、分版本输出目录和固定摘要的 Qt 缓存用于保证版本可辨识及构建可追溯。

[Qt 6.12 Windows 支持说明](https://doc.qt.io/qt-6/windows.html)列出 Windows 10 1809 及以后版本、Windows 11 的 x86_64 支持。本项目以 Windows 10/11 x64 为目标，实际只记录本机与隔离运行结果；这不是对全部 Qt 支持平台、显卡或其他实体设备的验证承诺。冻结测试还需覆盖实际 SVG/PDF 导出，源码环境通过不等于打包后相关后端一定存在。

## CUDA 分支重新调研（2026-11-14）

先查阅 [CuPy 原仓库](https://github.com/cupy/cupy)、[发布版本](https://github.com/cupy/cupy/releases)、[FFT 实现](https://github.com/cupy/cupy/blob/main/cupy/fft/_fft.py)及 [官方安装说明](https://docs.cupy.dev/en/stable/install.html)。CuPy 为 MIT 许可，提供 NumPy 风格数组与 cuFFT，Windows 有 CUDA 12/13 预编译轮子；本次固定 CuPy 14.2.0 和 CUDA 12.9 组件，不从最新主分支复制算法。

沿用物理模型，借鉴可选数组/FFT 后端，不引入另一套光学求解器。实际发现 NVIDIA 路径查找器按 site 安装前缀发现组件；独立运行库除加入 sys.path 外还注册 site.PREFIXES，不修改第三方函数。ASCII 独立目录避免前次中文编译路径兼容层；没有设备或依赖时回退 CPU。本机已实际执行 CUDA，不把成功安装、GPU 渲染或回退 CPU 的运行当作 CUDA 验证。性能、可移植边界及源码启动说明见 [加速说明](acceleration.md)。

## V3 便携 CUDA 组件

补读 [CUDA 12.9 官方 EULA](https://docs.nvidia.com/cuda/archive/12.9.1/eula/index.html)的运行库/头文件分发清单和 [CuPy 官方安装说明](https://docs.cupy.dev/en/stable/install.html)。V3 随包采用 cudart、NVRTC、cuFFT、nvJitLink 运行 DLL、CuPy 与 cuda-pathfinder，保留原始许可；不打包系统驱动。只保留可再分发头文件时实际无法满足 CuPy 的 cudart 目录检测，完整编译头文件改为首次从 NVIDIA 官方 PyPI 固定 wheel 在本机补充，URL、版本、字节数与 SHA-256 固定，不把所有 Toolkit 开发文件混入分发目录。

外置 CuPy 的 Cython 扩展动态导入 graphlib，单靠静态 AST 分析遗漏；实际 CUDA 加载模块记录用于补齐冻结依赖，并以隔离 EXE 实测验收。源码测试通过与 EXE 可运行仍是不同证据。

## 下一版本升级意见（2026-11-18，讨论稿）

建议将 V3.1 定位为光路实验对比版。V3 已支持自动预览、CPU/CUDA、观察屏和单次结果导出。典型操作是保存大口径透镜为方案 A，缩小通光直径得到 B，在同一观察面比较透过率、光斑剖面与包围能量，再查看两套光路各自的最佳焦面。

| 优先级 | 建议与依据 | 验收方法 |
| --- | --- | --- |
| 首选 | 为理想薄透镜增加可选有效通光直径。[RayTracing 发行记录](https://github.com/DCC-Lab/RayTracing/releases/tag/v1.4.6)展示焦距与直径并列输入。GaussianLab 可沿用已有圆孔复场遮罩处理衍射。 | 旧 JSON 缺省为无限口径并复现旧结果。有限口径与同位置薄透镜加独立圆孔比较透过率、剖面及 r86。 |
| 首选 | 固定 A/B 两次完整计算的参数和结果，共用横坐标和强度标尺，导出同一张白底对照图。分别标明固定观察面和各自焦面。 | 切换观察面后 A/B 位于同一物理 z。修改 B 时 A 保持原值。比较绝对强度时使用相同入射功率基准，单图归一化另行标明。 |
| 次选 | 增加 x–z 纵向强度图。沿传播方向取每个观察面的中心剖面，点击热图定位观察屏。[Diffractsim](https://github.com/rafael-fuente/diffractsim)提供透镜纵剖面示例。 | 选取三个已采样 z 核对热图与现有横向剖面。按需生成、允许取消，在 CPU 和 NVIDIA 设备上分别记录时间及峰值内存。 |
| 后续实验 | 对出现采样警告的案例，用另一种算法复核。[waveprop](https://github.com/ebezzam/waveprop)提供 Fresnel、带限角谱与直接积分对比示例。 | 固定相同波长、窗口、采样和归一化，记录随网格加密的误差，并与已有 LightPipes 对照衔接，再决定是否增加用户可选算法。 |

性能验收贯穿上述改动。用 V3 和候选版本在同机重复连续改参，分别记录首次启动、热启动后从最后一次输入到正确画面的延迟、界面最长停顿和实际计算后端，检查旧任务没有覆盖新结果。优先覆盖朋友使用的 NVIDIA 电脑，另测无独显电脑。新增实验图按需生成，避免每次输入都增加计算量。

以上为原项目公开说明与本地 V3 文档对照所得的设计建议。本轮未安装这些项目或测量新功能性能。采用代码或增加分发依赖前应针对选定版本复核许可及 Windows 兼容性。


## 相干横模与提高采样（2026-11-23）

沿用已有 LightPipes 调研，补读原仓库 [core.py](https://github.com/opticspy/lightpipes/blob/master/LightPipes/core.py)、[sources.py](https://github.com/opticspy/lightpipes/blob/master/LightPipes/sources.py) 和 [BSD-3-Clause 许可证](https://github.com/opticspy/lightpipes/blob/master/LICENSE.txt)，并用项目已安装的 LightPipes 读取 GaussHermite/GaussLaguerre 源码。借鉴横模与复场求和的模型划分；自行实现 Hermite、广义 Laguerre 递推，直接使用既有 NumPy/CuPy 数组后端，不复制上游代码，不增加运行依赖。

独立源场对照的首轮 LG 比较失败，查明本项目 exp(+i lφ) 与 LightPipes ecs=0 的 exp(-i lφ) 相反；测试显式翻转上游 l，再比较同一物理场。HG 的 x/y 阶数字段也显式对应，不能仅按形参名字比较。高阶模式不再假设圆对称高斯，保留基模包络参考但给出警告，实际半径和角度继续来自数值能量积分。

采样策略保持定长二维网格和完整强度体积，增加默认横向网格及可选上限，保留结果体积限制与轻量预览。未采用“插值放大图像”来代替提高计算采样。2048 网格与高轴向点数组合的内存限制是当前取舍，其他实体设备、便携包与所有高阶参数仍需后续验证。


## CuPy 安装与交付复核（2026-11-23）

重新查看 [CuPy 原仓库](https://github.com/cupy/cupy) 与 [14.2.0 官方安装说明](https://docs.cupy.dev/en/stable/install.html)，确认 Windows 预编译轮子与 Python 3.10、CUDA 12.x 路径。继续使用项目锁定版本，安装光场/FFT 需要的 6 个组件，沿用 MIT 与 NVIDIA 原始许可，不改变系统驱动。安装到应用私有 ASCII 目录并真实执行 GPU FFT；测试沙箱重定向 LOCALAPPDATA 的状态与用户真实环境分开记录，不把沙箱缺库误报为用户系统缺库。安装、冻结与额外高阶输入对照见 V3.1.1 验证。

本轮继续沿用既有随包 DLL/头文件分发边界。读取已安装轮子的原始 NVIDIA 许可证，尝试打开归档 EULA 页面时网络连接失败，未据此扩展分发范围；完整头文件轮子由使用者自行从官方获取或使用其本机缓存，不加入运行包或源码 ZIP。离线与在线流程保持同一固定摘要校验。


## 内存规划、低占用显示与焦面像素映射（2026-11-23）

先查看 [psutil 原仓库](https://github.com/giampaolo/psutil)（BSD-3-Clause）及其系统/进程内存区分，再读取 Microsoft [GlobalMemoryStatusEx](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex)、[GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo) 与 [CuPy memGetInfo](https://docs.cupy.dev/en/stable/reference/generated/cupy.cuda.runtime.memGetInfo.html)。采用 Windows 自带 API，无新增依赖；界面不为读数初始化 CUDA。显存显示工作区估算，并非查询出的空闲显存。

复查 [PyVistaQt 原仓库](https://github.com/pyvista/pyvistaqt) 的 Qt 渲染集成，保留按需三维，新增不依赖 VTK 的 Matplotlib 二维示意；模块惰性导入，退出三维移除并关闭渲染上下文，明确库仍可能驻留。参考 Matplotlib 官方 [鼠标事件](https://matplotlib.org/stable/gallery/event_handling/coords_demo.html) 与 [imshow 坐标/插值说明](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.imshow.html)，自行实现近点工具提示，不增加 mplcursors 依赖或复制上游代码。

焦面检查发现：旧 imshow 将第一像素中心放在 x[0]+dx/2，光轴整体偏移半像素；bilinear 插值和固定最小 0.15 mm 半视野会掩盖小光斑的离散结构。修复范围是坐标映射、显示插值和视野，不将模拟光斑强制修改为理想高斯。孔径衍射、高阶模式、欠采样与有限窗口仍应区分；原始强度、解析基准与独立传播对照用于验证。


### LG/TEM 与磁盘映射补充（2026-11-23）

复用此前 LightPipes 原仓库的 HG/LG 模型调研，不引入额外物理库。用户确认 TEM00/10/20/21/03/30/11 和 TEM01+TEM10；横模按 HG 实现，LG01—05 按 p=0、l=1—5 解释。参考 [LightPipes core 源码](https://github.com/opticspy/lightpipes/blob/master/LightPipes/core.py)，不复制第三方代码。

内存扩展查看 [NumPy memmap 官方接口](https://numpy.org/doc/stable/reference/generated/numpy.memmap.html)：文件映射支持 ndarray 式切片，但页缓存与子类视图生命周期不能忽略。实现私有临时文件、发布前批次写回/重映射、发布后由视图共享所有者，最后引用释放时清理；没有新安装依赖。不能宣称磁盘映射等于零 RAM。

显示参考 [Matplotlib 插值方法](https://matplotlib.org/stable/gallery/images_contours_and_fields/interpolation_methods.html)。保留像素中心对齐，默认 bilinear、data 阶段插值，提供 nearest 检查原始像素；曲线与悬停数据仍读原始数组。以已有解析/独立传播验证和新增模式、存储及真实界面测试验收，见 modes-storage-validation.md。


### 图表范围编辑（2026-11-23）

查看 [Matplotlib 原仓库 Qt 图形选项源码](https://github.com/matplotlib/matplotlib/blob/main/lib/matplotlib/backends/qt_editor/figureoptions.py)，借鉴按坐标维度读取和应用范围、校验输入的交互方式。使用项目已有 Qt/Matplotlib API 自主实现中文精简范围编辑器，未复制第三方代码或新增依赖。每图一个按钮，多数据子图可选；排除颜色条，双轴共享横轴同步，先捕获所有自动范围再应用手动范围，避免共享轴污染默认值。范围与导出快照独立于物理输入。


### 三维相干模式对应（2026-11-23）

查看 [PyVista 原仓库 contouring 示例](https://github.com/pyvista/pyvista/blob/main/examples/01-filter/contouring.py)，参考 StructuredGrid 与 contour 的数据标量等值面方式；实际使用项目已安装的 PyVista、VTK、SciPy map_coordinates，自主实现有界的自适应横向抽样，未复制外部代码、未新增依赖。放弃以多层圆管模拟高阶模式，改由实际强度提取 0.15/0.5 的逐面归一化形状。保留 r86 外罩作低透明参考。屏幕选择原始像素并保留光轴，统一与二维的模式标签、z、归一化和对数。原理限制及实际截图见 USER_GUIDE.md。


### 默认三维启动闪退与线程缓存生命周期（2026-11-23）

检查用户当日三份 Windows minidump，发现 0xC0000409/0xC0000374，工作线程栈包含 CuPy fft/_cache、VTK、Qt；独立进程按实际启动顺序重复出现堆损坏及访问冲突。只运行 CPU 对照成功，关闭 Python 自动 GC 的对照仍失败，不能用永久关闭 GC 解决显式回收。

查看 [CuPy 14.2 FFT 缓存原始源码](https://github.com/cupy/cupy/blob/v14.2.0/cupy/fft/_cache.pyx)：线程私有缓存析构会清理链表并显式调用 gc.collect。结合线程追踪，确定本次触发路径为线程退出时的全局回收与 VTK 对象生命周期冲突。参考 [Qt QThread finished/wait 文档](https://doc.qt.io/qt-6/qthread.html#finished)，finished 发出时线程局部析构仍可能未完成，因此仅监听信号不足，必须 wait 后释放持有引用。

采用应用层持有线程 FFT 缓存、主线程队列完成通知、wait 后由主线程清理的修复；未修改 CuPy/VTK 第三方源码，也未重装依赖或关闭三维/CUDA。新增独立解释器回归真实启动顺序，覆盖先建三维、CPU 预览、首次 CUDA 和重复完整计算；避免既有测试先在主线程初始化显卡造成遗漏。具体结果见 startup-crash-validation.md。
