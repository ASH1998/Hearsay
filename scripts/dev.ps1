$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$env:UV_PROJECT_ENVIRONMENT = Join-Path $repo ".venv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repo "tools/python"
$env:UV_CACHE_DIR = Join-Path $repo ".cache/uv"
$env:UV_TOOL_DIR = Join-Path $repo "tools/uv-tools"

if (-not (Test-Path -LiteralPath "tools/uv/uv.exe")) {
    throw "Local uv is missing. Run 'corepack pnpm@11.9.0 bootstrap' first."
}

$api = Start-Process -FilePath "tools/uv/uv.exe" `
    -ArgumentList @("run", "uvicorn", "hearsay_api.main:app", "--app-dir", "apps/api/src", "--reload", "--port", "8000") `
    -WorkingDirectory $repo `
    -WindowStyle Hidden `
    -PassThru

try {
    corepack pnpm@11.9.0 --filter @hearsay/web dev
} finally {
    if (-not $api.HasExited) {
        Stop-Process -Id $api.Id
    }
}
