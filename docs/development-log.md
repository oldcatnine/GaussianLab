# 开发过程与能力方法记录

课题：高斯光束经简单光学系统的传输仿真与光斑质量分析软件设计。

建档日期：2026-11-14。日期按 Asia/Shanghai 记录；历史条目由当前对话、项目文件和 Git 历史追溯，不补造具体时刻或耗时。

## 1. 记录目的与维护方式

本文件用于积累毕业设计报告的过程证据，覆盖需求分析、开源调研、系统设计、开发实现、测试验证、问题处理与成果交付。

- 每次有实质进展、决定或失败尝试时同步更新；每次交付和 commit 前补齐对应条目。这里的“实时”指随项目工作同步维护，不表示在会话之外持续监控。
- 历史记录原则上保留；发现错误时注明修正及依据。阶段总结可以更新，但不能覆盖关键失败与决策记录。
- 引用文件、提交、命令和结果，区分“提出”“调研”“实现”“验证通过”。读取 skill 不等于已采用其全部流程，搜索命中不等于安装或运行成功。
- 当前提交用唯一主题关联，提交后由 Git 查询哈希；下一次工作可补齐上一条记录的哈希，避免修改文档记录自身哈希造成循环提交。
- 图表、实验与截图在真实生成后记录路径、输入参数、算法版本、环境、单位和结论；不存在的证据不提前填写为已完成。
- 本文件建档时只有设计与文档测试；后续实现与验证进展以阶段记录和当前总览为准。

## 2. 当前阶段总览

| 项目 | 当前状态 |
| --- | --- |
| 版本管理 | v3.0.0 应用基线 b4806c3；私有仓库已正式发布，后续文档与发布通道提交另行追踪 |
| 需求 | 多透镜、聚焦/扩束/光阑案例、扫描、3D、白底导出及可选 CUDA/自动预览均有实现与证据 |
| 开源调研 | 分阶段完成源码/许可检查；LightPipes 已实际用于独立对照，CuPy 用于 CUDA；初期候选未使用的状态保留在历史条目 |
| 产品设计 | V1.0 设计稿作为历史规划；当前功能与限制以 requirements、USER_GUIDE、V3 验证为准 |
| 计算内核/GUI/3D | q 参数与 Fresnel、焦区细化、多指标收敛、可选 CUDA、自动预览/缓存、Qt/VTK 和白底导出已实现 |
| 验证 | DEV-019 交付时完整 98 项测试通过；远端下载版 CPU/CUDA、首次补充、图形与导出检查通过；不代表任意参数精度或跨全部设备验证 |
| 环境 | 运行/构建基线为项目 Python 3.10.11；便携版无需系统 Python，首次 CUDA 需联网补齐固定官方头文件；源码重建启用 UTF-8 |

## 3. 实际使用的能力、工具与方法

本节表格保留建档阶段的方法与当时状态；后续实际采用的 LightPipes、PyInstaller、CuPy、GitHub Actions 与回下载方法分别见 DEV-012、DEV-017—DEV-020，不将早期“未实测”当作当前结论。

| 能力或方法 | 实际使用方式 | 状态与证据 |
| --- | --- | --- |
| 需求梳理与范围管理 | 将对话拆成 R01—R10，区分确认需求和建议，补充波长、入射光束等必要参数 | 已用于 [需求记录](requirements.md) |
| Skill 查找 | 阅读本机 `find-skills`；查看 skills.sh，执行关键词检索 | 已使用；CLI 失败，网页检索完成补充 |
| GitHub 优先调研 | 用 GitHub 连接器的 search_repositories、fetch 检索仓库、读取文件及 Releases | 已用于 [调研记录](research.md)；未安装或运行仓库代码 |
| 网页检索与官方文档核对 | 使用 web 搜索与打开原仓库、skills.sh 和官方文档 | 已用于衍射、GUI 和 3D 方案调查；来源见调研文档 |
| 源码与许可审阅 | 阅读 RayTracing 的 gaussianbeam.py、LightPipes 的 Fresnel 入口、GaussianBeam 的 pyproject 及部分许可证 | 已完成限定范围阅读，不等于完整代码审计 |
| 技术比较与模型边界分析 | 比较 ABCD 与复场传播；区分 w/r86、θ/θ86，识别网格与窗口误差 | 已用于设计；算法尚未实现或实测 |
| 3D 产品交互设计 | 规划实验台、观察屏、强度曲面、视觉放大与多视图联动 | 设计已记录，未生成可运行场景 |
| 本地命令行 | functions.exec 编排 exec_command；PowerShell 读取文件、检查环境、运行 Git 和测试；rg 做定向查找 | 已使用，不代表修改系统或安装依赖 |
| 文件编辑 | apply_patch 创建和修改 Markdown、PowerShell、Python 文件 | 已使用，变更由 Git 保存 |
| 文档自动验证 | Python unittest 检查需求覆盖、链接、章节和设计边界；PowerShell 检查协作规则 | 已执行，结果见阶段记录 |
| 版本控制与格式检查 | git init、add、diff --check、commit、status、log | 已执行；写入索引时使用执行环境的受控权限机制 |
| 写作参考能力检查 | 汇总设计方案时读取 write-like-me 的 SKILL.md | 仅查看说明，未检索用户写作样本、未完成风格匹配，不作为已应用成果 |

建档时上述科学计算与桌面库均为候选；截至 DEV-006，已实际使用 NumPy/SciPy、PySide6、Matplotlib、PyVista/VTK、PyVistaQt、pytest 和 computer-use 插件，具体版本及用途见该条目。matplotlib skill、LightPipes、PyInstaller 尚未实际采用，不能把候选与安装/运行结果混同。

## 4. 阶段记录

### DEV-001｜2026-11-14｜Git 初始化与协作规则

- 目标：将项目 Git 化，保存每次提交及测试要求。
- 操作与变更：确认目录不是 Git 仓库，执行 git init；新增 agents.md 和 tests/Test-Agents.ps1。
- 工具与方法：PowerShell、Git、apply_patch、规则文本验证。
- 结果：首次提交完成，工作区干净。
- 验证证据：Test-Agents.ps1 返回 PASS；Git 差异检查通过。
- 问题与处理：git add/commit 曾因无法创建 .git/index.lock 失败；通过受控权限执行 Git 写入后完成。未删锁或破坏历史。
- 关联提交：`ae68e77`，`chore: initialize project collaboration rules and validation`。
- 报告素材：开发过程管理、版本追踪与基础质量约束。
- 下一步：需求调研与产品设计。

### DEV-002｜2026-11-14｜需求记录与开源学习

- 目标：记录 Python 高斯光束计算器需求，查找 skill 和可复用开源方案。
- 操作与变更：创建 requirements.md、research.md、product-design.md、README.md 和 test_project_docs.py；形成初步功能与模型边界。
- 工具与方法：find-skills、GitHub 连接器、web、源码阅读、许可证比较、PowerShell、apply_patch、unittest、Git。
- 结果：比较 RayTracing、LightPipes、GaussianBeam 和 Diffractio；提出自主解析内核与可评估衍射库的方案。
- 验证证据：当时 4 项文档测试通过，原有协作规则验证通过，暂存区差异检查通过。
- 问题与处理：npx skills find gaussian optics 遇到 ENOTFOUND，改用网页检索；部分源码获取未返回可读内容，已在调研文档限制结论；Diffractio 迁移后许可未完全核实，未列为首选依赖。
- 关联文件：[开源与 Skill 调研](research.md)、[需求记录](requirements.md)、[设计草案](product-design.md)。
- 关联提交：`939530a`，`docs: record Gaussian beam requirements research and product proposal`。
- 报告素材：国内外/开源方案调研、技术路线比较、物理模型适用范围、开源许可意识。
- 下一步：与用户确认多透镜、曲线范围及视觉方向。

### DEV-003｜2026-11-14｜多透镜、参数扫描与 3D 设计

- 目标：根据用户反馈扩展明确的需求范围，解释两类计算，设计有视觉冲击力的界面。
- 操作与变更：记录多片薄透镜、单透镜聚焦/双透镜扩束、轴向与焦距/光阑扫描；补充 3D 观察屏、强度曲面和演示动画设计。
- 工具与方法：需求追踪、GitHub/官方网页查阅、PyVistaQt 与体渲染能力调查、文档编辑和测试。
- 结果：优先评估 PySide6+PyVista/VTK 桌面架构；明确横向放大、伪彩和展示与物理数据一致性要求。
- 验证证据：当时 5 项文档测试通过，协作规则验证及暂存区差异检查通过。
- 问题与处理：3D 依赖、显卡与性能尚未实测，保留为候选选型；没有把三维展示称为完整三维电磁仿真。
- 关联提交：`18df815`，`docs: confirm multi-lens scans and propose 3D visualization`。
- 报告素材：需求迭代、人机交互、科学可视化设计、三维显示比例与精度边界。
- 下一步：汇总完整产品设计方案。

### DEV-004｜2026-11-14｜产品设计方案 V1.0

