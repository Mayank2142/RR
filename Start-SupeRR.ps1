param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$rrWorkspace = Split-Path -Parent $PSCommandPath
$rrLogs = Join-Path $rrWorkspace 'output\logs'
New-Item -ItemType Directory -Path $rrLogs -Force | Out-Null

function Test-RRPort([int]$Port) {
    $rrClient = [System.Net.Sockets.TcpClient]::new()
    try {
        $rrConnection = $rrClient.ConnectAsync('127.0.0.1', $Port)
        return $rrConnection.Wait(500) -and $rrClient.Connected
    } catch { return $false } finally { $rrClient.Dispose() }
}

if (-not (Test-RRPort 8000)) {
    $rrPython = (Get-Command python).Source
    Start-Process -FilePath $rrPython -ArgumentList @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $rrWorkspace -WindowStyle Hidden -RedirectStandardOutput (Join-Path $rrLogs 'api.log') -RedirectStandardError (Join-Path $rrLogs 'api-error.log')
}
if (-not (Test-RRPort 5173)) {
    $rrNode = (Get-Command node).Source
    $rrVite = Join-Path $rrWorkspace 'node_modules\vite\bin\vite.js'
    $rrConfig = Join-Path $rrWorkspace 'frontend\vite.config.ts'
    if (-not (Test-Path -LiteralPath $rrVite)) { throw 'Run npm ci in this workspace first.' }
    Start-Process -FilePath $rrNode -ArgumentList @(('"' + $rrVite + '"'),'--config',('"' + $rrConfig + '"')) -WorkingDirectory $rrWorkspace -WindowStyle Hidden -RedirectStandardOutput (Join-Path $rrLogs 'dashboard.log') -RedirectStandardError (Join-Path $rrLogs 'dashboard-error.log')
}
Write-Output 'SupeRR dashboard: http://127.0.0.1:5173/'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173/' -WindowStyle Hidden }
