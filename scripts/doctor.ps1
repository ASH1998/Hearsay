$ErrorActionPreference = "Continue"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$failed = $false

$env:UV_PROJECT_ENVIRONMENT = Join-Path $repo ".venv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repo "tools/python"
$env:UV_CACHE_DIR = Join-Path $repo ".cache/uv"
$env:UV_TOOL_DIR = Join-Path $repo "tools/uv-tools"
$env:COREPACK_HOME = Join-Path $repo ".cache/corepack"

function Check-Command {
    param([string]$Name, [scriptblock]$Command)
    try {
        $value = & $Command
        Write-Host "[ok] $Name`: $value"
    } catch {
        Write-Host "[missing] $Name"
        $script:failed = $true
    }
}

Check-Command "Node" { node --version }
Check-Command "pnpm" { corepack pnpm@11.9.0 --version }
Check-Command "uv" { & "tools/uv/uv.exe" --version }
Check-Command "Python project runtime" { & "tools/uv/uv.exe" run python --version }

$requiredNames = @(
    "HEARSAY_ENV",
    "HEARSAY_API_HOST",
    "HEARSAY_API_PORT",
    "HEARSAY_WEB_ORIGIN",
    "NEXT_PUBLIC_API_BASE_URL",
    "HEARSAY_PERSISTENCE_BACKEND",
    "DATABASE_URL"
)
$exampleNames = Get-Content -LiteralPath ".env.example" |
    Where-Object { $_ -match "^[A-Z][A-Z0-9_]*=" } |
    ForEach-Object { ($_ -split "=", 2)[0] }

foreach ($name in $requiredNames) {
    if ($exampleNames -contains $name) {
        Write-Host "[ok] .env.example declares $name"
    } else {
        Write-Host "[missing] .env.example does not declare $name"
        $failed = $true
    }
}

$archiveCount = (Get-ChildItem -LiteralPath "assets/downloads" -File -ErrorAction SilentlyContinue).Count
Write-Host "[info] Raw asset candidates present: $archiveCount"

& "tools/uv/uv.exe" run python scripts/build_assets.py --validate-only
if ($LASTEXITCODE -ne 0) {
    Write-Host "[failed] Runtime asset validation"
    $failed = $true
}

& "tools/uv/uv.exe" run python scripts/check_database.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[failed] Configured CockroachDB Cloud health/vector check"
    $failed = $true
}

if ($failed) {
    throw "Doctor found blocking local setup issues. Run 'pnpm bootstrap' and retry."
}

Write-Host "Doctor passed."
