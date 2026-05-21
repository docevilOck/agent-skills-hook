param(
    [string]$RepoRoot = ""
)

if ($RepoRoot -eq "") {
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}

$ErrorActionPreference = "Stop"

$Src = Join-Path $env:USERPROFILE ".cache\huggingface\hub\models--minishlab--potion-code-16M"
$Dest = Join-Path $RepoRoot "third_party\semble\huggingface\hub\models--minishlab--potion-code-16M"

if (-not (Test-Path $Src)) {
    throw "Local Semble model cache not found at $Src"
}

if (Test-Path $Dest) {
    Remove-Item $Dest -Recurse -Force
}

New-Item -ItemType Directory -Path (Split-Path $Dest -Parent) -Force | Out-Null
$null = robocopy $Src $Dest /E /NFL /NDL /NJH /NJS /NC /NS
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed copying '$Src' to '$Dest' with exit code $LASTEXITCODE"
}

Write-Host "Exported Semble model cache to $Dest"
