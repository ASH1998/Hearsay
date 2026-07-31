param(
    [ValidateRange(30, 600)]
    [int]$TimeoutSeconds = 300,
    [ValidateRange(1024, 65535)]
    [int]$WebPort = 3100,
    [ValidateRange(1024, 65535)]
    [int]$ApiPort = 8100
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$nextEnvPath = Join-Path $repo "apps/web/next-env.d.ts"
$nextEnvOriginal = [System.IO.File]::ReadAllText($nextEnvPath)

$qaDirectory = Join-Path $repo ".qa"
New-Item -ItemType Directory -Force -Path $qaDirectory | Out-Null
$stopFile = Join-Path $qaDirectory "stop-qa-servers"
Remove-Item -LiteralPath $stopFile -Force -ErrorAction SilentlyContinue

$python = Join-Path $repo "tools/python/cpython-3.12.13-windows-x86_64-none/python.exe"
$node = (Get-Command node.exe -ErrorAction Stop).Source

$env:PYTHONPATH = "apps/api/src;.venv/Lib/site-packages"
$env:HEARSAY_EMBEDDING_PROVIDER = "fallback"
$env:HEARSAY_ENV = "test"
$env:HEARSAY_LLM_PROVIDER = "fallback"
$env:HEARSAY_PERSISTENCE_BACKEND = "memory"
$env:HEARSAY_WEB_ORIGIN = "http://localhost:$WebPort"
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:$ApiPort"
$env:HEARSAY_NEXT_DIST_DIR = ".next-visual"

$api = $null
$web = $null

try {
    $api = Start-Process -FilePath $python `
        -ArgumentList @(
            "-m",
            "uvicorn",
            "hearsay_api.main:app",
            "--app-dir",
            "apps/api/src",
            "--host",
            "127.0.0.1",
            "--port",
            "$ApiPort"
        ) `
        -WorkingDirectory $repo `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $qaDirectory "visual-api.stdout.log") `
        -RedirectStandardError (Join-Path $qaDirectory "visual-api.stderr.log") `
        -PassThru

    $web = Start-Process -FilePath $node `
        -ArgumentList @(
            "apps/web/node_modules/next/dist/bin/next",
            "dev",
            "apps/web",
            "--webpack",
            "-p",
            "$WebPort"
        ) `
        -WorkingDirectory $repo `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $qaDirectory "visual-web.stdout.log") `
        -RedirectStandardError (Join-Path $qaDirectory "visual-web.stderr.log") `
        -PassThru

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline -and -not (Test-Path -LiteralPath $stopFile)) {
        if ($api.HasExited -or $web.HasExited) {
            throw "A visual-QA server exited unexpectedly."
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    foreach ($server in @($web, $api)) {
        if ($null -ne $server -and -not $server.HasExited) {
            Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
            $server.WaitForExit(5000) | Out-Null
        }
    }
    Remove-Item -LiteralPath $stopFile -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 250
    [System.IO.File]::WriteAllText(
        $nextEnvPath,
        $nextEnvOriginal,
        [System.Text.UTF8Encoding]::new($false)
    )
}
