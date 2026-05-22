param(
    [string]$RepoRoot = ""
)

if ($RepoRoot -eq "") {
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}

$ErrorActionPreference = "Stop"

$Src = Join-Path $env:USERPROFILE ".cache\huggingface\hub\models--minishlab--potion-code-16M"
$Dest = Join-Path $RepoRoot "third_party\semble\huggingface\hub\models--minishlab--potion-code-16M"
$SnapshotRel = "snapshots\86848193a842865570d9c8d3e7d268b66ab52752\model.safetensors"
$MinBinaryBytes = 1048576

function Test-SemblePointerFile {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path -PathType Leaf)) {
        return $false
    }

    $firstLine = Get-Content -LiteralPath $Path -TotalCount 1 -ErrorAction Stop
    return $firstLine -eq "version https://git-lfs.github.com/spec/v1"
}

function Assert-SembleLocalCacheValid {
    param(
        [string]$CacheRoot
    )

    $snapshotFile = Join-Path $CacheRoot $SnapshotRel
    if (-not (Test-Path $snapshotFile -PathType Leaf)) {
        throw "Local Semble snapshot not found at $snapshotFile"
    }

    $item = Get-Item -LiteralPath $snapshotFile -ErrorAction Stop
    if ($item.Length -lt $MinBinaryBytes -or (Test-SemblePointerFile -Path $snapshotFile)) {
        throw "Local Semble snapshot is not a valid binary safetensors file: $snapshotFile"
    }
}

if (-not (Test-Path $Src)) {
    throw "Local Semble model cache not found at $Src"
}

Assert-SembleLocalCacheValid -CacheRoot $Src

if (Test-Path $Dest) {
    Remove-Item $Dest -Recurse -Force
}

New-Item -ItemType Directory -Path (Split-Path $Dest -Parent) -Force | Out-Null
$null = robocopy $Src $Dest /E /NFL /NDL /NJH /NJS /NC /NS
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed copying '$Src' to '$Dest' with exit code $LASTEXITCODE"
}

Write-Host "Exported Semble model cache to $Dest"
