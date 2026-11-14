# V3.0.0 构建与发布验证

目标：将 a2a7363 的 CUDA/响应式预览分支整理为正式 V3.0.0。关联提交主题：`release: 构建并发布 GaussianLab V3.0.0`。

版本号、窗口标题及 Windows FileVersion/ProductVersion 统一为 3.0.0。运行包包含目录式 EXE、固定 CuPy/CUDA 运行组件、原始许可、指南、离线手册和示例；保留 V2.0.0 不覆盖。

调研沿用 CuPy/PyInstaller 原仓库及现有管线，补读 CUDA 12.9 EULA 的可再分发清单；仅随包提供应用需要的运行 DLL 和清单内头文件。CuPy 需要完整 cudart 编译头文件才能定位运行库，首次 CUDA 从官方 PyPI 固定轮子补齐，验证完整下载摘要，不分发自行改写的第三方头文件或替换编译器内部函数。没有 Python 安装要求，但首次 CUDA 需要联网。

初次中文路径暂存测试遇到沙箱临时路径过长；缩短缓存临时名，并在正常桌面环境验证。精简库初试只含再分发头文件，实际自检未通过，未算作 CUDA 成功；补充固定官方轮子后，在未使用开发环境全部 CUDA 数学库的条件下实际 CUDA 光阑计算通过。

冻结验证将从独立解压副本启动，PATH 仅含 Windows 系统目录，移除 Python/虚拟环境/开发 CUDA 路径。分别执行实际 CUDA 和禁用 CUDA 的 CPU 检查，要求每个案例及自动预览的实际后端匹配请求，防止把 CPU 回退当作 CUDA 通过；覆盖三个光学案例、三维渲染、项目往返、扫描、六类 PNG 及 SVG/PDF。

最终源码测试、EXE 属性、SHA-256/CRC、独立解压运行以及 GitHub 发布和回下载证据完成后补记。随包文档是整理时快照，外置 SHA256SUMS.txt 与最终仓库报告为附件校验依据；不在 ZIP 内嵌自身摘要。

## 本机最终结果

第三轮构建约 83.7s 完成，实际 EXE FileVersion/ProductVersion 均为 3.0.0。外置扩展的实际加载清单补齐 graphlib 后，冻结 CUDA 的三个案例、预览及导出通过。PyInstaller 对 typing.io/typing.re 两个旧别名记录未发现隐藏模块的非阻塞日志，构建退出成功，实际导入和运行验证通过；原始日志保留于 outputs/build-v3.0.0-traced.log。

完整源码测试 95 passed in 56.07s，退出码 0；规则脚本、pip check、PowerShell 语法及差异检查通过。最终运行 ZIP 为 601057166 字节，SHA-256 为 7e8ec617c0d85a538a0153740840906a1bad87de515b74e32c5b607e5ff729a0。EXE SHA-256 为 d5e97c300a19a9fc6d8191e880a30edbf643a2e93b771154ca2174b56cd228d9。

已从最终 ZIP 解压至 outputs/portable-v3.0.0-final：禁用 CUDA 的 CPU 与真实 CUDA 两次均退出码 0，分别完成三个案例、三点扫描、项目往返、Qt/VTK、六类 PNG、SVG/PDF 和自动预览。CUDA 使用全新 GL3 临时缓存，首次官方头文件下载核验为 true，未使用本机开发 CUDA 目录。实际报告见 release-smoke-v3.0.0.json 与 release-artifacts-v3.0.0.json；已查看解压版截图确认白色界面与图形可读。

应用源码附件在整理最终文档后单独刷新，运行 ZIP 不变；再复核三附件 SHA-256/CRC 和 EXE 摘要，避免因记录文件更新而重复改写已验证的运行包。远端发布及回下载证据另行追加，不能以本机通过替代远端验证。

## 发布通道调整

本地基线为 b4806c3，标签 v3.0.0 已推送。代理的大文件写入低速/超时与 DEV-008 历史现象一致，改用 Actions 构建同一标签并上传到私有草稿；工作流不自动发布。云端构建的时间/路径不同，ZIP 和 EXE 摘要可能变化，必须分别记录，本机原始附件不冒充远端文件。回下载验证允许明确指定草稿，只有实际 CPU/CUDA 通过后才解除草稿。

## 远端正式发布结果

[Actions 43613876322](https://github.com/oldcatnine/GaussianLab/actions/runs/43613876322) 已 success；[V3.0.0 发行页](https://github.com/oldcatnine/GaussianLab/releases/tag/v3.0.0) 已正式发布，draft=false、private=true。应用来源为 b4806c3/v3.0.0，后续发布通道调整不改写标签。

回下载三 ZIP 与校验清单，GitHub digest、SHA-256 和 ZIP CRC 均通过；下载版禁用 CUDA 的 CPU 与实际 CUDA 均退出码 0，三个案例、三维场景、扫描、配置、六类 PNG/SVG/PDF 及自动预览通过，CUDA 的独立新缓存首次官方补充核验为 true。最终运行 ZIP 为 600938694 字节，SHA-256 为 29a2ae19b9987915cf3da3304c9d5f22c30946514421eb5bee3545afdc68f321；EXE 摘要为 9fbcb2663cb4f90129fdb23facfa2a6031ce68fe0e33bde2d4692d8673c29f04。完整数据见 github-release-v3.0.0.json 与 github-release-smoke-v3.0.0.json。

本地 releases/v3.0.0 已同步为远端下载并复测的附件和程序；原始本机构建移至 outputs/local-build-v3.0.0，原始 release-artifacts/release-smoke 记录保留。下载复用要求文件大小与服务器摘要同时匹配；为避免 CuPy 深目录触及 Windows 路径限制，测试解压采用短 outputs/gh3-* 路径。未更改仓库可见性、邀请他人或覆盖历史发行。
