param(
    [ValidateSet('start', 'stop')] [string]$Action = 'start',
    [string]$PgBin = 'C:\Program Files\PostgreSQL\18\bin'
)
$ErrorActionPreference = 'Stop'
$backendDir = Split-Path $PSScriptRoot -Parent
$localDir = Join-Path $backendDir '.local'
$dataDir = Join-Path $localDir 'postgres'
$envFile = Join-Path $backendDir '.env'
$pgCtl = Join-Path $PgBin 'pg_ctl.exe'
if (-not (Test-Path $pgCtl)) { throw 'PostgreSQL binaries not found. Supply -PgBin.' }
if ($Action -eq 'stop') {
    & $pgCtl -D $dataDir -m fast -w stop
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop the project database.' }
    exit
}
if (-not (Test-Path (Join-Path $dataDir 'PG_VERSION'))) {
    if (Test-Path $envFile) { throw 'backend/.env already exists. Preserve it and use your configured database, or move it aside explicitly.' }
    New-Item -ItemType Directory -Force -Path $localDir | Out-Null
    $dbPassword = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $passwordFile = Join-Path $localDir 'init-password'
    try {
        Set-Content -LiteralPath $passwordFile -Value $dbPassword -Encoding ascii
        & (Join-Path $PgBin 'initdb.exe') -D $dataDir -U slotgrab --auth=scram-sha-256 --encoding=UTF8 --locale=C --pwfile=$passwordFile
        if ($LASTEXITCODE -ne 0) { throw 'initdb failed.' }
        Set-Content -LiteralPath $envFile -Value "DATABASE_URL=postgresql+psycopg://slotgrab:$dbPassword@127.0.0.1:55432/slotgrab" -Encoding ascii
    } finally {
        if (Test-Path $passwordFile) { Remove-Item -LiteralPath $passwordFile }
    }
}
& $pgCtl -D $dataDir status *> $null
if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D $dataDir -l (Join-Path $localDir 'postgres.log') -o '-h 127.0.0.1 -p 55432' -w start
    if ($LASTEXITCODE -ne 0) { throw 'Database did not start. Check backend/.local/postgres.log; port 55432 must be free.' }
}
Write-Output 'Project PostgreSQL is on 127.0.0.1:55432. Run python -m app.create_database, then python -m app.init_db.'
