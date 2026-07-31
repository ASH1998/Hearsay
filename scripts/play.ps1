$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$python = Join-Path $repo "tools/python/cpython-3.12.13-windows-x86_64-none/python.exe"
$node = (Get-Command node.exe -ErrorAction Stop).Source
$corepack = (Get-Command corepack.cmd -ErrorAction Stop).Source
$api = $null
$web = $null
$build = $null

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
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"

try {
    Write-Host "Preparing the production gameplay build (60 second limit)..."
    $build = Start-Process -FilePath $corepack `
        -ArgumentList @(
            "pnpm@11.9.0",
            "--filter",
            "@hearsay/web",
            "build"
        ) `
        -WorkingDirectory $repo `
        -WindowStyle Hidden `
        -PassThru
    if (-not $build.WaitForExit(60000)) {
        Stop-Process -Id $build.Id -Force -ErrorAction SilentlyContinue
        throw "The gameplay build exceeded 60 seconds and was stopped."
    }
    if ($build.ExitCode -ne 0) {
        throw "The gameplay build failed with exit code $($build.ExitCode)."
    }

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

    $web = Start-Process -FilePath $node `
        -ArgumentList @(
            "apps/web/node_modules/next/dist/bin/next",
            "start",
            "apps/web",
            "-p",
            "3000"
        ) `
        -WorkingDirectory $repo `
        -WindowStyle Hidden `
        -PassThru
    Wait-ForEndpoint -Uri "http://127.0.0.1:3000" -Name "gameplay server" -Process $web

    Write-Host "Greyhaven is ready at http://localhost:3000"
    Write-Host "Press Ctrl+C to stop the web server and any API started by this command."
    Wait-Process -Id $web.Id
} finally {
    foreach ($server in @($web, $api, $build)) {
        if ($null -ne $server -and -not $server.HasExited) {
            Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
            $server.WaitForExit(5000) | Out-Null
        }
    }
}