- 目标：将分散的需求和技术建议整合成可用于后续开发的完整方案。
- 操作与变更：新增 product-plan.md，汇总 16 个部分，覆盖功能、模型、3D、扫描、架构、保存导出、阶段与验收；更新 README 入口和测试。
- 工具与方法：文档综合、需求状态区分、数据/模块设计、风险分析、apply_patch、unittest、PowerShell 与 Git。
- 结果：[产品设计方案 V1.0](product-plan.md) 完成；未将待验证依赖写成已实施结果。
- 验证证据：6 项文档测试与规则验证通过；修正格式后暂存区差异检查通过。
- 问题与处理：首次暂存区检查发现 Markdown 行尾双空格，阻止提交；改为空行分段，重跑测试和检查后提交。普通 git diff 不覆盖未跟踪文件，说明提交前暂存区检查仍有必要。
- 关联提交：`0c03199`，`docs: consolidate Gaussian beam product design plan v1`。
- 报告素材：总体设计、模块划分、数据设计、分阶段计划、测试与验收体系。
- 下一步：建立持续开发记录，随后开展环境与原型验证。

### DEV-005｜2026-11-14｜建立开发过程与能力方法记录

- 目标：响应用户要求，新建持续维护的记录，方便撰写毕业设计报告。
- 操作与变更：创建本文件；追溯前四轮工作；更新 agents.md 强制同步记录、README 导航及文档/规则测试。
- 工具与方法：读取当前项目与 Git 历史，按目标—操作—结果—证据—问题整理；apply_patch、PowerShell、unittest、Git。复用已有调研，本轮未重新联网或安装软件。
- 结果：建立统一台账、报告章节映射与后续记录模板；将实际采用、失败尝试和待验证能力分开。
- 验证证据：`python -B -m unittest discover -s tests -p "test_*.py" -v` 返回 7 项通过；更新后的 Test-Agents.ps1 返回 PASS；工作区差异检查通过。提交前另执行暂存区差异检查，作为提交门槛。
- 问题与处理：当前提交的自身哈希尚未生成，使用唯一提交主题关联，避免为回填自身哈希产生无限提交。
- 关联文件：本文件、agents.md、README.md、tests/test_project_docs.py、tests/Test-Agents.ps1。
- 关联提交主题：`docs: establish continuous development and methods journal`。
- 后续核实的提交：`c122c38`。
- 报告素材：研发过程追踪、工具辅助开发方法、质量保证与成果可追溯性。
- 下一步：若进入开发，先完成独立环境与最小 Qt+3D 原型验证，并按模板继续更新。

### DEV-006｜2026-11-14｜首个可运行版本 V0.1

- 目标：开发 Python 计算与 3D 桌面第一版，使用插件操作软件自测。
- 操作与变更：新增 gaussian_lab 模型、ABCD 解析、二维 Fresnel FFT、包围能量与角谱、参数扫描、Qt 界面、VTK 场景、Matplotlib 图表、配置与导出；提供启动脚本、锁定依赖、数值/GUI 测试、证据生成脚本及第三方说明。
- 工具与方法：复用前轮 GitHub 调研；PowerShell 检查本机解释器，venv 隔离依赖，pip 安装；apply_patch；NumPy/SciPy 数值计算；PySide6/Qt 工作线程；PyVista/VTK 三维渲染；Matplotlib；pytest；computer-use Skill 的 node_repl + @oai/sky 桌面插件；Git。
- 环境处理：原计划 Python 3.12 未安装；采用已有 3.10.11 创建项目环境。沙箱安装依赖曾发生代理连接拒绝，经受控网络权限后完成；未修改用户旧环境。版本快照见 requirements-lock.txt。
- 当前结果：23 项数值测试、4 项 GUI 测试、7 项文档测试合计 34 项通过；默认及关闭 faulthandler 的对照运行均核对退出码 0。规则脚本 PASS，pip check 无冲突。已生成 docs/assets 内三个案例的桌面/场景截图与输入 JSON，以及 docs/validation-v0.1.json；详细证据见 [V0.1 验证与交付记录](validation-v0.1.md)。
- 插件操作：通过 list_windows 选择实际窗口，读取截图/可访问性树；选择并加载双透镜案例，执行 9 点焦距扫描，切换强度曲面，拖动旋转 3D 场景并改变观察屏。实际观察到扩束结果、扫描完成和观察屏由 160.00 mm 变化到 406.25 mm。初次插件窗口访问审批超时，后续重试成功；初次窗口被 Codex 遮挡，通过点击目标标题栏恢复前景。
- 最终插件复核：更新版本成功加载光阑衍射，透过率 61.66%，并完成 0.45—1.35 mm、9 点孔径扫描；透过率轴范围修复在真实窗口中可见。一次弹出菜单截图提示 no monitor found，重新枚举窗口并绑定后恢复。
- 问题与处理：透过率图自动轴把浮点误差放大，改为 0—105% 并添加回归断言；扫描状态明确说明主场景保留上次光场；增加内存上限与收敛检查分批释放；初次 Start-Process 后台启动未形成持续窗口，使用前台 Python 进程成功运行，提供命令行启动器。
- 测试环境诊断：Qt/VTK 的 pytest 运行出现 Windows 0x8001010d faulthandler 输出；关闭其他测试窗口后仍可复现，不能归因为插件并发。随后全量测试发现断言通过但进程退出码 -1073740791，不能算通过。修复 fixture 的 QApplication/窗口清理顺序，显式处理 DeferredDelete 后，默认和对照运行都达到 34 项通过、退出码 0。查阅 PyVistaQt 原仓库 issue #13、pytest-qt issue #426；记录仍可能出现的 COM 诊断，不宣称修复底层 COM 问题。
- 证据与限制：当前为有限周期窗口的标量近轴模型；焦点为离散采样搜索；末端 r86 收敛检查不是全光路精度证明。三维包络来自 r86，内层亮芯为视觉辅助。尚未制作 EXE，未实现透镜独立有效口径、相机状态保存及扫描动画播放。
- 关联文件：gaussian_lab/、tests/test_optics.py、tests/test_gui.py、scripts/validate_v1.py、[验证数据](validation-v0.1.json)、[第三方说明](third-party.md)。
- 关联提交主题：`feat: deliver GaussianLab v0.1 desktop optics simulator`。
- 报告素材：计算方法、模块实现、数值验证、3D 科学可视化、人机交互、测试发现和版本局限。
- 下一步：后续完善焦区/远场收敛、扫描动画、透镜有效口径与打包。

### DEV-007｜2026-11-14｜Windows EXE 与 GitHub 首版发布

- 目标：应用无需安装 Python 即可运行，整理 V0.1.0 到 GitHub。
- 操作与变更：新增 PyInstaller 入口/spec、冻结 EXE 冒烟测试、构建/发布脚本、使用说明、版本说明和第三方声明；采用 onedir ZIP，保留可替换的 Qt 动态库和独立对应源码附件。
- 工具与方法：复用光学调研；补查 PyInstaller/Qt 官方文档与 hooks-contrib 原仓库；pip 安装 PyInstaller 6.22.3 与 hooks-contrib 2026.10；官方 Qt 源码下载与 SHA-256 校验；pefile 检查 DLL 导入导出；Git Credential Manager 非交互读取及 GitHub 官方 REST API；未输出或保存凭据。
- 结果：创建私有仓库 https://github.com/oldcatnine/GaussianLab，用户随后明确确认私有。GitHub 插件仅支持部分仓库读写，不支持创建仓库与 Release 二进制上传，因此改用官方 API 和 Git。最终运行 ZIP 约 175.8 MiB，第三方对应源码 ZIP 约 70.2 MiB。
- 问题与处理：首次冻结程序 QtCore DLL 加载失败。检查到 PyInstaller 从本机 Poppler PATH 误收集 icuuc.dll，其缺少 Qt 使用的 Windows ICU 无版本后缀符号；排除后使用 System32 ICU。另把包根目录较旧的 Python MSVC 运行库统一到 Qt wheel 附带版本，规则写入 spec。
- 验证证据：37 项测试通过，退出码 0，规则脚本和 pip check 通过。最终 ZIP 的 SHA-256/CRC 校验通过，解压至全新 outputs/portable-check 目录，再以仅含 Windows 系统目录的 PATH 运行 EXE；frozen=true，三个案例、Qt/VTK 截图、配置往返、三点孔径扫描及 CSV 均通过，退出码 0。结果见 release-smoke-v0.1.0.json、release-artifacts-v0.1.0.json。已通过 computer-use 插件绑定实际 GaussianLab.exe 路径检查窗口，首屏计算与三维渲染正常；新 EXE 首次访问超时，重新绑定后成功。
- 第三方处理：初次 hook 带入未使用的 Qt PDF/VirtualKeyboard/DataVisualization，已排除；下载并验证 qtbase/qtsvg/qtimageformats/pyside-setup 6.12.0，随发行提供完整对应源码与上游许可证文本。
- 最终插件复核：绑定从最终 ZIP 解压的 GaussianLab.exe，点击传播播放，观察屏从 218.75 mm 移动到 275.00 mm，r86 联动变化，随后暂停。打包版与源码版窗口身份分别核对。
- 关联文件：GaussianLab.spec、app_entry.py、gaussian_lab/release_smoke.py、scripts/prepare_release.py、scripts/publish_github.py、docs/USER_GUIDE-v0.1.0.md、docs/THIRD-PARTY-NOTICES.md。
- 关联提交主题：`build: package Windows v0.1.0 and prepare GitHub release`。
- 报告素材：部署方案、冻结依赖、动态库冲突排查、二进制验证、版本发布与许可证整理。
- 下一步：提交标签并推送首版 Release，发布成功后另补录 GitHub 返回的附件与版本信息。

### DEV-008｜2026-11-14｜发布通道优化与远端构建

