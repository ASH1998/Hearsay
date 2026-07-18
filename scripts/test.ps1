$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$env:UV_PROJECT_ENVIRONMENT = Join-Path $repo ".venv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repo "tools/python"
$env:UV_CACHE_DIR = Join-Path $repo ".cache/uv"
$env:UV_TOOL_DIR = Join-Path $repo "tools/uv-tools"
$env:CI = "true"

& "tools/uv/uv.exe" run ruff check apps/api/src apps/api/tests scripts
if ($LASTEXITCODE -ne 0) { throw "Ruff lint failed." }
& "tools/uv/uv.exe" run ruff format --check apps/api/src apps/api/tests scripts
if ($LASTEXITCODE -ne 0) { throw "Ruff format check failed." }
& "tools/uv/uv.exe" run mypy apps/api/src
if ($LASTEXITCODE -ne 0) { throw "mypy failed." }
& "tools/uv/uv.exe" run pytest
if ($LASTEXITCODE -ne 0) { throw "pytest failed." }
pnpm --filter @hearsay/web lint
if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed." }
pnpm --filter @hearsay/web typecheck
if ($LASTEXITCODE -ne 0) { throw "Frontend typecheck failed." }
pnpm --filter @hearsay/web test
if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
