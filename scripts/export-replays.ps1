$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "tools/python/cpython-3.12.13-windows-x86_64-none/python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Pinned Python is missing. Run 'corepack pnpm@11.9.0 bootstrap' first."
}

$env:PYTHONPATH = "apps/api/src;.venv/Lib/site-packages"
& $python (Join-Path $repo "scripts/export_replays.py")
if ($LASTEXITCODE -ne 0) {
    throw "Replay export failed."
}