- 目标：完成私有 GitHub Release 附件上传。
- 问题与处理：本机代理中小附件可上传，但约 176 MiB 主包上传极慢。使用 36 字节、2 MiB 临时探针测试并清理；直接 HTTPS 连通性测试失败，未更改系统代理。增加 1 MiB 上传块和进度、草稿续传保护，经新测试验证；本机累计 I/O 仍显示低速，改用 GitHub Actions 在远端构建并上传。
- 工具与方法：官方 GitHub REST API、requests/urllib3、只读进程 I/O 统计、browser-use 检查网页通道；浏览器未登录，没有自动操作认证或改变访问权限。使用官方 actions/checkout 和 setup-python 配置 Windows 构建，避免通过本机网络发送大型二进制。
- 验证：上传优化后 38 项测试通过；补充最终发布证据测试后全量 39 项通过，退出码 0，规则验证及 pip check 通过。本地 v0.1.0 原始构建记录保留；GitHub Actions 运行 43573110436 已 success，三个 Release 附件全部存在，draft=false、private=true。下载两个远端 ZIP，SHA-256 与 GitHub digest 及发布校验清单均一致，ZIP CRC 通过；远端 EXE 隔离 Python 后三个案例、Qt/VTK 截图、配置、三点扫描及 CSV 通过，退出码 0。本地交付目录的 ZIP 再次与远端摘要核对一致。
- 关联提交主题：`ci: build private Windows release on GitHub Actions`。
- 关联提交：构建基线 `7b35599`（标签 v0.1.0），发布通道与 CI `2be6649`；最终证据补录提交主题 `docs: verify private v0.1.0 release and teacher handoff`。
- 发布结果：https://github.com/oldcatnine/GaussianLab/releases/tag/v0.1.0 。构建记录：https://github.com/oldcatnine/GaussianLab/actions/runs/43573110436 。用户未授权公开，仓库保持私有，未邀请或联系其他人。
- 本地整理：releases/v0.1.0 中的 ZIP、校验清单和解压程序已统一为 GitHub 下载并复测的版本；早期本机构建 ZIP 移至 outputs/local-build-archive 供追溯。GitHub 运行包 184256791 字节，其摘要见 github-release-v0.1.0.json；原本机构建摘要保留在 release-artifacts-v0.1.0.json，二者不混用。
- 能力与方法补充：官方 GitHub Actions Windows runner、checkout/setup-python、GitHub CLI Release 上传，认证 API 下载、GitHub digest/SHA-256/ZIP CRC 三重核对、冻结程序复测；通过受控 PowerShell 文件操作整理生成物，未改动用户其他目录。
- 下一步：后续功能开发按新版本和 Git commit 推进；其他用户获取私有仓库在线访问权需由用户另行授权，当前可直接转发已整理的 ZIP。

### DEV-009｜2026-11-14｜排查扫描页与扫描数据为空

- 目标：检查用户反馈的两个扫描标签页没有内容。
- 操作与方法：用 computer-use 的 @oai/sky 绑定实际 GaussianLab.exe（与 Python 源码窗口区分），读取空白页面、参数和状态；检查 GUI 的 compute/start_scan/job_done 与图表、数据表填充代码；点击左侧“开始扫描”，再分别检查曲线和数据页。
- 原因：启动与顶部“计算光场”只运行 simulate，扫描曲线和表格仅在单独的 scan 任务成功后生成。原窗口状态显示刚做过末端收敛检查，也不生成扫描数据。V0.1.0 在尚未扫描时缺少说明，数据表连列头都未初始化，导致像功能失效；本次未发现扫描计算或显示链路故障。
- 实际结果：在现有 EXE 运行 L1 焦距 60—180 mm、9 点扫描后，出现扫描完成状态、曲线及 9 行数据；120 mm 行显示最小 r86=52.41 μm、位置=218.75 mm。当前窗口停留在已填充的扫描数据页，未用假数据填充。
- 变更：补充使用说明的空白原因与操作步骤；新增真实按钮→QThread→图表和表格回归测试，以补足旧测试直接注入 job_done 的覆盖局限。没有修改算法、可执行文件或覆盖已发布 V0.1.0 附件。
- 验证：插件已经核对曲线和数据表。新增真实异步测试首次使用 QTest.qWait 循环时工作线程未在 15 秒内完成，39 项通过、该项失败；改为显式处理 Qt 事件并用短 time.sleep 释放 GIL 后，单项 4.54 秒通过。最终完整测试 40 项通过（13.42 秒）、退出码 0，规则脚本与差异检查通过；不把测试驱动的超时当作已复现的 EXE 故障。
- 关联文件：tests/test_gui.py、docs/USER_GUIDE-v0.1.0.md；关联提交主题 `test: verify scan button workflow and document empty scan tabs`。
- 报告素材：交互可发现性、操作流程诊断、真实异步按钮链路测试与测试覆盖改进。
- 下一步：将未扫描状态的引导提示作为后续界面改进项，不把尚未发布的界面修改写成已完成。

### DEV-010｜2026-11-14｜中文说明规范与项目学习手册

- 目标：将项目自有英文批注与说明整理为中文，采用通用应用开发语气；建立适合初学者的整体架构、逐文件用途、原理、操作和技术自测手册，并约束后续维护。
- 操作与变更：翻译 Python 文档字符串与注释、打包配置批注、脚本提示、工作流显示名称、第三方组件中文解释及文档相关表述。保留标识符、文件协议字段、命令、单位、第三方许可证原文、历史原始验证日志和提交主题。扫描导出指标说明改为中文，使用 UTF-8 可读文本；三维叠字保留 r86 和倍率符号，中文解释放在 Qt 提示中，避免依赖 VTK 默认字体的中文字形支持。
- 学习资料：新增《项目学习手册》Markdown 源文件及离线单文件 HTML，24 章、20 个技术自测问答、6 个练习；覆盖单位、高斯与衍射方法、物理假设、采样误差、数据模型、Python 基础写法、真实按钮与线程链路、三维显示、测试、发行、排错和后续扩展。附录覆盖 69 个文件，其中本机已有的 6 个 IDE 配置标为可选文件；虚拟环境、构建及输出目录按类别解释，不将第三方内部文件计入业务源码。
- 工具与方法：使用 PowerShell、Git、Python tokenize/ast 审计注释与文档字符串，结合真实源码逐项核对手册；使用 markdown-it-py 生成目录、表格和离线 HTML，生成依赖记入 requirements-build.txt。沿用 docs/research.md 的既有 GitHub 调研，无新增外部代码复用、安装无关项目或重新搜索。阅读了 documents Skill 的格式工作流说明，本次交付格式为 Markdown/HTML，没有执行 DOCX 生成或声称完成文档分页渲染。
- 规则与检查：agents.md 增加后续中文批注、通用应用语气与手册维护规则；test_text_policy.py 检查自有 Python 解释性文本、文档语气、逐文件清单覆盖、24 章与离线锚点；原有 GUI 测试增加中文提示和扫描指标元数据断言。检查允许技术标识、原始法律文本与历史日志保留原写法，不用简单全局替换破坏协议。
- 问题与处理：初次审计输出遇到终端编码问题，改用 PYTHONIOENCODING=utf-8。新增手册测试先后发现 Fresnel 中英文对应缺失和“局限/限制”措辞断言不一致，修正对应标题与断言。扫描元数据断言发现 JSON 默认将中文转为 Unicode 转义，调整为 ensure_ascii=False，并按 JSON 字段解析验证。此前失败结果不计作通过。
- 验证证据：完整 pytest 44 项通过，15.42 秒，退出码 0，包含真实 Qt/VTK 渲染与异步扫描；Test-Agents.ps1、pip check、git diff --check 通过。手册生成覆盖 69 个文件、93 个导航条目；中文批注、文件用途覆盖及离线导航结构检查通过。Browser Use 工具尝试读取 file:// 手册被浏览器安全策略拒绝，未绕过限制；网页视觉与打印分页尚未由浏览器验证，不能把结构检查写成视觉验收。
- 发行与本机文件：仅将发行目录外置指南改为“使用说明.md”并同步文本；未覆盖已发布 ZIP、EXE、摘要与第三方原始许可证。用户已有暂存的 .idea 文件及其内容保留，不混入本次提交。文档更新不代表已经重新打包程序。
- 关联文件：agents.md、README.md、gaussian_lab、scripts、tests、docs/项目学习手册.md、docs/项目学习手册.html、docs/file-roles.json、docs/file-inventory.json、requirements-build.txt。
- 关联提交主题：`docs: localize project text and add beginner learning handbook`。
- 报告素材：模块职责与调用链、两种传播方法的区别、r86 与 w 的定义、采样与模型边界、真实线程测试、中文文档维护和可追溯的文件用途索引。既有案例数值明确作为历史配置结果引用，不虚构新增实体实验。
- 下一步：后续新增或调整文件时更新用途字典，重新生成手册并运行测试；需要更新可执行程序时另建经过验证的发行版本。

### DEV-011｜2026-11-14｜阶段检查与数值可信度指导

