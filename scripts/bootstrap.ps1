$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$env:UV_PROJECT_ENVIRONMENT = Join-Path $repo ".venv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repo "tools/python"
$env:UV_CACHE_DIR = Join-Path $repo ".cache/uv"
$env:UV_TOOL_DIR = Join-Path $repo "tools/uv-tools"
$env:HF_HOME = Join-Path $repo ".cache/huggingface"
$env:TORCH_HOME = Join-Path $repo ".cache/torch"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $repo ".cache/ms-playwright"
$env:COREPACK_HOME = Join-Path $repo ".cache/corepack"
$env:CI = "true"

$uvDir = Join-Path $repo "tools/uv"
$uvExe = Join-Path $uvDir "uv.exe"

if (-not (Test-Path -LiteralPath $uvExe)) {
    New-Item -ItemType Directory -Force -Path $uvDir | Out-Null
    $env:UV_UNMANAGED_INSTALL = $uvDir
    $installerUrl = "https://releases.astral.sh/github/uv/releases/download/0.11.15/uv-installer.ps1"
    Write-Host "Installing pinned uv 0.11.15 into tools/uv..."
    $installer = Invoke-RestMethod -Uri $installerUrl
    Invoke-Expression $installer
}

$uvVersion = & $uvExe --version
if ($uvVersion -notmatch "uv 0\.11\.15") {
    throw "Expected uv 0.11.15, found: $uvVersion"
}

$uvHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $uvExe).Hash.ToLowerInvariant()
Write-Host "$uvVersion (uv.exe sha256: $uvHash)"

& $uvExe python install 3.12
if ($LASTEXITCODE -ne 0) {
    throw "uv could not install Python 3.12."
}

$pythonExe = Join-Path $repo "tools/python/cpython-3.12.13-windows-x86_64-none/python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "The pinned repository-local Python 3.12.13 executable is missing."
}

& $uvExe sync --all-groups --python $pythonExe
if ($LASTEXITCODE -ne 0) {
    throw "uv dependency synchronization failed."
}

corepack pnpm@11.9.0 install --frozen-lockfile
if ($LASTEXITCODE -ne 0) {
    throw "pnpm dependency installation failed."
}

Write-Host "Bootstrap complete. Run 'pnpm doctor', then 'pnpm dev'."
