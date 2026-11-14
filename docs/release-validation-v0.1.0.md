# V0.1.0 Windows 便携版验证

日期：2026-11-14。对应版本：v0.1.0；构建提交主题：`build: package Windows v0.1.0 and prepare GitHub release`。

## 发行内容

- `GaussianLab-v0.1.0-Windows-x64.zip`：GitHub 最终包 184,256,791 字节，完整解压运行 GaussianLab.exe，无需 Python。包内含依赖、示例、使用说明和完整第三方声明。
- `GaussianLab-v0.1.0-Qt-Corresponding-Source.zip`：73,624,348 字节，第三方对应源码；普通用户运行不需要此附件。
- `SHA256SUMS.txt`：附件完整性校验。

源码位于私有仓库 [oldcatnine/GaussianLab](https://github.com/oldcatnine/GaussianLab)，发布目标为 [v0.1.0](https://github.com/oldcatnine/GaussianLab/releases/tag/v0.1.0)。用户已确认私有，老师在线访问需要授权，或由用户下载运行 ZIP 后转发。

## 自动化与独立运行

1. 全量源码测试：37 passed，退出码 0；协作规则脚本 PASS，pip check 无冲突。
2. PyInstaller 6.22.3 + hooks-contrib 2026.10，Python 3.10.11，Windows x64，onedir，Qt 动态库独立保留。
3. 四个 Qt/PySide6 官方源码归档使用上游公开 SHA-256 核验；提取原始许可证并附 CPython 许可证。
4. 初次本机构建两个 ZIP 的 SHA-256 与 ZIP CRC 通过，原始运行包为 184,378,224 字节。记录见 [本机构建附件清单](release-artifacts-v0.1.0.json)。此清单是本地历史记录，不用于校验 GitHub 端重建的附件。
5. 从最终运行 ZIP 解压到新的 `outputs/portable-check`。启动前清空 PYTHONHOME/PYTHONPATH，PATH 仅保留 Windows 系统目录，执行 EXE 的 --smoke-test。
6. 冻结程序确认 `frozen=true`，聚焦、扩束、光阑三个案例的计算和真实 Qt/VTK 场景截图通过；项目保存加载、三点孔径扫描、CSV 与观察屏步进通过，退出码 0。见 [独立 EXE 结果](release-smoke-v0.1.0.json)。
7. computer-use 插件选择返回的 `GaussianLab.exe` 窗口对象并观察首屏：束腰 53.7 μm、全局位置 219.7 mm，衍射最小 r86 52.4 μm，三维场景和二维光斑可见。此处与之前 Python 源码窗口分开选择，避免误测源码版。
8. 插件点击 EXE 的“播放传播”，观察到按钮变为“暂停播放”、观察屏从 218.75 mm 移动到 275.00 mm，并联动更新 r86，随后暂停。

## 打包问题与处理

初次冻结程序 QtCore 导入失败。PE 检查显示构建机 PATH 中的 Poppler icuuc.dll 被误打包，缺少 Windows 原生 ICU 的无版本后缀函数；排除该库及其附属 ICU 后使用 System32 中正确版本。包根目录 MSVC 运行库统一采用 Qt wheel 所附的更新版本，避免 Python 3.10 的旧副本优先加载。以上规则写入 spec 并由发布检查验证。

Qt hook 还会发现本程序不用的 PDF、VirtualKeyboard、DataVisualization；已排除相关插件与 DLL。Qt LGPL 动态库、对应源码与许可说明随发行提供。

## 限制

这是当前机器上的独立 Python 环境验证，不是全新 Windows 虚拟机测试。仍需兼容的系统 ICU/OpenGL/显卡驱动，未承诺所有 Windows 和显卡组合。程序未做商业代码签名；本版计算模型与采样限制沿用 [V0.1 数值验证](validation-v0.1.md)。

## GitHub 最终发布与交付

本机大文件上传链路低速，因此使用 [GitHub Actions 构建](https://github.com/oldcatnine/GaussianLab/actions/runs/43573110436) 在 Windows runner 上按 v0.1.0 标签构建。依赖、计算/发布检查、打包、附件上传及正式发布全部 success。

[私有 Release v0.1.0](https://github.com/oldcatnine/GaussianLab/releases/tag/v0.1.0) 已发布，draft=false、private=true，包含运行 ZIP、Qt 对应源码 ZIP 和 SHA256SUMS.txt。随后将两个 ZIP 从 GitHub 实际下载，核对服务器 digest、发布校验清单和本地 SHA-256，全部一致，ZIP CRC 通过；见 [GitHub 发布证据](github-release-v0.1.0.json)。

下载得到的 EXE 在仅含 Windows 系统目录的 PATH 下重新运行冻结冒烟测试，三个案例、3D、配置往返、扫描和导出通过，退出码 0；见 [GitHub 下载版 EXE 证据](github-release-smoke-v0.1.0.json)。因此验证对象为远端实际附件，未用旧本地二进制替代。

最终文件整理在 `releases/v0.1.0/`，与 GitHub 附件一致；原本机构建 ZIP 备份在 outputs/local-build-archive。重建造成二进制摘要变化属于不同构建结果，不将初次本地清单冒充远端清单。老师可以接收运行 ZIP 后完整解压运行；直接在线访问私有仓库需要用户邀请授权。

发布证据增加到回归检查后，当前主分支完整测试为 39 项通过、退出码 0；规则验证及依赖检查通过。原始输出见 [最终测试输出](test-results-release-v0.1.0.txt)。此计数包含发布后的验证工具，不改变标签基线的 37 项本地测试记录。