- 目标：从课题完成度、计算可信度、工程质量和结果分析角度检查当前项目，给出有证据的改进顺序。
- 操作与变更：检查 model、optics、gui、charts、scene、测试、发布工作流与文档；新增阶段检查报告，记录焦区采样风险、多指标收敛缺口、独立衍射对照、结果元数据和论文材料建议；同步 README、文件用途清单和学习手册离线版。计算内核、GUI 与发行包保持本次检查基线。
- 工具与方法：实际使用 PowerShell、rg、Git、项目 .venv Python、pytest、NumPy 与现有计算接口；复用 research.md 中同目标的 GitHub 调研，未重新在线核验上游状态，未安装外部光学软件或使用专项 Skill。轻量查询记忆索引未获得与本项目有关的证据，检查结论来自当前工作区。
- 已完成：4 组焦距/轴向采样数值对照；40 mm 焦距下 65/161 点分别得到最小 r86=35.1563/16.5728 μm，统一为 r86 定义后的连续解析参考为 17.7207 μm；独立解析采样对照得到采样最小半径为连续最小半径的 1.9175 倍。所有数值均来自实际执行，详细输入及复现方法见检查报告。
- 测试变更：新增 50%、86%、95% 三组高斯包围能量半径积分对照，直接验证 encircled_radius，允许一个横向网格间距的误差；不将其视作焦区精度或光阑衍射认证。
- 验证证据：检查前完整 pytest 为 44 passed in 15.24s；新增测试后为 47 passed in 15.36s，两次进程退出码均为 0。Test-Agents.ps1 通过，pip check 无依赖冲突；重新生成手册后覆盖 70 个文件、93 个导航条目；最终文档与文字规范检查 11 passed in 0.20s，git diff --check 通过。
- 问题与处理：Qt/VTK 测试仍打印 Windows COM 0x8001010d 诊断，最终断言和进程退出成功，未声称修复环境诊断。临时数值命令中文警告显示编码失真，数值正常，按源码核对警告内容。首次 git add 因沙箱禁止写入 .git/index.lock 失败，使用授权提权调用后成功；后续重建清单以纳入新增报告。用户原有暂存的 .idea 文件保留，不混入本次提交。
- 尚未验证/建议：焦区细化、多指标收敛、外部衍射库对照、峰值内存与跨设备运行均未在本次实现；不把建议写成完成成果。检查报告不替代学校正式评分与任务书验收。
- 关联文件：docs/project-review-2026-11-14.md、docs/development-log.md、docs/file-roles.json、docs/file-inventory.json、docs/项目学习手册.md、docs/项目学习手册.html、README.md、tests/test_optics.py。
- 关联提交主题：`docs: review numerical credibility and graduation project priorities`。
- 报告素材：阶段评价、解析与数值对照表、轴向采样敏感性、指标定义与误差来源、验证边界及需求证据追溯。
- 下一步：优先建立最终需求验收表，并实现焦区细化和分离的横向/轴向/窗口收敛实验。

### DEV-012｜2026-11-14｜焦区细化、多指标收敛与独立数值验证

- 目标：按阶段检查建议落实计算可信度、光斑质量分析、结果追溯、验收矩阵和持续测试，优先解决轴向漏采。
- 操作与变更：新增 0—4 级焦区局部细化，解析位置仅作额外探测；保留最低平台括区、边界警告与细化结果平面。四组分轴收敛记录焦区/末端 r86、位置、θ86、透过率与剖面；新增包围能量图与曲线导出。元数据关联输入、定义、加载时源码摘要与匹配收敛，避免旧检查混入新输入；收敛界面说明主场景保持上次光场。扫描区分警告与失败。预分配强度体并复用半径排序。
- 工具与方法：实际使用 PowerShell、rg、Git、Python/NumPy/SciPy、pytest、Qt/VTK 程序化界面测试、Matplotlib、Windows 进程峰值工作集接口；web 工具复核 LightPipes 原仓库 README、LICENSE 与传播源码，读取随包许可及元数据。未使用专项 Skill 或并行代理，未复制第三方算法源码。
- 独立依赖：沙箱内首次 pip 安装因网络权限失败，经 require_escalated 安装 LightPipes==2.1.5 到本项目 .venv；仅加入可选 requirements-validation.txt。LightPipes 使用卷积传播，本项目采用传递函数，显式统一输入与坐标，并禁用高斯快捷分支。随包完整许可为 BSD-3-Clause，元数据的 MIT 分类标签冲突按完整 LICENSE 解释。
- 已完成的数值证据：横向充分采样的短焦距基准，关闭细化时 r86=59.3217 μm，细化后 17.8206 μm，解析参考 17.7207 μm，差异约 0.5636%。六组独立传播对照最大归一化强度 L1 差异约 0.031814。7 点孔径取舍同时记录加密结果，最小 r86 最大变化约 1.8128%。输入、环境、质量指标与原始结果见 numerical-validation-v2.json，不把本次配置与历史粗网格案例直接混作同配置提升。
- 内存与性能：在独立子进程实际读取 N=256/512/1024、33 点案例峰值工作集；最终数值见 validation-v2.md 与 JSON。没有改动前同条件实测基线，不宣称降低百分比或普适耗时。实际图像 numerical-validation-v2.png 已通过 view_image 检查，中文标签、单位和两组曲线可读。
- 测试与过程证据：内核第一轮 26 项通过；增加针对性测试后 32 项通过；GUI 第一轮 6 项通过；外部对照 3 项通过；新增来源隔离等测试后的组合检查 46 项通过，退出码均为 0。实现最终版本后再运行完整测试与文档检查，第一次完整检查 65 passed in 40.08s，退出码 0；Test-Agents.ps1、pip check、git diff --check 通过，手册覆盖 77 个文件、93 个导航条目。实际生成并查看 outputs/energy-v2-desktop.png，确认新增标签、曲线与控件可读；随后为最小窗口增加可滚动参数区和可达性测试，最终完整检查为 66 passed in 41.27s，退出码 0，包含最小窗口下滚动访问收敛按钮的回归；pip check 与差异空白检查再次通过。
- 问题与处理：沿用原有 COM 0x8001010d 诊断，不关闭 faulthandler 掩盖；检查实际断言与退出码。实现中发现冻结程序可能缺少独立源码，改为摘要未知并增加测试；源码摘要在模块加载时固定，避免后续编辑文件污染已加载算法的追溯。临时控制台中文输出编码失真时依据 UTF-8 归档与图像复核。多轮数值脚本试跑因功能和来源记录完善而重生成，归档保留最终版本。
- 文档与持续测试：同步 README、需求—实现—测试矩阵、既有方案的当前入口、调研及第三方说明、文件用途清单和离线学习手册；新增普通提交的无 GUI CI 与可手动触发 GUI 作业。尚未推送或声称远端执行成功。
- 关联文件：gaussian_lab/model.py、optics.py、gui.py、charts.py；tests/test_optics.py、test_gui.py、test_independent_optics.py、test_project_docs.py；scripts/validate_numerics.py；requirements-validation.txt；.github/workflows/checks.yml；docs/validation-v2.md、numerical-validation-v2.json、numerical-validation-v2.png 及配套文档。
- 关联提交主题：`feat: 完善焦区搜索与多指标数值验证`。
- 报告素材：焦区搜索算法与平台限制、解析误差表、独立算法对照、孔径多指标取舍和加密对照、内存测量口径、可追溯结果与验收矩阵。
- 尚未完成/限制：未重新构建或上传历史 EXE，无实体光学实验、标准 M² 或跨设备保证；局部搜索不保证任意多峰全局连续极值。所有孔径点的独立窗口收敛链仍待扩展，当前没有任意参数精度认证。
- 下一步：按当前边界形成正式结果分析章节；如需交付增强 EXE，应另建版本并执行冻结程序、许可与下载包复测，不覆盖历史证据。

### DEV-013｜2026-11-14｜撤回 CUDA 加速与自动预览试验

- 目标：用户反馈上一需求出现无法解决的问题，要求回退开发版本；停止该方向的后续开发并恢复此前已验证的 4179468。
- 操作与变更：上个需求未形成 Git commit。先保存六个已跟踪文件的差异补丁，再将八个新增源码、测试、依赖与实验文件移入 outputs/rollback-cuda-20261114；随后仅恢复 GaussianLab.spec、charts.py、gui.py、optics.py、scene.py、test_gui.py 的工作区版本。用户原有暂存的六个 .idea 文件及其中工作区修改保持原状，不执行全局 reset 或 clean。
- 环境恢复：核对并卸载仅为该试验新增的 11 个虚拟环境包，包含 CuPy、CUDA Toolkit 元包、pathfinder 和 NVIDIA CUDA 组件；原有 NumPy/SciPy、Qt/VTK、LightPipes 等保留。未修改系统显卡驱动。临时目录内的编译缓存不再由当前项目使用，本次没有跨工作区清理缓存。
- 工具与方法：实际使用 PowerShell、Git、Python pathlib/subprocess/importlib.metadata、pip、pytest；复用已有项目调研，本次没有新增联网调研、专项 Skill 或并行代理。git restore 首次因沙箱禁止写 .git/index.lock 失败，使用 require_escalated 后完成；可选包卸载同样经授权提权执行。
- 试验状态：此前 CUDA 分项一致性测试及部分界面测试曾通过，也有一轮实际性能记录；这些不是最终需求验收。用户未提供具体故障细节，本次不虚构根因、不宣称问题已修复，直接按要求撤回。代码、补丁、包版本与实验数据保存在忽略目录备查，不作为当前功能交付。
- 当前结果：恢复 CPU 手动计算、焦区细化、多指标收敛、包围能量和原有结果导出；当前开发代码不包含 CUDA 与参数自动重算。逐文件比较确认上述六个文件与 4179468 内容一致（允许 Git 行尾转换）。
- 测试变更：文档测试将开发记录连续编号检查扩展到 DEV-013；学习手册同步注明当前基线与回退状态。完整回归为 66 passed in 44.01s，进程退出码 0；pip check 无依赖冲突，Test-Agents.ps1 和 git diff --check 通过。Qt/VTK 仍打印既有 COM 0x8001010d 诊断，未将其隐藏或宣称修复。手册已重建，覆盖 77 个文件、93 个导航条目。
- 关联文件：docs/development-log.md、docs/项目学习手册.md、docs/项目学习手册.html、tests/test_project_docs.py；本机备份 outputs/rollback-cuda-20261114。
- 关联提交主题：`docs: 记录撤回 CUDA 与自动预览试验`。
- 报告素材：未完成需求的撤回、限定文件恢复、环境依赖回退、实验与正式验收的区别，以及版本基线验证方法。
- 下一步：继续使用已验证的 CPU 数值增强版；后续开发按用户重新明确的目标进行。

