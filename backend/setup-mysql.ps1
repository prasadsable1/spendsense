param(
    [string]$MySQLHost = "127.0.0.1",
    [int]$MySQLPort = 3306,
    [string]$DatabaseName = "spendsense",
    [string]$DatabaseUser = "spendsense_app"
)

$ErrorActionPreference = "Stop"

if ($MySQLHost -notmatch '^[A-Za-z0-9.:-]+$') {
    throw "Use a MySQL host name or IP address."
}
if ($MySQLPort -lt 1 -or $MySQLPort -gt 65535) {
    throw "MySQLPort must be between 1 and 65535."
}
if ($DatabaseName -notmatch '^[A-Za-z0-9_]+$' -or $DatabaseUser -notmatch '^[A-Za-z0-9_]+$') {
    throw "DatabaseName and DatabaseUser may only contain letters, numbers, and underscores."
}

$mysql = Get-Command mysql -ErrorAction SilentlyContinue
if (-not $mysql) {
    throw "The MySQL command-line client was not found. Add mysql.exe to PATH, then retry."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $PSScriptRoot ".env"
if (Test-Path $envPath) {
    throw "backend\.env already exists. Review it first; this script will not overwrite local configuration."
}

$adminUser = Read-Host "MySQL administrator username"
if ([string]::IsNullOrWhiteSpace($adminUser) -or $adminUser -notmatch '^[A-Za-z0-9_]+$') {
    throw "Enter a MySQL administrator username containing only letters, numbers, and underscores."
}
$adminSecret = Read-Host "MySQL administrator password" -AsSecureString
$adminPassword = [System.Net.NetworkCredential]::new("", $adminSecret).Password

$randomBytes = New-Object byte[] 24
$random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $random.GetBytes($randomBytes)
}
finally {
    $random.Dispose()
}
$applicationPassword = -join ($randomBytes | ForEach-Object { $_.ToString("x2") })
[Array]::Clear($randomBytes, 0, $randomBytes.Length)

$sql = @"
CREATE DATABASE IF NOT EXISTS ``$DatabaseName`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER '$DatabaseUser'@'localhost' IDENTIFIED BY '$applicationPassword';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON ``$DatabaseName``.* TO '$DatabaseUser'@'localhost';
"@

$previousMysqlPassword = $env:MYSQL_PWD
try {
    $env:MYSQL_PWD = $adminPassword

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $mysql.Source
    $startInfo.Arguments = "--protocol=TCP --host=$MySQLHost --port=$MySQLPort --user=$adminUser --batch --skip-column-names"
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Could not start the MySQL command-line client."
    }
    $process.StandardInput.WriteLine($sql)
    $process.StandardInput.Close()
    $mysqlOutput = $process.StandardOutput.ReadToEnd()
    $mysqlError = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "MySQL setup failed. Check the administrator account and privileges. $mysqlError"
    }

    @(
        "DB_HOST=$MySQLHost"
        "DB_PORT=$MySQLPort"
        "DB_USER=$DatabaseUser"
        "DB_PASSWORD=replace_with_a_local_password
        "DB_NAME=$DatabaseName"
        "CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173"
    ) | Set-Content -Path $envPath -Encoding ASCII

    $env:MYSQL_PWD = $applicationPassword
    $mysqlOutput = & $mysql.Source --protocol=TCP "--host=$MySQLHost" "--port=$MySQLPort" "--user=$DatabaseUser" "--database=$DatabaseName" --batch --skip-column-names -e "SELECT VERSION();"
    if ($LASTEXITCODE -ne 0) {
        throw "The generated application account could not connect. Check the MySQL account host settings and retry."
    }

    Write-Host "MySQL application connection verified: $mysqlOutput"
    Write-Host "The database and dedicated application account are ready. Backend startup creates the tables and default categories."
    Write-Host "Local connection settings were saved to backend\.env. Do not share or commit that file."
}
finally {
    if ($null -eq $previousMysqlPassword) {
        Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
    }
    else {
        $env:MYSQL_PWD = $previousMysqlPassword
    }
    $adminPassword = $null
    $applicationPassword = $null
    $adminSecret.Dispose()
}
