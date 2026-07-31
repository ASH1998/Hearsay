$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$python = Join-Path $repo "tools/python/cpython-3.12.13-windows-x86_64-none/python.exe"
$node = (Get-Command node.exe -ErrorAction Stop).Source
$api = $null
$web = $null

function Test-LocalPort {
    param([int]$Port)
    return [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().
        GetActiveTcpListeners().Port -contains $Port
}

function Wait-ForEndpoint {
    param(
        [string]$Uri,
        [string]$Name,
        [System.Diagnostics.Process]$Process
    )

    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        if ($null -ne $Process -and $Process.HasExited) {
            throw "$Name exited before it became ready."
        }
        try {
            Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "$Name did not become ready within 30 seconds."
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Pinned Python is missing. Run 'corepack pnpm@11.9.0 bootstrap' first."
}
if (Test-LocalPort -Port 3000) {
    throw "Port 3000 is already in use. Stop the older Hearsay web process before starting another."
}

$env:PYTHONPATH = "apps/api/src;.venv/Lib/site-packages"
$env:HEARSAY_WEB_ORIGIN = "http://localhost:3000"
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"
# Local gameplay must remain available when the configured CockroachDB cluster
# is offline. Database proof and deployment workflows set their own backend.
$env:HEARSAY_PERSISTENCE_BACKEND = "memory"

try {
    if (Test-LocalPort -Port 8000) {
        Wait-ForEndpoint -Uri "http://127.0.0.1:8000/health" -Name "existing API" -Process $null
        Write-Host "Reusing the existing healthy API on port 8000."
    } else {
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
                "8000"
            ) `
            -WorkingDirectory $repo `
            -WindowStyle Hidden `
            -PassThru
        Wait-ForEndpoint -Uri "http://127.0.0.1:8000/health" -Name "API" -Process $api
    }

    # Webpack is used deliberately for the local editing server: it is already
    # covered by the browser harness and avoids the workspace-wide Turbopack
    # watcher getting stuck on the large licensed source-asset directory.
    $web = Start-Process -FilePath $node `
        -ArgumentList @(
            "apps/web/node_modules/next/dist/bin/next",
            "dev",
            "apps/web",
            "--webpack",
            "-p",
            "3000"
        ) `
        -WorkingDirectory $repo `
        -WindowStyle Hidden `
        -PassThru
    Wait-ForEndpoint -Uri "http://127.0.0.1:3000" -Name "web server" -Process $web

    # The dev controls are useful to developers but cover the game's HUD and
    # can retain a stale "Compiling" state. Keep them out of the play surface.
    Invoke-WebRequest `
        -Uri "http://127.0.0.1:3000/__nextjs_disable_dev_indicator" `
        -Method Post `
        -UseBasicParsing `
        -TimeoutSec 3 | Out-Null

    Write-Host "Greyhaven is ready at http://localhost:3000"
    Write-Host "Press Ctrl+C to stop the web server and any API started by this command."
    Wait-Process -Id $web.Id
} finally {
    foreach ($server in @($web, $api)) {
        if ($null -ne $server -and -not $server.HasExited) {
            Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
            $server.WaitForExit(5000) | Out-Null
        }
    }
}