### DEV-014｜2026-11-14｜白色主题与分析图片导出

- 目标：按新需求将软件改成白色主题，支持光斑、剖面强度曲线、强度曲面及包围能量图片的白底导出。
- 操作与变更：新增 theme.py 管理共享绘图配色与低强度白色色标；窗口、控件、坐标、图例、三维背景与观察面同步改为浅色。右下加入明确的图像类型选择，可导出当前右上分析图或指定光斑、剖面、曲面、包围能量、轴向与扫描六类图；支持未访问过的标签，保持结果和扫描快照口径，补充缺失结果及保存失败提示。
- 格式与显示：PNG 使用 300 dpi，另保留 SVG/PDF；明确白色图纸与不透明输出，紧边界加留白避免标签裁切。剖面、曲面及包围能量标题显示观察面 z，光斑导出沿用对数开关。三维场景截图沿用原入口并采用白底。
- 工具与方法：实际使用 PowerShell、Git、Python、pytest、Qt/VTK 程序化界面测试、Matplotlib 保存、Pillow 像素核验与 view_image。复用 research.md 中已有 Matplotlib/PyVista 选型与源码学习结论，无新增第三方依赖、专项 Skill 或再次联网调研；未恢复此前撤回的 CUDA/自动预览。
- 测试变更：增加六类 PNG 导出检查，验证四角纯白且不透明、当前观察面、旧结果快照、未访问标签导出、SVG/PDF、缺失扫描提示和取消保存。需求检查扩展至 R11，日志编号检查扩展至 DEV-014。
- 已完成的验证：原有 8 项 GUI 测试通过（退出码 0）；加入导出测试后 12 项 GUI 测试通过（26.28s，退出码 0）。真实生成 outputs/white-theme-preview 下四类图片、desktop.png 与 scene.png，已通过 view_image 检查窗口、光斑、剖面、曲面及包围能量的颜色、标签与数据表现。
- 问题与处理：首次导出视觉检查发现部分标题和横轴标注靠近边缘，保存设置补充 bbox_inches 与留白；三维 z 标签额外纳入导出边界，并增加整圈边缘纯白检查，避免只检查四角漏掉标签裁切。修正后重新生成检查。既有 COM 0x8001010d 图形诊断保持单独记录，不以隐藏诊断代替检查退出码。首轮完整验证为 70 passed in 50.78s；补充三维标签边界后最终完整验证为 70 passed in 49.30s，两次退出码均为 0；Test-Agents.ps1、pip check、git diff --check 通过。手册覆盖 78 个文件、94 个导航条目。加留白后已重新导出四类图片并复看剖面、包围能量及曲面图；像素边界检查确认四类图的所有内容均位于留白之内，三维 z 轴标签完整。
- 关联文件：gaussian_lab/theme.py、charts.py、scene.py、gui.py、tests/test_gui.py、tests/test_project_docs.py、README.md、docs/requirements.md、docs/项目学习手册.md、docs/项目学习手册.html、docs/file-roles.json、docs/file-inventory.json、docs/development-log.md。
- 关联提交主题：`feat: 添加白色主题与分析图像导出`。
- 报告素材：需求 R11、显示层与计算层分离、可选图像导出、白底与透明度验证、当前观察面和结果快照一致性。
- 限制：没有更改光学算法或新增实体实验；导出分辨率不代表计算网格精度。历史发行 EXE 尚未重新构建，当前打开的旧窗口需重新启动源码版才能加载新界面。
- 下一步：使用源码启动器运行白色主题，在指定观察面选择所需图像类型并导出。

### DEV-015｜2026-11-14｜教学手册与相关文档同步

- 目标：按白色主题与图像导出功能基线 853e9b3 同步教学资料，明确当前源码与历史发行版的区别。
- 操作与变更：新增当前源码使用说明 USER_GUIDE.md，补齐版本识别、手动计算、3D 缩放、七种导出选择（当前标签加六类图）、格式与 dpi、观察面、扫描及 CSV 快照口径；教学手册修正首页基线，增加操作练习、当前界面截图、Result 新字段和取消/验证说明。同步 README、需求矩阵、产品设计与方案、数值验证的阅读提示及旧版指南入口。
- 历史与当前：保留旧发行包、原始数值表、旧测试数量、发布记录和历史日志；早期“尚未实现”“深色建议”标明设计背景，当前白色界面与实际能力单独说明。CUDA/自动预览仍为已撤回状态，未新增运行功能或改动计算内核。
- 工具与方法：实际使用 PowerShell、rg、Git、Python pathlib/shutil/json、现有 build_handbook.py 与 pytest；基于当前源码、853e9b3 的真实截图和已有验证记录核对，不新增联网调研、专项 Skill、外部依赖或实验数据。
- 教学截图：复制上一阶段实际生成的白色界面截图到 docs/assets/white-theme-desktop.png，并在 Markdown 教学手册和当前使用说明引用；离线 HTML 由构建脚本嵌入截图，保留单文件阅读能力。截图用于解释该功能基线，不宣称本次新运行了一组光学实验或完成浏览器打印分页验收。
- 测试变更：文档检查扩展到 DEV-015，并核对当前指南与源码的导出选择、功能基线、格式/CPU/快照说明、相关本地链接和离线截图嵌入。文档专项 13 项通过；完整回归 71 passed in 53.18s，进程退出码 0；Test-Agents.ps1、pip check、git diff --check 通过。手册重建覆盖 80 个文件、95 个导航条目，截图已嵌入 HTML。既有 COM 0x8001010d 诊断仍按原状记录，未宣称修复；本次未进行浏览器打印分页验收。
- 问题与处理：发现手册首页仍把 4179468 写作当前界面基线、四类分析标签和导出操作未在入门章节完整介绍、设计文档有历史“尚未实现/深色”描述；分别修正为当前状态、历史说明与可追溯链接。旧指南继续服务 V0.1.0，不直接替换旧 EXE 的操作说明。
- 关联文件：README.md、docs/USER_GUIDE.md、docs/USER_GUIDE-v0.1.0.md、docs/项目学习手册.md、docs/项目学习手册.html、docs/assets/white-theme-desktop.png、docs/requirements.md、docs/product-design.md、docs/product-plan.md、docs/validation-v2.md、docs/file-roles.json、docs/file-inventory.json、tests/test_project_docs.py、docs/development-log.md。
- 关联提交主题：`docs: 同步白色主题教学手册与当前操作指南`。
- 报告素材：功能与文档基线管理、当前/历史版本区分、操作与数据口径、源码到教学资料的交叉核对、离线阅读资源嵌入。
- 下一步：按当前源码指南开展操作和图片导出；新的代码与界面变更继续同步手册和用途清单。

### DEV-016｜2026-11-14｜V2.0.0 便携版本迭代与构建

