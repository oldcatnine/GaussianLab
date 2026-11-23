# V3.1.1 安装与便携交付验证

日期：2026-11-23。范围是本机 Windows x64、RTX 4060 Laptop GPU，其他实体机器尚待验证。

## 安装与环境诊断

先复查 CuPy 原仓库与官方安装说明，沿用已锁定的 CuPy 14.2.0 和 CUDA 12.9。固定光场与 FFT 所需的 6 个包：CuPy、cuda-pathfinder、cudart、NVRTC、cuFFT、nvJitLink。没有安装系统 CUDA Toolkit 或修改 NVIDIA 驱动；没有复制第三方算法源码。

安装目标为真实用户的 `LOCALAPPDATA/GaussianLab/cuda-v2-dev`。首次运行旧 pip 因 GBK 解码中文依赖注释失败，改为 `python -X utf8 -m pip` 后安装成功，真实 GPU FFT 自检返回 `used=cuda`、设备 `NVIDIA GeForce RTX 4060 Laptop GPU`。

默认测试沙箱会将 LOCALAPPDATA 重定向到 Codex 私有沙箱，因此普通沙箱命令仍报告 `No module named cupy`；不能据此认定用户真实环境没有装好。退出该沙箱、在真实用户环境执行原 GPU 测试，11 项通过、0 跳过。随后加入高阶 HG、LG 和相干叠加的专项 GPU 对照及安装入口检查。

新增高阶/相干 GPU 对照及入口检查后，首次完整回归 118 项通过、0 跳过（56.98 s）。修复 NVIDIA 命名空间包整理并增加专项后，最终完整回归 119 项通过、0 跳过（57.26 s）。有 1 条第三方 CUDA_PATH 提示；实际 CUDA FFT 和全部 GPU 对照均成功，不要求系统 Toolkit。

## 构建与冻结验证

为保留原有未提交的工作台设计与 IDE 配置，从已提交源码叠加本轮差异生成独立构建快照。学习手册和文件索引按该快照生成，应用源码 ZIP 包含新安装入口和维护文档。构建脚本支持显式 `-PythonExecutable`，继续使用现有锁定构建环境。

首次独立解压受 Windows MAX_PATH 限制，验证脚本默认改用短临时目录。第一轮解压 EXE 的 CPU 冒烟通过；CUDA 首次官方头文件下载遭 TLS EOF 中断，实际回退 CPU，未将其记为 GPU 通过。随后增加最多 3 次网络异常重试，每次覆盖部分下载，仍检查 HTTPS、字节数与 SHA-256；TLS 恢复及错误摘要拒绝专项通过，重新构建并复测。后续同进程对照发现原始/隔离 PATH 均会失败，Windows 原生 HTTPS 请求也失败，故不能归因于冻结环境。此前一次官方请求曾返回 3591604 字节并匹配 SHA-256，此后网络均出现 TLS EOF。未关闭证书校验或更改系统代理。

从旧 pip 的 MessagePack 响应缓存恢复官方轮子，仅提取响应 body，按固定字节数和 SHA-256 确认完全一致。增加用户指定本地官方轮子的离线初始化选项，与在线流程使用相同摘要和路径校验；运行包不包含该轮子。TLS 重试、坏摘要拒绝和离线无网络初始化 3 项专项通过。冻结 GPU 将在全新缓存中以 local-wheel 来源验证，明确区分联网下载通过与离线校验通过。最终解压 EXE 的 CPU、CUDA 均通过，退出码均为 0，版本为 3.1.1，同一 EXE 摘要。覆盖默认 1024 网格、三个案例、自动预览、Qt/VTK 三维、PNG/SVG/PDF 导出、模式控件经真实线程的 HG00+HG10 相干输入，以及高阶 HG12/LG12。CUDA 设备为 RTX 4060 Laptop GPU。

全新 CUDA 缓存中的头文件摘要验证通过，来源明确为 local-wheel，headers_download_verified=false。不能把本轮离线初始化写成联网首次下载验收通过。当前网络的 TLS EOF 仍是外部限制；网络正常时可按既有官方在线流程尝试，离线步骤见 V3.1.1 指南。附件摘要与完整冻结字段见 release-artifacts-v3.1.1.json、release-smoke-v3.1.1.json。ZIP 内维护文档为构建快照，最终附件摘要以交付目录外置 JSON 和 SHA256SUMS.txt 为准。构建使用既有 PyInstaller、随包运行组件清单和固定 SHA-256 的 Qt 对应源码，不自动上传或发布。

便携包首次 CUDA 仍需联网补充官方头文件。独立冻结测试移除开发 Python、Qt 和 GAUSSIANLAB_CUDA_PATH，使用新缓存验证实际程序；CPU 模式显式禁用 CUDA。GPU 图形渲染不作为 CUDA 数值计算证据。

最终收口：全部更改和冻结证据纳入后，真实用户环境完整回归 122 项通过、0 跳过（53.96 s）；独立提交快照文档/中文规范 15 项通过。安装脚本在 Windows PowerShell 5 解析通过，项目规则脚本与 Git 差异检查通过。其他实体机器未实测，网络首次在线下载在本轮持续 TLS 故障下未通过，已提供并验证本地官方轮子替代路径。
