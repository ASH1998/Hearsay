$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$manifest = Get-Content -Raw -LiteralPath "assets/manifest.json" | ConvertFrom-Json
$runtimeBytes = 0
foreach ($asset in $manifest.assets) {
    $path = Join-Path $repo $asset.output
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Manifest output is missing: $($asset.output)"
    }
    $runtimeBytes += (Get-Item -LiteralPath $path).Length
}

$runtimeMb = [math]::Round($runtimeBytes / 1MB, 2)
Write-Host "Validated $($manifest.assets.Count) runtime assets ($runtimeMb MB)."
if ($runtimeBytes -gt 60MB) {
    throw "Full-session runtime asset budget exceeded (60 MB)."
}
