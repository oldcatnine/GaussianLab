# GaussianLab V3.0.0

V3.0.0 将独立 CUDA 开发分支整理为 Windows x64 便携发行，保留 V2.0.0 历史附件。

- 可选 CUDA FFT 和复光场计算，设备不可用或执行故障自动回退 CPU，记录实际后端与原因。
- 数值框停止输入 400 ms 后自动预览，完整计算保持原始采样与焦区细化；取消过期任务并丢弃迟到结果。
- 光路区段频谱复用、128 MiB 会话缓存、场景几何和游标复用、拖动更新合并，减少重复计算与绘制。
- 保留白色主题、六类 PNG/SVG/PDF 导出、扫描和收敛；预览图与数据明确标记质量，导出使用独立快照。
- 内含 CuPy/CUDA 运行组件，无需 Python。首次 CUDA 需联网下载约 3.6 MB 固定官方头文件并建立本机缓存；显卡需要兼容 NVIDIA 驱动，离线首次使用仍可运行 CPU。

分支实测在 RTX 4060 上，四个固定场景 CUDA 内核相对 V2.0.0 约快 15—27 倍，优化 CPU 约快 2.0—2.3 倍。它们是预热后的同精度内核计时，不能当作首次启动或全部电脑的响应承诺；真实窗口仍存在首次初始化与绘制耗时。

附件：Windows-x64 运行 ZIP、Qt-Corresponding-Source ZIP、Application-Source ZIP 及 SHA256SUMS.txt。运行只需完整解压 Windows-x64 ZIP；两个源码附件不必为运行解压。Qt LGPL 对应源码与 CUDA 原始许可保留。

目标为 Windows 10/11 x64；本机 CUDA 与禁用 CUDA 的冻结验证在交付前执行并记录于 release-validation-v3.0.0.md。未商业签名；其他实体设备仍需实测。不包含完整 CUDA Toolkit 或驱动安装器，不改变仓库的私有设置。