- 目标：将白色主题、分析图导出和 CPU 数值增强整理为其他 Windows x64 电脑无需 Python 即可运行的 V2.0.0，保留历史版本。
- 操作与变更：包版本、窗口标题、冻结自测与 Windows EXE 文件资源统一为 2.0.0；分版本输出至 dist/v2.0.0、build/v2.0.0、releases/v2.0.0。构建整理脚本按包版本生成运行包、Qt 对应源码、应用源码与摘要清单，附当前指南、离线手册、示例和原始许可。应用源码过滤虚拟环境、IDE、输出与生成目录。
- 工具与方法：实际使用 PowerShell、Git、Python、PyInstaller 6.22.3、pytest、Qt/VTK、ZIP/CRC 与 SHA-256；读取 PyInstaller 原仓库与官方使用说明、Qt 6.12 Windows 支持说明，复用已有打包方案，不安装无关项目或改动系统驱动。Qt 源码固定摘要从前次验证清单继承，可复用旧缓存并重新校验，不将旧版本附件改名充作新程序。
- 版本与许可：新增 Windows 中文版本资源与固定 Qt 源码摘要清单；保持动态库目录和完整版权/许可，应用源码单独作为同版本附件提供。本次没有选择新的开源许可证，没有上传 GitHub Release；发布脚本与手动工作流更新默认版本，尚未执行远端发布。
- 实际构建：首次 PyInstaller 完成约 141.4s，EXE FileVersion/ProductVersion 为 2.0.0；隔离路径冻结测试完成三个光学案例和三维渲染，但实际 SVG 导出失败，缺少 matplotlib.backends.backend_svg。补齐 SVG/PDF 后端后重新构建约 135.8s；第二次直接构建目录的冻结程序自测通过，包含三个案例、配置、三点扫描、六类 PNG、SVG/PDF、白底和窗口版本，退出码 0。
- 验证口径：冻结程序自测使用 PATH 仅含 Windows 系统目录，移除 Python/虚拟环境/Qt 开发路径，并从独立目录启动；窗口程序自测失败时写日志退出，避免弹窗阻塞自动验证。低网格扫描的 warning 状态按实际保留，不当作 error 或伪装为 ok。直接构建版通过不替代最终 ZIP 的解压复测。
- 测试变更：增加版本资源与 SVG/PDF 后端一致性、Qt 来源/摘要清单检查、发行附件被篡改时拒绝解压，以及无 .git 的源码解压目录按文件清单重新整理附件的测试；发布规则专项最终 9 项通过（0.65s）。完整项目测试 `python -m pytest tests -q` 为 75 passed in 50.70s，退出码 0；Test-Agents.ps1、pip check 与差异空白检查通过。手册覆盖 87 个文件、95 个导航条目。
- 最终附件验证：三个 ZIP 的 SHA-256/CRC 通过，运行包独立解压至 outputs/portable-v2.0.0-final 后，隔离路径冻结自测通过、退出码 0；三个案例、配置往返、三点扫描、六类白底 PNG 及 SVG/PDF 均完成。EXE 摘要为 d2acb4610616c5888724e14681ffc351867e600386a8ffcf435e0cd809001c82，运行 ZIP 为 188667175 字节。view_image 复看 desktop-v2.png，白色界面、三维光路和曲线可读；摘要与实际输出见两个同版本 JSON 报告。源码附件最后单独刷新，不改变已验证的运行包。
- 问题与处理：直接在根目录运行未限定范围的 pytest 会误收集 outputs/rollback-cuda-20261114 的历史备份测试，因已撤回模块不存在而收集失败；改为对当前项目 tests 目录运行完整测试，不删除回退证据。Qt/VTK 测试仍输出已知 Windows COM 0x8001010d 诊断，实际断言与退出码成功，未声称修复底层环境问题。用户原有 .idea 暂存内容保持原状，不混入本次提交。
- 关联文件：gaussian_lab/__init__.py、gui.py、release_smoke.py、app_entry.py、GaussianLab.spec、packaging、scripts/build_release.ps1、prepare_release.py、verify_release.py、publish_github.py、verify_published_release.py、.github/workflows/release.yml、tests/test_release.py、tests/test_project_docs.py、README.md、docs 当前指南/学习手册/依赖说明与 V2.0.0 发布文件。
- 关联提交主题：`release: 构建 GaussianLab V2.0.0 便携版`。
- 报告素材：版本元数据一致性、源码环境与冻结环境差异、真实导出后端漏包的发现修复、对应源码与许可、隔离运行和摘要/CRC 校验。
- 限制：目标为 Windows 10/11 x64，实际仍为本机 Windows 11，未宣称所有其他实体电脑、显卡或 ARM/macOS/Linux 可运行；未进行商业代码签名。CUDA 与参数自动预览维持撤回状态。
- 下一步：保留本机 V2.0.0 发行附件与同版本源码，按接收设备实际环境反馈兼容情况；跨实体电脑验证和远端发布尚未执行。

### DEV-017｜2026-11-14｜独立 CUDA 分支与交互响应优化

- 目标：针对分发测试的卡顿反馈，在 V2.0.0 基线上创建 feature/cuda-responsive-preview，重点支持用户确认的 NVIDIA 独显电脑，同时保留 CPU 兼容路径；稳定运行附件不覆盖。
- 操作与变更：新增惰性 CuPy 后端、设备/FFT 自检、不可用及执行故障的 CPU 回退、固定版本的独立可选运行库；复用光学区段起点频谱，焦区细化不再从入口反复传播。默认停止输入 400 ms 后预览，最多 256/33/0 采样；数值框启用键盘跟踪并以真实 QTest 输入覆盖，无需额外回车，表格在提交单元格编辑后更新。完整计算保留原始配置。单任务排队、取消过期任务、修订号过滤迟到结果，128 MiB 结果缓存按配置/后端/质量隔离；Git 状态首次捕获并保留时间。图形合并滑块更新、复用轴向游标和光路外形、批量渲染、相机保持；独立导出画布与预览标签防止自动更新混淆快照。
- 工具与方法：实际使用 Git 分支、PowerShell、Python、pytest、NumPy/SciPy、CuPy/cuFFT、NVIDIA-SMI、Qt/VTK、perf_counter、JSON 归档与窗口截图。先搜索并读取 CuPy 原始仓库、发布、FFT 源码和官方安装说明；MIT 许可与可选依赖说明同步文档。未使用额外 Skill、子代理或远端发布；不复制第三方光学算法。
- 环境与依赖：本机 RTX 4060 Laptop GPU 8 GiB、驱动 617.14；CuPy 14.2.0 与 CUDA 12.9 固定轮子装入 LOCALAPPDATA/GaussianLab/cuda-v2-dev，不改 .venv 基础库或系统驱动。首次仅加入 sys.path 时 NVIDIA 查找器找不到头文件/库，注册标准 site.PREFIXES 后实际 CUDA 通过；未重用前次修改第三方编译器的中文路径兼容层。沙箱的 LOCALAPPDATA 重定向与默认 CuPy 缓存权限曾导致检测失败，显式运行库路径与临时编译缓存后恢复；这些失败均按 CPU 回退处理。
- 验证证据：原有数值测试 38 项通过（13.39s）、初始 GUI 12 项通过（26.54s）；新增回退/一致性测试初轮 10 项通过（14.61s），三种案例实际 used=cuda；新增交互回归后 18 项 GUI 通过（37.09s）。全量初次 93 passed in 55.46s；完善真实键盘输入回归后的最终全量为 93 passed in 55.11s、退出码 0；禁用 CUDA 的加速与 GUI 专项为 27 passed、3 skipped in 37.00s、退出码 0，跳过的是三项真实设备对照，不伪称无设备执行 CUDA。后者也覆盖了选文件路径期间到达新结果而导出仍保持旧预览快照的回归。规则脚本、pip check、PowerShell 安装脚本语法及差异检查通过；手册覆盖 98 个文件、95 个导航条目。实际计时脚本从 v2.0.0 标签加载旧内核，预热后各三次；512/65 三案例旧版中位数 2.291/2.549/2.453 s，优化 CPU 为 1.161/1.177/1.196 s，CUDA 为 0.151/0.157/0.152 s；1024/33 光阑案例为 7.706/3.330/0.283 s。自动预览内核为 0.106—0.123 s。强度最大绝对差不超过 1.46e-11、r86 差为 0；数据、配置和源码摘要见 acceleration-validation.json，不外推跨机性能。
- 真实交互：最终脚本在真实 CUDA Qt/VTK 窗口退出码 0，连续改参最终快照正确、完整计算使用 512/65/2、同参数命中缓存；首次预览约 2.380 s、后续约 0.659 s、完整显示约 0.995 s、缓存约 0.014 s；最大心跳间隔约 0.870 s。过程日志 outputs/cuda-interaction-verified.log，记录与截图见 interaction-validation.json 和 assets/cuda-preview-desktop.png；首轮编译曾使首次预览达 9.77 s，不承诺首次即时完成。
- 问题与处理：验证脚本用 .77*1e-3 与 .00077 精确相等导致等待超时，改为容差判断，未归因为应用死锁。一次真实窗口断言成功后退出码 -1073740791，不能算通过；补齐 deleteLater、DeferredDelete 与 gc 清理后重跑退出码 0。新增相机回归最初把 CameraPosition 当成 NumPy 数组导致类型错误，改为比较显式数值列表后通过；不归因为相机丢失。CuPy 仍打印未发现系统 CUDA_PATH 的提示，但独立轮子实际自检及 CUDA 计算成功；不隐藏提示。沿用已知 Qt/VTK COM 诊断，按断言和进程退出码验收。view_image 已检查最终截图的白色界面、后端/预览控件、实际 CUDA 标签、光路及曲线可读。稳定运行 ZIP 摘要仍为 37b423995164935f06abb1157de5c9cfcd5a25b5d80ea64f3fcdb45a8889baa4；用户 .idea 暂存内容不混入分支提交。
- 关联文件：backend.py、session.py、optics.py、gui.py、charts.py、scene.py、requirements-cuda.txt、安装与两项验证脚本、tests/test_acceleration.py、tests/test_gui.py、当前指南/学习手册/需求/研究/第三方说明、acceleration.md 与实际 JSON/截图。
- 关联提交主题：`feat: 开发可选 CUDA 加速与响应式预览`。
- 报告素材：CPU/GPU 同精度对照、区段频谱复用、设备故障回退、预览/完整质量区别、端到端与内核计时区别、任务取消和过期结果隔离、界面绘制剩余瓶颈及失败复核证据。
- 下一步：接收其他 NVIDIA 设备与 CPU 实体机反馈，再独立制作并验证开发版分发包；本次未替换或发布稳定版 EXE，未宣称所有操作无卡顿或全场景实时。

### DEV-018｜2026-11-14｜V3.0.0 便携打包与私有发布

