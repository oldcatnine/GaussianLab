param([string]$SourceCache = '', [string]$CudaRuntime = (Join-Path $env:LOCALAPPDATA 'GaussianLab\cuda-v2-dev'))
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$releaseVersion = (& $pythonPath -c "from gaussian_lab import __version__; print(__version__)").Trim()
if ($LASTEXITCODE -ne 0 -or $releaseVersion -notmatch '^\d+\.\d+\.\d+$') { throw '应用版本无效。' }
$releaseTag = 'v' + $releaseVersion
$cudaStage = Join-Path $projectRoot "build/$releaseTag/cuda_runtime"
if (-not (Test-Path -LiteralPath (Join-Path $cudaStage 'RUNTIME-MANIFEST.json'))) {
    & $pythonPath scripts/stage_cuda_runtime.py --source $CudaRuntime --target $cudaStage
    if ($LASTEXITCODE -ne 0) { throw '随包 CUDA 运行组件整理失败。' }
}
& $pythonPath -m PyInstaller --noconfirm --distpath "dist/$releaseTag" --workpath "build/$releaseTag" GaussianLab.spec
if ($LASTEXITCODE -ne 0) { throw '可执行程序构建失败。' }
Copy-Item -LiteralPath $cudaStage -Destination (Join-Path $projectRoot "dist/$releaseTag/GaussianLab/_internal/cuda_runtime") -Recurse -Force
if (-not $SourceCache) {
    $previousCache = Join-Path $projectRoot 'releases/v0.1.0/qt-sources'
    if (Test-Path -LiteralPath $previousCache) { $SourceCache = $previousCache }
}
if ($SourceCache) { & $pythonPath scripts/prepare_release.py --source-cache $SourceCache }
else { & $pythonPath scripts/prepare_release.py }
if ($LASTEXITCODE -ne 0) { throw '发行文件整理失败。' }
Write-Output "发行文件已生成于 releases/$releaseTag。"
