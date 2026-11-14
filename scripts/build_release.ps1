param([string]$SourceCache = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$releaseVersion = (& $pythonPath -c "from gaussian_lab import __version__; print(__version__)").Trim()
if ($LASTEXITCODE -ne 0 -or $releaseVersion -notmatch '^\d+\.\d+\.\d+$') { throw '应用版本无效。' }
$releaseTag = 'v' + $releaseVersion
& $pythonPath -m PyInstaller --noconfirm --distpath "dist/$releaseTag" --workpath "build/$releaseTag" GaussianLab.spec
if ($LASTEXITCODE -ne 0) { throw '可执行程序构建失败。' }
if (-not $SourceCache) {
    $previousCache = Join-Path $projectRoot 'releases/v0.1.0/qt-sources'
    if (Test-Path -LiteralPath $previousCache) { $SourceCache = $previousCache }
}
if ($SourceCache) { & $pythonPath scripts/prepare_release.py --source-cache $SourceCache }
else { & $pythonPath scripts/prepare_release.py }
if ($LASTEXITCODE -ne 0) { throw '发行文件整理失败。' }
Write-Output "发行文件已生成于 releases/$releaseTag。"
