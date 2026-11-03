param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("backend", "frontend", "tunnel", "all")]
    [string]$Service
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$urlFile = Join-Path $env:TEMP "spendsense-tunnel-url.txt"

function Get-PortProcess([int]$Port) {
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $connection) {
        return $null
    }
    return Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)"
}

function Get-ApiAuthStatus {
    try {
        return Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/auth/status" -TimeoutSec 2
    } catch {
        return $null
    }
}

function Test-ApiDatabase {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/health" -TimeoutSec 2
        return $health.status -eq "ok" -and $health.database -eq "connected"
    } catch {
        return $false
    }
}

function Stop-VerifiedSpendSenseProcess([int]$Port, [string]$Component) {
    $process = Get-PortProcess $Port
    if (-not $process) {
        return
    }

    $command = [string]$process.CommandLine
    $expected = $false
    if ($Component -eq "backend") {
        $expectedPython = [IO.Path]::GetFullPath($python)
        $expected = $command.StartsWith(
            ('"' + $expectedPython + '"'),
            [StringComparison]::OrdinalIgnoreCase
        ) -and
            $command.Contains("uvicorn") -and $command.Contains("--port 8002")
    } else {
        $expected = $process.Name -eq "node.exe" -and
            $command.IndexOf((Join-Path $root "frontend"), [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
            $command.Contains("vite") -and $command.Contains("--port 5174")
    }

    if (-not $expected) {
        throw "Port $Port is occupied by a process that is not the expected SpendSense $Component. Stop it yourself or choose another port."
    }

    Stop-Process -Id $process.ProcessId -ErrorAction Stop
    $deadline = (Get-Date).AddSeconds(10)
    do {
        Start-Sleep -Milliseconds 250
        if (-not (Get-PortProcess $Port)) {
            return
        }
    } while ((Get-Date) -lt $deadline)
    throw "SpendSense $Component did not release port $Port."
}

function Ensure-PasswordProtection {
    if (-not (Test-Path $python)) {
        throw "Backend virtual environment not found. Run .\backend\setup.ps1 or see the README installation steps."
    }
    Push-Location $backend
    try {
        & $python "setup_public_access.py"
        if ($LASTEXITCODE -ne 0) {
            throw "Could not configure SpendSense password protection."
        }
    } finally {
        Pop-Location
    }
}

function Start-BackendService {
    $auth = Get-ApiAuthStatus
    if ($auth -and $auth.required -and (Test-ApiDatabase)) {
        Write-Host "SpendSense API is already running with password protection and MySQL connected."
        return
    }

    Stop-VerifiedSpendSenseProcess 8002 "backend"
    Ensure-PasswordProtection
    $env:APP_ENV = "local_tunnel"
    $env:APP_AUTH_REQUIRED = "true"
    Push-Location $backend
    try {
        & $python -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8002
        if ($LASTEXITCODE -ne 0) {
            throw "FastAPI stopped with exit code $LASTEXITCODE."
        }
    } finally {
        Pop-Location
    }
}

function Test-Frontend {
    $status = & curl.exe -sS -o NUL -w "%{http_code}" --max-time 2 "http://127.0.0.1:5174/" 2>$null
    return $LASTEXITCODE -eq 0 -and "$status".Trim() -eq "200"
}

function Start-FrontendService {
    $auth = Get-ApiAuthStatus
    if (-not $auth -or -not $auth.required -or -not (Test-ApiDatabase)) {
        throw "The password-protected API is not running. Start the backend first or use start_all.bat."
    }
    if (Get-PortProcess 5174) {
        Stop-VerifiedSpendSenseProcess 5174 "frontend"
    }
    $env:VITE_API_URL = "/api"
    Push-Location (Join-Path $root "frontend")
    try {
        & npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort
        if ($LASTEXITCODE -ne 0) {
            throw "Vite stopped with exit code $LASTEXITCODE."
        }
    } finally {
        Pop-Location
    }
}

function Get-Cloudflared {
    $command = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $paths = @(
        (Join-Path $env:ProgramFiles "cloudflared\cloudflared.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "cloudflared\cloudflared.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\cloudflared.exe")
    )
    foreach ($path in $paths) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }
    return $null
}

function Start-TunnelService {
    $auth = Get-ApiAuthStatus
    if (-not (Test-Frontend) -or -not $auth -or -not $auth.required -or -not (Test-ApiDatabase)) {
        throw "Start the password-protected backend and frontend before exposing the app."
    }
    $cloudflared = Get-Cloudflared
    if (-not $cloudflared) {
        throw "cloudflared is not installed. Install Cloudflare Tunnel with winget, then run this script again."
    }
    $existing = Get-CimInstance Win32_Process |
        Where-Object { $_.Name -match "^cloudflared(\.exe)?$" -and $_.CommandLine -match "tunnel\s+--url\s+http://127\.0\.0\.1:5174" } |
        Select-Object -First 1
    if ($existing) {
        if (Test-Path $urlFile) {
            Write-Host "An existing SpendSense tunnel is running: $(Get-Content $urlFile -Raw)"
        } else {
            Write-Host "A SpendSense tunnel is already running. Check its window for the public URL."
        }
        return
    }

    Remove-Item $urlFile -Force -ErrorAction SilentlyContinue
    Write-Host "Starting a temporary public HTTPS tunnel. Keep this window open."
    Write-Host "The app requires the private SpendSense password; share that password separately and privately."
    & $cloudflared tunnel --url "http://127.0.0.1:5174" --no-autoupdate 2>&1 |
        ForEach-Object {
            $line = "$_"
            Write-Host $line
            if ($line -match "https://[a-z0-9-]+\.trycloudflare\.com") {
                $publicUrl = $Matches[0]
                Set-Content -Path $urlFile -Value $publicUrl -NoNewline
                Write-Host ""
                Write-Host "SpendSense sharing URL: $publicUrl"
            }
        }
    if ($LASTEXITCODE -ne 0) {
        throw "cloudflared exited with code $LASTEXITCODE."
    }
}

function Start-AllServices {
    if (-not (Get-Cloudflared)) {
        throw "cloudflared is not installed. Install Cloudflare Tunnel first."
    }
    Ensure-PasswordProtection

    $launch = Join-Path $PSScriptRoot "start_spendsense.ps1"
    $backendAuth = Get-ApiAuthStatus
    if (-not $backendAuth -or -not $backendAuth.required) {
        Start-Process -FilePath "powershell.exe" -WorkingDirectory $root -ArgumentList @(
            "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$launch`"", "-Service", "backend"
        ) | Out-Null
        $deadline = (Get-Date).AddSeconds(90)
        do {
            Start-Sleep -Seconds 2
            $backendAuth = Get-ApiAuthStatus
            if ($backendAuth -and $backendAuth.required) {
                break
            }
        } while ((Get-Date) -lt $deadline)
        if (-not $backendAuth -or -not $backendAuth.required) {
            throw "The backend did not become ready. Check the SpendSense Backend window."
        }
    }

    Start-Process -FilePath "powershell.exe" -WorkingDirectory $root -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$launch`"", "-Service", "frontend"
    ) | Out-Null
    $deadline = (Get-Date).AddSeconds(60)
    do {
        Start-Sleep -Seconds 2
    } until ((Test-Frontend) -or (Get-Date) -ge $deadline)
    if (-not (Test-Frontend)) {
        throw "The frontend did not become ready. Check the SpendSense Frontend window."
    }

    Write-Host "Local SpendSense: http://127.0.0.1:5174/"
    Write-Host "Local API health: http://127.0.0.1:8002/api/health"
    Write-Host "API documentation: http://127.0.0.1:8002/docs"
    Write-Host "MySQL remains local and is not exposed."
    Write-Host "A new temporary public URL will appear in the SpendSense Tunnel window."
    Start-Process -FilePath "powershell.exe" -WorkingDirectory $root -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$launch`"", "-Service", "tunnel"
    ) | Out-Null
}

switch ($Service) {
    "backend" { Start-BackendService }
    "frontend" { Start-FrontendService }
    "tunnel" { Start-TunnelService }
    "all" { Start-AllServices }
}
