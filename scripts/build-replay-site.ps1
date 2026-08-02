$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$web = Join-Path $repo "apps/web"
$export = Join-Path $web ".next-replay"
$dist = Join-Path $web "dist"
$client = Join-Path $dist "client"
$server = Join-Path $dist "server"
$worker = Join-Path $web "worker/replay-static.js"

$resolvedRepo = [System.IO.Path]::GetFullPath($repo)
$resolvedDist = [System.IO.Path]::GetFullPath($dist)
if (-not $resolvedDist.StartsWith($resolvedRepo, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Replay distribution directory escaped the repository."
}

$env:HEARSAY_STATIC_REPLAY = "1"
$env:NEXT_PUBLIC_HEARSAY_REPLAY_HOME = "1"
$env:HEARSAY_NEXT_DIST_DIR = ".next-replay"
if (-not $env:NEXT_PUBLIC_SITE_URL) {
    $env:NEXT_PUBLIC_SITE_URL = "https://hearsay.ashutoshmishra.dev"
}

Push-Location $repo
try {
    corepack pnpm@11.9.0 replay:export
    if ($LASTEXITCODE -ne 0) { throw "Replay export failed." }

    corepack pnpm@11.9.0 --filter @hearsay/web build
    if ($LASTEXITCODE -ne 0) { throw "Static replay build failed." }

    if (Test-Path -LiteralPath $dist) {
        Remove-Item -LiteralPath $dist -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $client, $server | Out-Null
    Copy-Item -Path (Join-Path $export "*") -Destination $client -Recurse -Force
    Copy-Item -LiteralPath $worker -Destination (Join-Path $server "index.js") -Force
    Write-Host "Static replay site staged at apps/web/dist."
} finally {
    Pop-Location
}
