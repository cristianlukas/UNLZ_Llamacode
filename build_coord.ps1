<#
  build_coord.ps1  —  Encolamiento inteligente de builds para sesiones paralelas.

  Varias IAs/CI pueden lanzar build_auto.bat / tests.bat a la vez. Este
  coordinador serializa por "lane" (build vs tests, dirs separados) usando un
  lock atomico (mkdir). Resuelve la carrera con tres desenlaces:

    OWNER  (exit 0)  -> tomaste el lock; compila vos y despues llama -Action release.
    REUSE  (exit 10) -> ya habia un build EN CURSO con el mismo fingerprint de
                        fuente y termino OK; adoptas su resultado, no recompilas.
    error  (exit 1)  -> timeout / fallo.
    Ademas: si el build compartido termino en FALLO, se devuelve OWNER para que
    reintentes desde cero (no querés adoptar un rojo silenciosamente).

  El "fingerprint" es un hash del contenido de src/ qml/ tests/ CMakeLists.txt con
  los triples semver (X.Y.Z) neutralizados, para que el auto-bump de version NO
  cuente como cambio de fuente (si contara, cada sharer creería ver un árbol
  distinto y recompilaría al pedo).

  Locks muertos se roban de inmediato usando la identidad del proceso real que
  ejecuta el .bat (PID + hora de creación, para resistir reutilización de PID).
  No usa procesos guardianes ni sleeps como señal de vida.

  Uso:
    powershell ... build_coord.ps1 -Lane build  -Action acquire [-TimeoutSec 1800]
    powershell ... build_coord.ps1 -Lane build  -Action release -Result OK|FAIL
    powershell ... build_coord.ps1 -Lane tests -Action fingerprint   (debug)
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('build','tests')] [string]$Lane,
    [Parameter(Mandatory=$true)][ValidateSet('acquire','release','fingerprint','status')] [string]$Action,
    [ValidateSet('OK','FAIL')] [string]$Result = 'OK',
    [int]$OwnerPid = 0,
    [int]$TimeoutSec = 1800,
    [int]$StaleSec   = 3600
)

$ErrorActionPreference = 'Stop'
$root     = Split-Path -Parent $MyInvocation.MyCommand.Path
$lockRoot = Join-Path $root '.buildlock'
$lockDir  = Join-Path $lockRoot ("{0}.lock" -f $Lane)      # mkdir atomico = el lock
$ownerJson= Join-Path $lockDir 'owner.json'
$resultDir= Join-Path $lockRoot 'results'

function Log([string]$m) { Write-Host ("[coord:{0}] {1}" -f $Lane, $m) }