- 目标：用户接受 CUDA/交互开发成果并授权作为 V3.0.0 打包发布；保持既有私有仓库和历史版本。
- 操作与变更：版本、窗口、Windows 文件资源统一 3.0.0；从固定轮子整理约 719 MB 应用私有 CuPy/CUDA 组件，随包原始许可和逐文件摘要。中文路径下复制到英文私有缓存并核验；首次 CUDA 从固定官方 PyPI 轮子补齐约 3.6 MB 编译头文件，下载大小/SHA-256 校验后限定目录提取，失败回退 CPU。更新指南、手册、发布说明、构建脚本和冻结双后端验证；不覆盖 V2.0.0。
- 工具与方法：实际使用 Git、PowerShell、Python、PyInstaller、AST 标准库导入分析、实际 CUDA 运行模块清单、pytest、Qt/VTK、SHA-256/ZIP CRC；复用前次 CuPy/PyInstaller GitHub 原仓库结论，补读 CUDA 12.9 官方 EULA 与 CuPy 安装说明。GitHub 插件不支持附件上传，沿用项目已有官方 API 发布脚本；只读查询已确认仓库 private=true、默认 master、未归档，仅有历史 v0.1.0 远端发行。未使用额外 Skill 或子代理。
- 实际发现：直接复制至沙箱长临时目录出现 WinError 206，缩短缓存临时名并在正常 Windows 临时目录验证；只保留再分发清单头文件时 CuPy 无法定位 cudart，不能算 CUDA 通过，改为本机首次官方轮子补齐。精简运行组件在源码环境下实际 CUDA 光阑计算通过。首轮 EXE 约 85.8s 构建完成，但冻结 CuPy 导入缺 graphlib；第二轮约 84.4s 的 AST 分析仍漏掉 Cython 扩展中的动态导入，实际冻结检查仍失败。记录 543 个实际加载的标准库/NumPy/SciPy 模块，并显式加入 graphlib 后继续构建；不把 CPU 回退当作 CUDA 通过。
- 测试变更：增加运行库缓存内容校验/复用、损坏运行组件拒绝使用、官方头文件下载摘要不符不提取测试；初轮发布/加速专项 19 passed、3 skipped，缺省沙箱路径未加载可选 CUDA，因此三项设备对照未执行。冻结验证扩展实际 CPU/CUDA 案例及自动预览，移除开发 CUDA/Python 路径；源码完整回归、最终附件与远端回下载证据完成后补记。
- 关联文件：版本资源、backend.py、gui.py、release_smoke.py、GaussianLab.spec、packaging/cuda-headers-wheel.json、cuda-hiddenimports.json、stage_cuda_runtime.py、构建/整理/发布/验证脚本、V3 指南/版本说明/验证报告及文件清单。
- 关联提交主题：`release: 构建并发布 GaussianLab V3.0.0`。
- 报告素材：源码与冻结动态导入差异、官方运行组件来源与摘要、首次初始化和缓存、实际后端验证、同版本源码/许可、私有发布与回下载验收。
- 本机最终证据：第三轮约 83.7s 构建成功，Windows 版本属性 3.0.0；完整源码 95 passed in 56.07s、退出码 0，规则脚本、pip check、PowerShell 语法与差异检查通过。PyInstaller 对 typing.io/re 旧别名的非阻塞日志保留，实际冻结导入通过。最终运行 ZIP 为 601057166 字节，SHA-256 7e8ec617c0d85a538a0153740840906a1bad87de515b74e32c5b607e5ff729a0，EXE 摘要 d5e97c300a19a9fc6d8191e880a30edbf643a2e93b771154ca2174b56cd228d9；独立解压的 CPU 和实际 CUDA 均退出码 0，三个案例、扫描、配置、PNG/SVG/PDF、三维渲染与自动预览均通过。全新 CUDA 缓存完成首次官方头文件摘要校验；对应 JSON 已归档，view_image 检查冻结窗口白色界面和曲线可读。最终源码附件单独刷新，不改写已验证的运行 ZIP。
- 下一步：提交并发布至既有私有仓库，回下载核对远端摘要和双后端冻结运行；其他实体电脑验证不在本机结果中冒充完成。

### DEV-019｜2026-11-15｜V3 远端构建上传通道

- 目标：绕开本机代理的大文件上传瓶颈，在保持私有草稿的条件下完成 V3 分发，再回下载双后端验证后正式发布。
- 操作与变更：发布基线 b4806c3 已提交、快进 master 并推送；v3.0.0 与历史基线 v2.0.0 标签、CUDA 分支一并保留。上传主包长时间低速，仅发送到 16 MiB；较小源码请求也发生写入超时。原生 curl 经 ASCII 相对路径修正后成功上传源码附件，摘要与本机一致，但不把它当作主包上传完成。读取历史 DEV-008 发现相同代理瓶颈已使用 Actions 解决，改为复用该路线。
- 工具与方法：实际使用官方 GitHub API、Git、PowerShell、requests、curl；curl 凭据只经进程输入管道传递，不写文件或命令行。核对命令行后停止本任务自己的低速上传进程，保留私有草稿；不更改系统代理。更新 Actions 为构建和上传后保持草稿，不在无 GPU runner 上声称通过 CUDA；下载验证增加明确的 allow-draft 选项，在本机执行真实 CPU/CUDA 后才发布。
- 验证证据：调整后的发行/文档/文字专项 25 passed in 1.37s、退出码 0。主程序和 v3.0.0 标签代码不改写；新增工作流保护测试检查远端上传不自动解除草稿。后续记录 Actions、远端附件摘要、下载验证和正式发布结果；尚未完成项不记为已发布。
- 问题与处理：首次 curl 配置的 Unicode 转义路径无法打开，改为 ASCII 相对路径后返回 HTTP 201；未输出凭据。仅在确认草稿和摘要后清理本次测试上传的草稿附件，避免与远端完整附件集合冲突；历史发行不操作。
- 关联文件：.github/workflows/release.yml、scripts/verify_published_release.py、tests/test_release.py、docs/development-log.md、V3 验证记录。
- 关联提交主题：`ci: 通过远端构建上传 V3 私有草稿`。
- 报告素材：网络通道瓶颈、草稿与发布分离、远端构建和本机 GPU 验收、附件摘要与跨构建产物区别。
- 下一步：触发 V3 远端构建，回下载并验证全部附件与真实双后端，最后发布草稿。

#### DEV-019 远端构建补记

Actions 43613467773 的基础环境和 58 项发行/计算检查通过，安装可选 CUDA 时 pip 23.0.1 按 Windows runner 的 cp1252 解码中文 requirements 注释失败，未进入 EXE 构建和上传。工作流显式设置 PYTHONUTF8=1 与 PYTHONIOENCODING=utf-8，保持 v3.0.0 主程序标签不变；实际失败日志归档 outputs/remote-v3-build-43613467773.log，继续重跑。补充工作流回归要求 UTF-8 模式，避免将本机中文区域设置当作其他机器的默认环境。

修复后的 Actions 43613876322 已 success，四个附件上传至草稿。顺序回下载同样受本机代理低速影响；确认服务端支持精确 HTTP 206 后，使用 outputs/download_v3_parallel.py 临时诊断脚本先 16 路、后 32 路分段读取，签名链接仅保存在内存，每段检查 Content-Range/长度，组装后必须匹配完整 SHA-256 才接受。保留已完成及部分文件，不重下已核对的源码附件；认证下载工具增加 outputs 内指定目录复用，且同时匹配大小与服务器 digest 才跳过网络。补充损坏等长文件必须重新下载的测试，不将并行连接数当作实验加速比。

#### DEV-019 正式交付结果

- 已完成：Actions 43613876322 远端构建成功；回下载三 ZIP 与 SHA256SUMS.txt 后，服务器 digest/SHA-256/ZIP CRC 全部通过。顺序解压布局预计最长 279 字符，调整为短 outputs/gh3-* 路径避免 Windows 长路径问题。下载版 EXE 的 CPU 与真实 CUDA 均退出码 0，覆盖三个光学案例、自动预览、三维渲染、配置、扫描和六类 PNG/SVG/PDF；CUDA 全新缓存首次官方头文件核验为 true，报告见 github-release-v3.0.0.json、github-release-smoke-v3.0.0.json。
- 正式发布：仅在上述验证通过后 PATCH 草稿为 false，实际仓库 private=true、draft=false；发行页 https://github.com/oldcatnine/GaussianLab/releases/tag/v3.0.0 。应用基线 b4806c3/v3.0.0 不改写，工作流修复另有提交 dc61261、82fdf04。
- 最终附件：运行 ZIP 600938694 字节，SHA-256 29a2ae19b9987915cf3da3304c9d5f22c30946514421eb5bee3545afdc68f321；EXE SHA-256 9fbcb2663cb4f90129fdb23facfa2a6031ce68fe0e33bde2d4692d8673c29f04。releases/v3.0.0 已同步为远端下载并验证的版本，本机构建原包经绝对路径核对后移动到 outputs/local-build-v3.0.0；本机历史报告仍保留原摘要，不混同远端文件。V2.0.0 原始 ZIP 摘要未变。
- 最终测试：完整 tests 为 98 passed in 47.87s、退出码 0；新增发布证据检查要求实际 CPU/CUDA、首次下载和服务器摘要，规则脚本、pip check、差异检查通过。已知 CuPy CUDA_PATH 提示保持原样，实际显卡计算通过；未隐藏既有 Qt COM 诊断。学习手册/离线版覆盖 108 个文件、95 个导航条目，更新草稿验收流程、UTF-8 源码构建前提与两类构建证据区别。
- 关联提交主题：`docs: 核验 V3 私有发行与双后端回下载`。下一步为其他实体设备试用与兼容反馈；本次未改变仓库可见性、邀请或联系他人，也未保证全部显卡/驱动组合可用。

