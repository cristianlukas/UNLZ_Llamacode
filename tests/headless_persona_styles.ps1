param(
    [string]$Exe = ".\build\Debug\LlamaCode.exe",
    [int]$Port = 8896
)

$ErrorActionPreference = "Stop"
$exePath = (Resolve-Path $Exe).Path
$profileDir = Join-Path ([System.IO.Path]::GetTempPath()) ("llamacode-persona-" + [guid]::NewGuid())
$oldPort = $env:LLAMACODE_CONTROL_PORT
$oldProfiles = $env:LLAMACODE_PROFILES_DIR
$proc = $null

function Invoke-Control([string]$Target, [string]$Method, [object[]]$Args = @()) {
    $body = @{ method = $Method; args = $Args } | ConvertTo-Json -Depth 20 -Compress
    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/invoke?target=$Target" `
        -Method Post -ContentType "application/json" -Body $body
}

try {
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
    $env:LLAMACODE_CONTROL_PORT = [string]$Port
    $env:LLAMACODE_PROFILES_DIR = $profileDir
    $proc = Start-Process -FilePath $exePath -ArgumentList "--agent-daemon" `
        -WindowStyle Hidden -PassThru

    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$Port/health"
            if ($health) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $ready) { throw "ControlApi no estuvo disponible en el puerto $Port" }

    $styleId = (Invoke-Control "profileManager" "addPersonaStyleProfile" @(
        "Headless style", "writing-style")).result
    if ([string]::IsNullOrWhiteSpace($styleId)) { throw "No se creó el perfil de estilo" }

    $updated = Invoke-Control "profileManager" "updatePersonaStyleProfile" @(@{
        id = $styleId
        styleCard = "voz clara y frases medias"
        description = "perfil de smoke"
        examples = @("bosque y río", "compilador y código")
    })
    if (-not $updated.result) { throw "No se actualizó el perfil de estilo" }

    $agentId = (Invoke-Control "profileManager" "addAgentProfile" @("Headless agent")).result
    if ([string]::IsNullOrWhiteSpace($agentId)) { throw "No se creó el perfil de agente" }
    $agentUpdated = Invoke-Control "profileManager" "updateAgentProfile" @(@{
        id = $agentId
        styleProfileIds = @($styleId)
        styleExampleLimit = 1
        styleContextLimit = 2000
    })
    if (-not $agentUpdated.result) { throw "No se asoció el estilo al agente" }

    $preview = (Invoke-Control "profileManager" "previewPersonaStylePrompt" @(
        $agentId, "necesito código del compilador")).result
    if ($preview -notmatch "compilador y código") { throw "El preview no priorizó el ejemplo relevante" }
    if ($preview -match "bosque y río") { throw "El preview excedió el límite de ejemplos" }

    $exported = (Invoke-Control "profileManager" "exportPersonaStyleProfile" @($styleId)).result
    if ($exported -notmatch "Headless style") { throw "La exportación no contiene el perfil" }
    $imported = (Invoke-Control "profileManager" "importPersonaStyleProfile" @($exported)).result
    if ([string]::IsNullOrWhiteSpace($imported) -or $imported -eq $styleId) {
        throw "La importación no generó un ID nuevo"
    }

    Write-Output "PASS: ControlApi persona/style CRUD, asociación, ranking, preview e import/export"
} finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        $proc.WaitForExit()
    }
    if ($null -eq $oldPort) { Remove-Item Env:LLAMACODE_CONTROL_PORT -ErrorAction SilentlyContinue }
    else { $env:LLAMACODE_CONTROL_PORT = $oldPort }
    if ($null -eq $oldProfiles) { Remove-Item Env:LLAMACODE_PROFILES_DIR -ErrorAction SilentlyContinue }
    else { $env:LLAMACODE_PROFILES_DIR = $oldProfiles }
    if (Test-Path $profileDir) { Remove-Item -LiteralPath $profileDir -Recurse -Force }
}
