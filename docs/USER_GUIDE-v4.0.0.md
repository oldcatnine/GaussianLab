# GaussianLab V4.0.0 便携版操作

建议解压至有写权限的短目录，以免 Windows 路径长度限制影响深层头文件。将 `GaussianLab-v4.0.0-Windows-x64.zip` 完整解压到 Windows 10/11 x64 电脑，双击 `GaussianLab.exe`，窗口标题应显示 V4.0.0。保留同目录的 `_internal`、使用说明和许可文件，无需安装 Python 或手动安装 CuPy。

运行包包含 CuPy 14.2.0、CUDA 12.9 的 cudart、NVRTC、cuFFT、nvJitLink 与必要许可。显卡驱动由电脑系统提供。兼容 NVIDIA 显卡可选择“CUDA 优先”；自动模式在小网格时使用 CPU。首次 CUDA 需联网下载约 3.6 MB 固定官方头文件，核对 SHA-256 后生成本机缓存；短暂网络中断会最多尝试 3 次，网络或显卡不可用时使用 CPU。重新打开程序可重试。

在“相干输入光 / 横模”应用 HG、LG 或相干叠加案例，编辑阶数、振幅和入口相位。完整网格默认 1024×1024，可选最高 4096×4096，轴向最高 2049 点；结果 RAM 预算可设置，自动模式超预算转存磁盘，FFT 工作区等开销另计。点击“计算光场”取得完整结果；自动预览最多 256×256 / 33 点。

成功条件：状态显示“完整结果”、选定的 N 和实际 CPU/CUDA 后端；修改相干叠加的相位会改变光斑分布。没有 NVIDIA 显卡时，CPU 完成计算也属于正常使用。三维图形显示不能证明 GPU 数值计算已经启用。

从源码运行时，先按 [README](../README.md) 创建 `.venv`，再双击根目录 `安装显卡加速.cmd`。安装器把固定的可选运行组件装到当前用户私有目录，执行真实 FFT 自检，不修改系统驱动。若用户名含中文，可在 PowerShell 7 执行 `./scripts/install_cuda_runtime.ps1 -RuntimeDirectory C:\GaussianLabCuda`，并在启动前设置 `GAUSSIANLAB_CUDA_PATH` 指向该自定义目录。安装后重启程序。

详细操作见 [当前指南](USER_GUIDE.md)，计算模型见 [项目学习手册](项目学习手册.md)。

## 网络受限时初始化 CUDA

若首次 CUDA 下载报 TLS/网络错误，可暂时使用 CPU。需要离线启用 GPU 时，从随包 `_internal/cuda_runtime/CUDA-HEADERS.json` 读取固定官方下载地址，在可联网的电脑下载 `nvidia_cuda_runtime_cu12-12.9.79-py3-none-win_amd64.whl`，复制到当前电脑。不要使用改名的其他版本。

在 EXE 所在目录打开 PowerShell，设置本地文件路径后启动：

```powershell
$env:GAUSSIANLAB_CUDA_HEADERS_WHEEL = 'C:\Downloads\nvidia_cuda_runtime_cu12-12.9.79-py3-none-win_amd64.whl'
.\GaussianLab.exe
```

软件核对固定字节数和 SHA-256，校验通过才提取头文件到本机私有缓存；之后可正常双击 EXE，不再需要该环境变量。这个本地轮子由使用者从官方来源获取，不包含在运行包中，也不需要安装 Python。该方法不关闭 HTTPS 校验、不修改系统代理或驱动。

## 第四代新增入口

完整 TEM 双方向 0—3 阶、LG01—LG05 与 TEM01+TEM10 共 22 项预设；三维横截面与二维计算结果对应。可设置图像平滑、图表坐标范围、2D/3D 显示与磁盘结果存储。详细操作和当前资源约束以 [当前指南](USER_GUIDE.md) 为准，早期 V3.1.1 的内存上限不作为第四代完整功能清单。