### DEV-020｜2026-11-15｜V3 发布后文档一致性整理

- 目标：根据用户要求同步相关文档，消除 V3 已发布后仍指向开发版、旧便携版或首轮未实现状态的表述。
- 操作与变更：统一 README、当前指南、CUDA 说明、第三方依赖、需求补充、设计/调研入口和学习手册；区分便携首次初始化与源码安装、预览与完整计算、开发阶段性能与正式发行证据。更新 V3 发布说明的实际验证状态；数值增强旧报告只补阅读提示，旧版指南、原始 JSON、摘要和实验数据保持原版本口径。已发布 ZIP 作为构建快照，最新 Markdown/离线 HTML 在仓库维护。
- 工具与方法：实际使用 rg、PowerShell、Git、Python、pytest、build_handbook.py，以及工作区代码和既有发布 JSON 对照；复用既有 GitHub 调研结论，没有新联网调研、依赖安装或 Skill 执行。项目记忆仅用于定位手册维护惯例，版本和工作区状态重新读取文件确认。
- 验证证据：新增当前文档与 V3 发布记录、预览配置的一致性回归；相关文档/文字/发布检查 28 passed in 1.32s，最终完整 tests 为 99 passed in 55.17s、退出码 0，包含实际 CUDA 对照。项目规则与差异空白检查通过，离线手册覆盖 108 个文件、95 个导航条目。CuPy 的 CUDA_PATH 提示保留，实际设备检查通过；此次 99 项为真实重跑结果，不沿用既有 98 项交付数量。
- 问题与处理：全文检索发现旧“稳定包仍走 CPU”“使用 V2.0.0”及日志总览 V0.1 等误导现状的文字，按当前源码和既有发行证据修正；早期讨论和失败过程明确标为历史。补丁有两次因上下文不完整未应用，读取完整行后重新应用，无部分内容误提交。首轮检查发现两个历史追溯断言缺少“未实测”和 V0.1.0 入口，补回准确的首轮限制与旧版指南链接后通过，不放宽测试来删除历史依据。用户原有 .idea 暂存内容独立保留。
- 关联文件：README.md、USER_GUIDE.md、acceleration.md、third-party.md、requirements.md、product-design.md、research.md、validation-v2.md、release-notes-v3.0.0.md、项目学习手册及生成文件、file-roles.json、tests/test_project_docs.py。
- 关联提交主题：`docs: 统一 V3 发布后的操作与教学文档`。
- 报告素材：需求—实现—证据映射、不同阶段验证口径、预览/正式结果边界与发布文档维护。
- 下一步：按实际设备反馈补充兼容记录；新增实验或新版发行另建证据，不覆盖原始归档。

### DEV-021｜2026-11-18｜下一版本升级调研

- 目标与方法：通过网页检索上游 GitHub 说明及发行记录，与 README 和现有研究对照。
- 结果与问题处理：将透镜口径、方案对比、纵剖面及算法复核按优先级记录于 [升级意见](research.md)。上游功能说明仅作设计参考，跨设备性能待测。
- 验证方法：更新开发日志连续编号检查，运行项目文档测试与差异检查。报告素材包括工程取舍和可复现实验设计。
- 关联提交主题：`docs: 记录下一版本光路对比与升级建议`。下一步由用户确定开发范围。

### DEV-022｜2026-11-18｜V3.1 实验对比与界面更新

- 目标。按 DEV-021 把有效口径、A/B 分析与纵向剖面连成可操作流程。沿用该轮 GitHub 调研。
- 变更。透镜可选有效通光直径，圆孔与薄透镜共用现有标量传播。A/B 用实际共用采样面或各自最小光斑面，采用单位入射功率的共同强度标尺。纵图从已算剖面生成并联动观察屏。更新白色导航、控件和可拖动分析布局。
- 工具与方法。使用 PowerShell、Git、pytest、Qt/VTK 和手册生成脚本。本轮首轮功能验证 59 通过、1 失败。界面测试错误地将任务对象释放当作完成信号，已改为检测计算按钮恢复与新结果。
- 问题与处理。旧 JSON 缺省无限口径。共面比较使用离观察屏最近的共用采样面，图上标明实际位置。算法对照及多设备延迟待测。
- 关联文件。model.py、optics.py、gui.py、charts.py、版本资源、操作指南与回归测试。
- 关联提交主题。`feat: 添加 V3.1 光路实验对比与现代界面`。
- 报告素材。有限口径与同面圆孔的数值等效、固定观察面和最小光斑面的比较、入射功率基准、纵图定位工作流。
- 最终验证。全量 pytest 为 102 passed in 67.78s、退出码 0，含实际 CUDA 数值对照。发布摘要测试曾因夹具硬编码 V3.0.0 而提前拒绝文件名，改用当前版本再验证篡改检测。项目规则和差异检查通过。实窗截图保存为 outputs/v31-comparison-ui.png。截图检查后缩短侧栏表头并修复强度单位字体缺字。
- 本机响应测量。RTX 4060 Laptop GPU、驱动 617.14，同机 V3.0.0 标签与 V3.1.0，单透镜快速预览 N=256、33 点，6 次连续改参后从最后一次输入测到结果就绪，含 400 ms 防抖，每后端 3 轮。CPU 中位数 0.545→0.544 s，CUDA 0.649→0.668 s。V3.1 单轮最大 GUI 定时器间隔为 CPU 0.171 s、CUDA 0.153 s。重复次数有限，首次初始化未隔离编译缓存，实测只用于核对当前场景的交互量级。脚本及三轮原始值保存在 outputs/v31-benchmark.py、outputs/v31-benchmark.jsonl。
- 下一步。实测跨设备改参延迟并复核采样警告案例。

### DEV-023｜2026-11-18 至 2026-11-19｜V3.1.0 Windows 便携构建

- 目标与结果。以 e9c60ee 为应用基线构建本地 Windows x64 便携包，文件资源版本为 3.1.0。运行 ZIP 为 601077275 字节。未上传 GitHub。
- 工具与方法。PowerShell 驱动 PyInstaller，使用已锁定 CUDA 组件和通过固定 SHA-256 的 Qt 源码缓存。用 verify_release.py 核验三个附件的 SHA-256 与 ZIP CRC、解压关键文件并在隔离开发环境的条件下运行。
- 问题与处理。首轮 CUDA 验证因沙箱临时路径过长使运行组件复制失败。改用标准 Windows 临时目录后，第一次官方头文件下载发生 TLS 中断。确认服务可访问后重试，完成全新缓存的头文件下载与摘要验证。
- 验证证据。CPU 和真实 CUDA 冻结冒烟均退出码 0，覆盖三个计算案例、预览、三维渲染及已有分析图导出。V3.1 新增功能的专项测试见 DEV-022。附件与运行记录见 release-artifacts-v3.1.0.json 和 release-smoke-v3.1.0.json。完整运行包是构建时的文档快照。
- 关联文件。V3.1.0 操作指南、版本说明、便携证据、发布测试及学习手册。文档、文字与发行专项测试 29 项通过，规则脚本及差异检查通过。离线手册覆盖 112 个文件。
- 关联提交主题。`docs: 记录 V3.1.0 本地便携包验收`。
- 报告素材与下一步。记录冻结程序的首次依赖初始化、回退诊断与完整性校验。其他实体机器仍待试用。

## 5. 毕业设计报告素材映射

| 报告部分 | 当前已有素材 | 后续需补证据 |
| --- | --- | --- |
| 绪论与需求分析 | 课题、目标、R01—R10 与范围边界 | 最终需求基线、使用场景确认 |
| 相关技术与方案比较 | 开源仓库、许可、ABCD 与衍射路线 | 正式文献、原始论文、引用日期与学术引用格式 |
| 理论基础 | q 参数、光阑、包围能量与发散角定义 | 推导、符号统一、公式来源核对 |
| 总体与详细设计 | V1.0、模块、交互、数据、3D 方案 | 最终类/模块图、接口与配置 schema |
| 系统实现 | V0.1 源码、依赖快照、GUI/线程流程、实际截图与学习手册 | 新功能实现证据、进一步的接口与类关系整理 |
| 测试与结果分析 | 解析对照、数值案例、GUI 与扫描回归、独立发行复测、文档检查 | 全面收敛、性能基准、实体实验与跨设备验证 |
| 总结与展望 | 当前已记录的范围与风险 | 完成情况、实际不足与有依据的改进方向 |

AI 工具辅助的调研、设计整理、代码与文档生成应如实记录；论文署名、辅助工具披露和引用方式遵循学校要求。本记录不替代实验数据、正式文献或用户独立理解。

## 6. 后续记录模板

新增条目使用递增 DEV 编号，填写以下字段；不适用项写明原因。

```text
### DEV-NNN｜YYYY-MM-DD｜工作主题
- 目标：
- 操作与变更：
- 工具与方法：（工具/Skill 名称、实际作用、是否安装或运行）
- 结果：（已完成/建议/失败/待验证）
- 验证证据：（命令、环境、结果、数据或截图路径；失败也要记录）
- 问题与处理：（原因、方案和剩余限制）
- 关联文件：
- 关联提交：（当前提交写唯一主题，已有提交写哈希）
- 报告素材：（适用章节、可引用结论和证据位置）
- 下一步：
```

数值实验额外记录波长、初始束腰、光路、单位、网格、窗口、算法版本、评价指标和误差；性能测试额外记录 CPU/GPU、系统、依赖版本、场景规模和耗时口径。
