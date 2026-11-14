# V0.1.0 Windows 便携版验证

日期：2026-11-14。对应版本：v0.1.0；构建提交主题：`build: package Windows v0.1.0 and prepare GitHub release`。

## 发行内容

- `GaussianLab-v0.1.0-Windows-x64.zip`：184,378,224 字节，完整解压运行 GaussianLab.exe，无需 Python。包内含依赖、示例、使用说明和完整第三方声明。
- `GaussianLab-v0.1.0-Qt-Corresponding-Source.zip`：73,624,348 字节，第三方对应源码；普通用户运行不需要此附件。
- `SHA256SUMS.txt`：附件完整性校验。

源码位于私有仓库 [oldcatnine/GaussianLab](https://github.com/oldcatnine/GaussianLab)，发布目标为 [v0.1.0](https://github.com/oldcatnine/GaussianLab/releases/tag/v0.1.0)。用户已确认私有，老师在线访问需要授权，或由用户下载运行 ZIP 后转发。

## 自动化与独立运行

1. 全量源码测试：37 passed，退出码 0；协作规则脚本 PASS，pip check 无冲突。
2. PyInstaller 6.22.3 + hooks-contrib 2026.10，Python 3.10.11，Windows x64，onedir，Qt 动态库独立保留。
3. 四个 Qt/PySide6 官方源码归档使用上游公开 SHA-256 核验；提取原始许可证并附 CPython 许可证。
4. 最终两个 ZIP 的 SHA-256 与 ZIP CRC 通过。记录见 [附件清单](release-artifacts-v0.1.0.json)。
5. 从最终运行 ZIP 解压到新的 `outputs/portable-check`。启动前清空 PYTHONHOME/PYTHONPATH，PATH 仅保留 Windows 系统目录，执行 EXE 的 --smoke-test。
6. 冻结程序确认 `frozen=true`，聚焦、扩束、光阑三个案例的计算和真实 Qt/VTK 场景截图通过；项目保存加载、三点孔径扫描、CSV 与观察屏步进通过，退出码 0。见 [独立 EXE 结果](release-smoke-v0.1.0.json)。
7. computer-use 插件选择返回的 `GaussianLab.exe` 窗口对象并观察首屏：束腰 53.7 μm、全局位置 219.7 mm，衍射最小 r86 52.4 μm，三维场景和二维光斑可见。此处与之前 Python 源码窗口分开选择，避免误测源码版。
8. 插件点击 EXE 的“播放传播”，观察到按钮变为“暂停播放”、观察屏从 218.75 mm 移动到 275.00 mm，并联动更新 r86，随后暂停。

## 打包问题与处理

初次冻结程序 QtCore 导入失败。PE 检查显示构建机 PATH 中的 Poppler icuuc.dll 被误打包，缺少 Windows 原生 ICU 的无版本后缀函数；排除该库及其附属 ICU 后使用 System32 中正确版本。包根目录 MSVC 运行库统一采用 Qt wheel 所附的更新版本，避免 Python 3.10 的旧副本优先加载。以上规则写入 spec 并由发布检查验证。

Qt hook 还会发现本程序不用的 PDF、VirtualKeyboard、DataVisualization；已排除相关插件与 DLL。Qt LGPL 动态库、对应源码与许可说明随发行提供。

## 限制

这是当前机器上的独立 Python 环境验证，不是全新 Windows 虚拟机测试。仍需兼容的系统 ICU/OpenGL/显卡驱动，未承诺所有 Windows 和显卡组合。程序未做商业代码签名；本版计算模型与采样限制沿用 [V0.1 数值验证](validation-v0.1.md)。

Release 上传与远端附件核实在完成后补入开发记录，不能以本地构建成功代替远端发布成功。
