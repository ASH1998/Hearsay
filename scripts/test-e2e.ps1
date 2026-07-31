param(
    [switch]$Release,
    [ValidatePattern("^e2e[/\\][A-Za-z0-9._-]+\.spec\.ts$")]
    [string]$Spec = "",
    [ValidateRange(1024, 65535)]
    [int]$WebPort = 3200,
    [ValidateRange(1024, 65535)]
    [int]$ApiPort = 8200
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$nextEnvPath = Join-Path $repo "apps/web/next-env.d.ts"
$nextEnvOriginal = [System.IO.File]::ReadAllText($nextEnvPath)

$qaDirectory = Join-Path $repo ".qa"
New-Item -ItemType Directory -Force -Path $qaDirectory | Out-Null

$apiStdout = Join-Path $qaDirectory "release-api.stdout.log"
$apiStderr = Join-Path $qaDirectory "release-api.stderr.log"
$webStdout = Join-Path $qaDirectory "release-web.stdout.log"
$webStderr = Join-Path $qaDirectory "release-web.stderr.log"

$python = Join-Path $repo "tools/python/cpython-3.12.13-windows-x86_64-none/python.exe"
$node = (Get-Command node.exe -ErrorAction Stop).Source

if (-not (Test-Path -LiteralPath $python)) {
    throw "Pinned Python runtime is missing. Run 'corepack pnpm@11.9.0 bootstrap' first."
}

$env:PYTHONPATH = "apps/api/src;.venv/Lib/site-packages"
$env:HEARSAY_EMBEDDING_PROVIDER = "fallback"
$env:HEARSAY_ENV = "test"
$env:HEARSAY_LLM_PROVIDER = "fallback"
$env:HEARSAY_PERSISTENCE_BACKEND = "memory"
$env:HEARSAY_WEB_ORIGIN = "http://localhost:$WebPort"
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:$ApiPort"
$env:HEARSAY_E2E_WEB_PORT = "$WebPort"
$env:HEARSAY_E2E_API_PORT = "$ApiPort"
$env:HEARSAY_E2E_EXTERNAL_SERVERS = "1"
$env:HEARSAY_NEXT_DIST_DIR = ".next-e2e"

function Wait-ForEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Uri,
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process
    )

    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            throw "$Name exited before it became ready."
        }

        try {
            Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }

    throw "$Name did not become ready within 60 seconds."
}

$api = $null
$web = $null
$testExitCode = 1

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
        -RedirectStandardOutput $apiStdout `
        -RedirectStandardError $apiStderr `
        -PassThru

    Wait-ForEndpoint -Uri "http://127.0.0.1:$ApiPort/health" -Name "API server" -Process $api

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
        -RedirectStandardOutput $webStdout `
        -RedirectStandardError $webStderr `
        -PassThru

    Wait-ForEndpoint -Uri "http://127.0.0.1:$WebPort" -Name "web server" -Process $web

    if ($Spec) {
        & "node_modules/.bin/playwright.cmd" test $Spec
    } elseif ($Release) {
        & "node_modules/.bin/playwright.cmd" test e2e/first-playthrough.spec.ts
    } else {
        & "node_modules/.bin/playwright.cmd" test
    }
    $testExitCode = $LASTEXITCODE
} finally {
    foreach ($server in @($web, $api)) {
        if ($null -ne $server -and -not $server.HasExited) {
            Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
            $server.WaitForExit(5000) | Out-Null
        }
    }
    Start-Sleep -Milliseconds 250
    [System.IO.File]::WriteAllText(
        $nextEnvPath,
        $nextEnvOriginal,
        [System.Text.UTF8Encoding]::new($false)
    )
}

exit $testExitCode
