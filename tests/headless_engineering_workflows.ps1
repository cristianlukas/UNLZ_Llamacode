$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$exe = Join-Path $root "build\Debug\LlamaCode.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "No existe $exe. Ejecutá build.bat Debug NOPAUSE." }
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$listener.Start(); $port = $listener.LocalEndpoint.Port; $listener.Stop()
$profileDir = Join-Path ([IO.Path]::GetTempPath()) ("llamacode-workflow-" + [guid]::NewGuid())
$oldPort = $env:LLAMACODE_CONTROL_PORT; $oldProfiles = $env:LLAMACODE_PROFILES_DIR; $proc = $null
try {
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
    $env:LLAMACODE_CONTROL_PORT = [string]$port; $env:LLAMACODE_PROFILES_DIR = $profileDir
    $proc = Start-Process -FilePath $exe -ArgumentList "--headless" -WindowStyle Hidden -PassThru
    $base = "http://127.0.0.1:$port"; $ready = $false
    # El primer arranque puede cargar catálogos y perfiles antes de abrir
    # ControlApi; el timeout debe cubrir una notebook fría sin modelo.
    for ($i = 0; $i -lt 120; $i++) {
        try { if ((Invoke-RestMethod "$base/health").ok) { $ready = $true; break } }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw "El daemon no respondió en $base" }
    function Invoke-Llama([string]$method, [object[]]$argumentList) {
        $body = @{ method = $method; args = @($argumentList) } | ConvertTo-Json -Depth 20 -Compress
        Invoke-RestMethod "$base/invoke" -Method Post -ContentType "application/json" -Body $body
    }
    $catalog = Invoke-Llama "engineeringWorkflows" @()
    if ($catalog.result.Count -ne 5) { throw "Se esperaban 5 workflows, llegaron $($catalog.result.Count)" }
    $qa = ($catalog.result | Where-Object { $_.id -eq "qa" })
    if ((Invoke-Llama "validateWorkflow" @($qa)).result -ne "") { throw "QA inválido" }
    $taskId = (Invoke-Llama "installEngineeringWorkflow" @("qa")).result
    if ([string]::IsNullOrWhiteSpace($taskId)) { throw "No se instaló qa" }
    $getBody = @{ target = "taskStore"; method = "get"; args = @($taskId) } |
        ConvertTo-Json -Depth 20 -Compress
    $saved = (Invoke-RestMethod "$base/invoke" -Method Post -ContentType "application/json" -Body $getBody).result
    if ($saved.workflow.id -ne "qa") { throw "La Task no conserva workflow qa" }
    if ([string]::IsNullOrWhiteSpace($saved.safetyProfile)) { throw "Falta safetyProfile" }
    Write-Host "OK: catálogo, validación, instalación y persistencia headless"
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    if ($null -eq $oldPort) { Remove-Item Env:LLAMACODE_CONTROL_PORT -ErrorAction SilentlyContinue } else { $env:LLAMACODE_CONTROL_PORT = $oldPort }
    if ($null -eq $oldProfiles) { Remove-Item Env:LLAMACODE_PROFILES_DIR -ErrorAction SilentlyContinue } else { $env:LLAMACODE_PROFILES_DIR = $oldProfiles }
    if (Test-Path -LiteralPath $profileDir) { Remove-Item -LiteralPath $profileDir -Recurse -Force }
}
