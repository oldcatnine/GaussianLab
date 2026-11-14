# V2.0.0 便携版构建与验证

版本：2.0.0。平台：Windows x64。关联提交主题：`release: 构建 GaussianLab V2.0.0 便携版`。

## 构建口径

使用现有 Python 3.10.11 和固定的 PyInstaller 6.22.3、PyInstaller hooks 2026.10，继续目录式打包；输出目录为 dist/v2.0.0 与 releases/v2.0.0。窗口标题、包版本、EXE FileVersion/ProductVersion、运行包名称及指南均同步为 2.0.0。旧版文件不覆盖。

Qt 6.12.0、PySide6 6.12.0、Shiboken6 的对应源码从固定摘要清单复核；本机可复用 v0.1.0 的缓存，缺失时才下载官方原始归档。保留原始许可证、CPython 许可、动态库分离结构和重建所需的应用源码附件。

## 验证方法

源码执行完整 pytest、项目规则、依赖一致性和差异空白检查。冻结程序使用 --smoke-test 执行三个案例、真实 Qt/VTK、JSON 往返、扫描、六类白底 PNG 以及 SVG/PDF 导出。

便携附件通过 SHA-256 与 ZIP CRC 检查后，解压至全新的独立目录。执行 EXE 时 PATH 仅保留 Windows 系统目录，移除 PYTHONHOME、PYTHONPATH、VIRTUAL_ENV 与开发用 Qt 路径，并从独立工作目录启动；不能靠项目 .venv 或系统 Python 补齐运行依赖。

## 发现与处理

首次 EXE 已完成三个计算案例和三维渲染，但 SVG 导出失败，提示缺少 matplotlib.backends.backend_svg。构建配置补入 SVG 与 PDF 后端，冻结测试扩展到实际格式保存；第一次失败不计作交付通过。

V0.1.0 冻结扫描断言只接受 ok，与当前 warning 状态不兼容；新版允许带明确警告的有效点，仍拒绝 error，并保留扫描状态记录。光学算法和采样警告没有为打包而关闭。

## 附件与边界

运行只需完整解压 GaussianLab-v2.0.0-Windows-x64.zip，不需要安装 Python 或 CUDA。Qt 对应源码、应用源码和 SHA256SUMS.txt 作为同版本附件提供。随包文档是整理附件时的快照，最终解压验证记录与附件摘要在仓库中另行归档，避免在 ZIP 内嵌自身摘要造成循环。

目标为 Windows 10/11 x64；本次实际环境为本机 Windows 11。隔离开发路径不等于已经在另一台实体电脑或所有显卡上测试。未作商业代码签名，也未上传新的 GitHub Release。


## 本机构建版结果

第二次构建完成后，Windows 文件属性 FileVersion 与 ProductVersion 均为 2.0.0。直接构建目录的 EXE 已在隔离 PATH 下完成三个案例、三维渲染、配置往返、三点孔径扫描、六类白底 PNG、SVG/PDF 导出；frozen=true、status=passed、退出码 0，窗口标题含 V2.0.0。三点扫描保留 warning，符合低网格测试场景的采样提示，不把警告点改写为无警告。

最终 ZIP 的摘要、解压版复测和同版本附件信息在构建完成后独立归档；校验时以运行包旁的 SHA256SUMS.txt 为准。

## 独立解压版结果

运行包已通过 SHA-256 和 ZIP CRC 检查，解压至 outputs/portable-v2.0.0-final 后，在隔离开发路径的环境中通过全部冻结自测，退出码 0。三个案例、三点扫描、六类 PNG、SVG/PDF 与白底检查通过；已查看 desktop-v2.png，三维光路、包围能量及扫描曲线可读。

EXE SHA-256：d2acb4610616c5888724e14681ffc351867e600386a8ffcf435e0cd809001c82。运行 ZIP 为 188667175 字节；摘要与检查详情见 release-artifacts-v2.0.0.json、release-smoke-v2.0.0.json。应用源码整理支持没有 .git 的解压目录，按随附文件清单重建源码附件；源码附件单独刷新，不改变已验证的运行包。
