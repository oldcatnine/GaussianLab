$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$agentsPath = Join-Path $projectRoot 'agents.md'
if (-not (Test-Path -LiteralPath $agentsPath -PathType Leaf)) {
    throw '缺少 agents.md 项目规则文件。'
}
$content = [System.IO.File]::ReadAllText($agentsPath)
$requiredRules = @(
    '每次改动完成后，都必须创建一个对应的 Git commit，以便后续追踪和回滚。',
    '每次改动后，都必须编写或更新相关测试，并在交付给用户前确保所有测试和验证全部通过。',
    'docs/development-log.md',
    '在交付及对应 Git commit 前完成记录'
)
foreach ($rule in $requiredRules) {
    if (-not $content.Contains($rule)) {
        throw "缺少必需的规则： $rule"
    }
}
Write-Output '通过：项目规则已包含提交、验证和过程记录要求。'
