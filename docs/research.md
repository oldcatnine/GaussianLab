# 开源与 Skill 调研

调研日期：2026-11-14。方法：GitHub 连接器检索与获取原仓库、文件、Releases；网页检索原仓库和官方文档。未运行第三方代码、未安装软件，兼容性与数值正确性均未实测。

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

- 建议自主编写规模较小、可解释的 ABCD 解析核心，使用外部库作为独立对照；衍射部分优先评估 LightPipes，评估后决定依赖还是自主实现。
- 本轮仅记录知识与来源，未复制第三方实现代码。以后复制或修改代码时保留对应版权、许可证与必要 NOTICE；依赖发布另核对分发义务。
- 拟采用 Python 3.12 环境进行依赖验证；本机 `python --version` 为 3.15.2，不能由此推定科学计算和 Qt 依赖可用，尚未创建环境。
- 开发前选定上游发布版本或 commit，完成 Windows 安装、无光阑基准、焦区精度、GUI 嵌入与打包冒烟测试。未通过前不把候选写成已选定依赖。
