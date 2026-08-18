# Barrido A/B de HARNESS: corre el mismo benchmark con dos (o mas) perfiles de
# AGENTE sobre el MISMO launch profile, y compara los resultados agrupados por
# perfil de agente. Es el cierre del ciclo del harness modular: personalizar sin
# medir es adivinar.
#
# Requiere un daemon headless corriendo (ver docs/HEADLESS.md):
#   $env:LLAMACODE_CONTROL_PORT = "8877"
#   Start-Process .\build\Release\LlamaCode.exe -ArgumentList "--agent-daemon"
#
# Uso:
#   powershell -File tools\harness_ab.ps1 -LaunchProfileId <id> `
#       -AgentProfileIds agent-intermedio,agent-minimal `
#       [-CustomBenchmarkId <id>] [-Mode coding] [-Passes 3] [-TimeoutSec 900] `
#       [-Port 8877] [-Out harness-ab.json]
#
# El script NO elige por vos: imprime el informe (medianas de calidad, tiempo,
# tasa de exito y complejidad por perfil, mas los deltas entre pares) y lo deja
# en JSON. Un harness solo es mejor si no baja calidad ni exito.
#
# ASCII puro: Windows PowerShell 5.1 lee un .ps1 sin BOM como ANSI y un caracter
# UTF-8 dentro de un string puede terminarlo (ver CLAUDE.md).

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]   $LaunchProfileId,
    [Parameter(Mandatory = $true)][string[]] $AgentProfileIds,
    [string] $CustomBenchmarkId = "",
    [string] $Mode = "coding",
    [int]    $Passes = 1,
    [int]    $TimeoutSec = 0,
    [int]    $Port = 8877,
    [int]    $PollSeconds = 10,
    [int]    $MaxWaitMinutes = 240,
    [string] $Out = "harness-ab.json"
)

$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:$Port"

# Invocado con -File (CI, cmd, otro script), PowerShell NO separa por comas: la
# lista llega como UN string. Sin esto, '-AgentProfileIds a,b' se interpretaba
# como un unico perfil llamado "a,b" y el script cortaba diciendo que no existe.
$AgentProfileIds = @($AgentProfileIds | ForEach-Object { $_ -split ',' } |
                     ForEach-Object { $_.Trim() } | Where-Object { $_.Length -gt 0 })
if ($AgentProfileIds.Count -lt 1) { throw "Falta -AgentProfileIds." }

function Inv([string]$target, [string]$method, $arguments) {
    $body = @{ method = $method; args = $arguments } | ConvertTo-Json -Depth 12 -Compress
    return Invoke-RestMethod "$base/invoke?target=$target" -Method Post `
        -ContentType "application/json" -Body $body
}
function Prop([string]$target, [string]$name) {
    return (Invoke-RestMethod "$base/prop?target=$target&name=$name").value
}

# El daemon tiene que estar arriba: si no, fallar temprano y claro en vez de
# arrastrar un error de conexion adentro del bucle de polling.
try { Invoke-RestMethod "$base/health" | Out-Null }
catch { throw "No hay daemon headless en $base. Arrancalo con --agent-daemon (docs/HEADLESS.md)." }

# Los perfiles de agente tienen que existir: un id mal escrito correria el
# benchmark con el nivel por defecto y la comparacion seria una mentira.
foreach ($ap in $AgentProfileIds) {
    $spec = Inv "profileManager" "agentProfileSpec" @($ap)
    if (-not $spec.ok) { throw "Perfil de agente inexistente: $ap" }
    $summary = Inv "profileManager" "harnessSpecSummary" @($ap, "")
    $s = $summary.result
    Write-Host ("[{0}] {1} tools, ~{2} tok de schemas" -f $ap, $s.toolCount, $s.approxTokens)
    foreach ($w in $s.warnings) { Write-Host ("  aviso: {0}" -f $w) -ForegroundColor Yellow }
}

function Wait-Benchmark {
    $deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds $PollSeconds
        if (-not (Prop "" "benchmarkRunning")) { return $true }
        $progress = Prop "" "benchmarkProgress"
        if ($progress) { Write-Host ("  {0}" -f $progress) }
    }
    return $false
}

foreach ($ap in $AgentProfileIds) {
    Write-Host "=== Corriendo benchmark con perfil de agente '$ap'" -ForegroundColor Cyan
    if ($CustomBenchmarkId) {
        Inv "" "startCustomBenchmark" @(@($LaunchProfileId), $CustomBenchmarkId, $Passes,
                                       "agent", $TimeoutSec, $ap) | Out-Null
    } else {
        Inv "" "startBenchmark" @(@($LaunchProfileId), $Mode, $Passes,
                                 "agent", $TimeoutSec, $ap) | Out-Null
    }
    if (-not (Wait-Benchmark)) { throw "Timeout esperando el benchmark del perfil '$ap'." }
}

$report = (Inv "" "compareHarnessBenchmarks" @($AgentProfileIds, "")).result
$report | ConvertTo-Json -Depth 12 | Set-Content -Path $Out -Encoding UTF8

Write-Host ""
Write-Host "=== Resultado por perfil de agente" -ForegroundColor Cyan
foreach ($p in $report.profiles) {
    Write-Host ("{0,-24} calidad {1,6:N1}%  exito {2,6:N1}%  tiempo {3,7:N1}s  archivos {4,4:N1}  runs {5}" -f `
        $p.profileName, $p.medianQualityPct, $p.successRatePct, $p.medianElapsedSec,
        $p.medianFilesChanged, $p.runs)
}
Write-Host ""
Write-Host "=== Deltas (candidato vs baseline)" -ForegroundColor Cyan
# Formato con signo explicito: "{n,+6:N1}" NO es valido en .NET (el alineado es
# un entero, no admite '+') y tiraba FormatException justo antes del resumen.
function Signed($v) { return ("{0:+0.0;-0.0;0.0}" -f [double]$v) }
foreach ($c in $report.comparisons) {
    Write-Host ("{0} -> {1}: calidad {2,7} pp  exito {3,7} pp  tiempo {4,7}%  archivos {5,6}" -f `
        $c.baselineProfileId, $c.candidateProfileId, (Signed $c.qualityDeltaPctPoints),
        (Signed $c.successRateDeltaPctPoints), (Signed $c.comparisonTimeChangePct),
        (Signed $c.filesChangedDelta))
}
Write-Host ""
Write-Host "Informe completo: $Out"
Write-Host "Un harness solo es mejor si NO baja calidad ni tasa de exito." -ForegroundColor Yellow
