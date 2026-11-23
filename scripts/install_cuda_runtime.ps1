param([string]$RuntimeDirectory = (Join-Path $env:LOCALAPPDATA 'GaussianLab\cuda-v2-dev'))
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw '请先按 README 创建项目 Python 环境。' }
$runtimePath = [IO.Path]::GetFullPath($RuntimeDirectory)
if ($runtimePath -match '[^\x00-\x7F]') { throw 'CUDA 编译头文件需要 ASCII 路径，请通过 -RuntimeDirectory 指定英文目录。' }
# 仅安装固定的可选显卡库，不替换基础环境，也不安装或修改系统显卡驱动。
& $pythonExe -X utf8 -m pip install --upgrade --only-binary=:all: --target $runtimePath --no-deps -r (Join-Path $projectRoot 'requirements-cuda.txt')
if ($LASTEXITCODE -ne 0) { throw 'CUDA 可选库安装失败；CPU 模式仍然可用。' }
$env:GAUSSIANLAB_CUDA_PATH = $runtimePath
Push-Location $projectRoot
try {
    & $pythonExe -c "from gaussian_lab.backend import select_backend; import json; b=select_backend('cuda'); print(json.dumps(b.information(),ensure_ascii=True)); raise SystemExit(0 if b.name=='cuda' else 1)"
    if ($LASTEXITCODE -ne 0) { throw 'CUDA 实测自检未通过，请读取上方原因；没有修改系统驱动，可继续使用 CPU。' }
} finally { Pop-Location }
Write-Output "CUDA 自检通过。独立运行库：$runtimePath"
Write-Output '如使用自定义路径，启动应用前设置 GAUSSIANLAB_CUDA_PATH；默认路径可自动识别。'