# --- fingerprint de la fuente (semver neutralizado) --------------------------
function Get-Fingerprint {
    $targets = @('src','qml','tests') | ForEach-Object { Join-Path $root $_ }
    $files = @()
    foreach ($t in $targets) {
        if (Test-Path $t) {
            $files += Get-ChildItem -Path $t -Recurse -File -ErrorAction SilentlyContinue
        }
    }
    $cmake = Join-Path $root 'CMakeLists.txt'
    if (Test-Path $cmake) { $files += Get-Item $cmake }

    $sb = [System.Text.StringBuilder]::new()
    foreach ($f in ($files | Sort-Object FullName)) {
        try {
            $txt = [IO.File]::ReadAllText($f.FullName)
        } catch { continue }
        # Neutraliza triples semver (X.Y.Z) para que el bump de version no cuente.
        $txt = [regex]::Replace($txt, '\d+\.\d+\.\d+', 'V')
        $rel = $f.FullName.Substring($root.Length)
        [void]$sb.Append($rel).Append("|").Append($txt).Append("`n")
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes($sb.ToString())
    $sha   = [Security.Cryptography.SHA256]::Create()
    $hash  = $sha.ComputeHash($bytes)
    return ([BitConverter]::ToString($hash) -replace '-','').Substring(0,32)
}

function Test-Alive([int]$procId) {
    if (-not $procId) { return $false }
    try { return [bool](Get-Process -Id $procId -ErrorAction Stop) } catch { return $false }
}

function Get-ProcessIdentity([int]$procId) {
    if (-not $procId) { return $null }
    try {
        $p = Get-Process -Id $procId -ErrorAction Stop
        return [pscustomobject]@{
            pid = $p.Id
            startedUtc = $p.StartTime.ToUniversalTime().ToString('o')
        }
    } catch { return $null }
}

function Test-OwnerAlive($owner) {
    if (-not $owner -or -not $owner.ownerPid -or -not $owner.ownerStartedUtc) {
        return $false # formato legacy/guardían: stale por diseño
    }
    $live = Get-ProcessIdentity ([int]$owner.ownerPid)
    return $live -and $live.startedUtc -eq [string]$owner.ownerStartedUtc
}

function Read-Owner {
    if (-not (Test-Path $ownerJson)) { return $null }
    try { return Get-Content -Raw $ownerJson | ConvertFrom-Json } catch { return $null }
}

function Remove-Lock {
    try { Remove-Item -Recurse -Force $lockDir -ErrorAction Stop } catch {}
}

function Result-Path([string]$fp) { Join-Path $resultDir ("{0}.{1}.txt" -f $Lane, $fp) }

# =============================================================================
if ($Action -eq 'fingerprint') {
    Get-Fingerprint
    exit 0
}

if ($Action -eq 'status') {
    $owner = Read-Owner
    if (-not $owner) { Log 'FREE'; exit 0 }
    $alive = Test-OwnerAlive $owner
    Log ("{0} owner={1} fingerprint={2} started={3}" -f `
         $(if ($alive) {'BUSY'} else {'STALE'}), $owner.ownerPid,
         $owner.fingerprint, $owner.startedUtc)
    exit $(if ($alive) {10} else {11})
}

New-Item -ItemType Directory -Force -Path $lockRoot  | Out-Null
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null

# --- release -----------------------------------------------------------------
if ($Action -eq 'release') {
    $me = Read-Owner
    if (-not $me) { Log 'release ignorado: lock inexistente'; exit 0 }
    if (-not $OwnerPid -or [int]$me.ownerPid -ne $OwnerPid) {
        Log ("release rechazado: caller={0}, owner={1}" -f $OwnerPid, $me.ownerPid)
        exit 1
    }
    if ($me -and $me.fingerprint) {
        # Publica el resultado para que los sharers en espera lo adopten.
        $rp = Result-Path $me.fingerprint
        try {
            "{0}|{1}|{2}" -f $Result, (Get-Date).ToUniversalTime().ToString('o'), $PID |
                Set-Content -Path $rp -Encoding ASCII
        } catch {}
    }
    Remove-Lock
    Log ("released ({0})" -f $Result)
    exit 0
}

# --- acquire -----------------------------------------------------------------
$myFp   = Get-Fingerprint
$myOwner = Get-ProcessIdentity $OwnerPid
if (-not $myOwner) { Log ("OwnerPid inválido o muerto: {0}" -f $OwnerPid); exit 1 }
$deadline = (Get-Date).AddSeconds($TimeoutSec)
Log ("fingerprint {0}" -f $myFp)

while ($true) {
    if ((Get-Date) -gt $deadline) { Log 'timeout esperando el lock'; exit 1 }

    # Intento tomar el lock (mkdir atomico).
    $got = $false
    try { New-Item -ItemType Directory -Path $lockDir -ErrorAction Stop | Out-Null; $got = $true }
    catch { $got = $false }

    if ($got) {
        # Borro cualquier resultado viejo de esta fuente ANTES de publicar owner.json,
        # asi un sharer que entre despues no adopta un resultado stale de una corrida
        # anterior en vez de esperar la mia.
        Remove-Item -Force (Result-Path $myFp) -ErrorAction SilentlyContinue
        $owner = [ordered]@{
            ownerPid    = $myOwner.pid
            ownerStartedUtc = $myOwner.startedUtc
            host        = $env:COMPUTERNAME
            fingerprint = $myFp
            phase       = 'building'
            startedUtc  = (Get-Date).ToUniversalTime().ToString('o')
        }
        ($owner | ConvertTo-Json -Compress) | Set-Content -Path $ownerJson -Encoding ASCII
        Log ('OWNER (lock tomado, pid={0}) -> compilando' -f $myOwner.pid)
        exit 0
    }

    # Lock ocupado: inspecciono al owner.
    $owner = Read-Owner
    if (-not $owner) {
        # Lock a medio escribir; espero un toque y reintento.
        Start-Sleep -Milliseconds 400
        continue
    }

    # Lock muerto o vencido -> lo robo.
    $started = $null
    try { $started = [datetime]::Parse($owner.startedUtc).ToUniversalTime() } catch {}
    $expired = $started -and ((Get-Date).ToUniversalTime() - $started).TotalSeconds -gt $StaleSec
    $ownerDead = -not (Test-OwnerAlive $owner)
    if ($ownerDead -or $expired) {
        Log ("robando lock stale (owner={0}, ownerDead={1}, expired={2})" `
             -f $owner.ownerPid, $ownerDead, $expired)
        Remove-Lock
        Start-Sleep -Milliseconds 200
        continue
    }

    if ($owner.fingerprint -eq $myFp) {
        # ── SHARE: hay un build en curso con la MISMA fuente. Espero su resultado.
        Log ("build en curso con misma fuente (pid={0}); esperando para reusar..." -f $owner.pid)
        $rp = Result-Path $myFp
        while ($true) {
            if ((Get-Date) -gt $deadline) { Log 'timeout esperando build compartido'; exit 1 }
            if (Test-Path $rp) {
                $line = (Get-Content -Raw $rp).Trim()
                if ($line -like 'OK|*') { Log 'REUSE: build compartido OK'; exit 10 }
                else { Log 'build compartido FALLO -> reintento propio'; Remove-Item -Force $rp -ErrorAction SilentlyContinue; break }
            }
            # El owner libero sin dejar resultado (crash): reintento acquire.
            if (-not (Test-Path $lockDir)) { Log 'owner libero sin resultado -> reintento'; break }
            $cur = Read-Owner
            if ($cur -and $cur.fingerprint -ne $myFp) { Log 'owner cambio de fuente -> reintento'; break }
            Start-Sleep -Seconds 2
        }
        continue
    }
    else {
        # ── QUEUE: build en curso con OTRA fuente. Espero mi turno.
        Log ("build en curso con OTRA fuente (pid={0}); en cola..." -f $owner.pid)
        Start-Sleep -Seconds 2
        continue
    }
}
