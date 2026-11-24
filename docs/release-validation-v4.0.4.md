# V4.0.4 便携 EXE 发行验证

2026-11-24。以源码标签 v4.0.4（9d18872）构建，发行包含三个 ZIP 与 SHA256SUMS.txt；历史发行保持原样。本次没有修改应用代码或递增版本，属于同一版本的打包与证据记录。

## 构建与运行

- 源码回归为 187 项通过、0 跳过，80.11 秒；实际 GUI 与 CUDA 检查见 DEV-040。
- GitHub Actions [45334443241](https://github.com/oldcatnine/GaussianLab/actions/runs/45334443241) 成功：依赖、计算/发布检查、构建与上传均成功。无显卡的远端构建不作为 CUDA 运行验收。
- 实际下载运行包、Qt 对应源码、应用源码与校验清单，核对 SHA-256、GitHub digest、ZIP CRC。三个 ZIP 的实际字节数和摘要见 [附件证据](github-release-v4.0.4.json)。官方附件采用 HTTP Range 并行回下载，检查各段范围/长度后合并核对完整摘要，保持 TLS 校验。
- 下载版 EXE 在隔离开发 Python/Qt 环境变量后分别运行 CPU 和真实 CUDA，均退出码 0；核验三个光学案例、三维渲染、预览、相干输入、配置、扫描及 PNG/SVG/PDF 导出。两次使用同一 EXE 摘要，CUDA 独立缓存完成官方头文件校验。见 [冻结运行证据](github-release-smoke-v4.0.4.json)。
- 实际 EXE 的 Windows FileVersion 和 ProductVersion 均为 4.0.4，窗口标题为 V4.0.4。核验后发布为 GitHub 最新版本，记录最终附件地址。

## 使用

下载 GaussianLab-v4.0.4-Windows-x64.zip，完整解压后双击 GaussianLab.exe。保留 _internal 和随附文件，不要求安装 Python。CPU 可直接使用；CUDA 需要兼容 NVIDIA 驱动，首次使用校验并补充固定官方头文件缓存，失败时可使用 CPU。

本机已将实际下载版整理到 releases/v4.0.4，含运行目录、三个 ZIP 和校验清单。不要仅复制 EXE。V4.0.4 已包含工作区、轻量选择框与步进按钮以及内存说明裁切修复；早期“源码更新”段落是阶段记录。

## 边界

本次是软件与本机 Windows 的发行验证，不构成跨所有电脑的兼容性或实体光学实验结论。标签与包内资料为构建时快照，本页及证据提交补录发布结果；不修改历史附件或摘要。
