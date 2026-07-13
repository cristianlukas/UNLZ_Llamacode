<#
  test_build_coord.ps1 — regresion del encolamiento inteligente (build_coord.ps1).

  No corre en ctest (es infra de build en PS/batch, no C++). Correr a mano:
      powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_build_coord.ps1
  Exit 0 = todo verde.

  Cubre: fingerprint estable, OWNER exclusivo, robo inmediato al morir el dueño,
  rechazo de release ajeno, SHARE/REUSE y lanes independientes.
#>
$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$coord  = Join-Path $root 'build_coord.ps1'
$lock   = Join-Path $root '.buildlock'
$fails  = 0
function Ok($cond,$msg){ if($cond){Write-Host "  PASS $msg"}else{Write-Host "  FAIL $msg" -Foreground Red; $script:fails++} }
function Clean(){ if(Test-Path $lock){ Remove-Item -Recurse -Force $lock -ErrorAction SilentlyContinue } }
Clean

# Corre acquire en background y devuelve el objeto Process (con out redirigido).
function StartAcquire($lane,$out,$timeout=60){
    $of = Join-Path $lock $out
    $rf = "$of.rc"
    New-Item -ItemType Directory -Force -Path $lock | Out-Null
    $cmd = "& '$coord' -Lane $lane -Action acquire -OwnerPid `$PID -TimeoutSec $timeout; Set-Content -Path '$rf' -Value `$LASTEXITCODE"
    return Start-Process powershell -PassThru -WindowStyle Hidden -RedirectStandardOutput $of `
        -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',$cmd
}
# Espera al proceso y lee el exit code que dejo en su archivo .rc.
function ReadRC($proc,$out){
    $proc.WaitForExit(30000) | Out-Null
    $rf = (Join-Path $lock $out) + '.rc'
    for($i=0;$i -lt 20 -and -not (Test-Path $rf);$i++){ Start-Sleep -Milliseconds 100 }
    if(Test-Path $rf){ return [int]((Get-Content -Raw $rf).Trim()) } else { return $null }
}
function Release($lane,$res='OK'){ & $coord -Lane $lane -Action release -Result $res -OwnerPid $PID | Out-Null }

Write-Host "== test 1: fingerprint estable ante bump semver =="
$fp = (& $coord -Lane build -Action fingerprint).Trim()
Ok ($fp.Length -eq 32) "fingerprint 32 chars ($fp)"
# Simula bump: escribo un archivo temporal en tests/ con un triple semver, recomputo.
$tmp = Join-Path $root 'tests\_fp_probe.tmp'
'version 1.2.3'  | Set-Content $tmp -Encoding ASCII
$fpA = (& $coord -Lane build -Action fingerprint).Trim()
'version 9.9.9'  | Set-Content $tmp -Encoding ASCII
$fpB = (& $coord -Lane build -Action fingerprint).Trim()
Remove-Item $tmp -Force
Ok ($fpA -eq $fpB) "solo cambia un triple semver -> mismo fingerprint (bump no invalida)"

Write-Host "== test 2: OWNER exclusivo + REUSE (share) =="
Clean
& $coord -Lane build -Action acquire -OwnerPid $PID | Out-Null
Ok (Test-Path (Join-Path $lock 'build.lock')) "lock creado por A"
$b = StartAcquire 'build' '_b.txt' 60                # B: mismo fp -> debe esperar
Start-Sleep -Seconds 3
Ok (-not $b.HasExited) "B espera (no roba el lock de A vivo)"
Release 'build' 'OK'                                 # A libera OK
$brc  = ReadRC $b '_b.txt'
$bout = Get-Content -Raw (Join-Path $lock '_b.txt')
Ok ($brc -eq 10) "B exit 10 (REUSE); actual=$brc"
Ok ($bout -match 'REUSE') "B tomo el path REUSE"

Write-Host "== test 3: robo de lock muerto =="
Clean
New-Item -ItemType Directory -Force -Path (Join-Path $lock 'build.lock') | Out-Null
# owner.json con PID inexistente y viejo
$dead = [ordered]@{ ownerPid=999999; ownerStartedUtc='2000-01-01T00:00:00Z'; host='x'; fingerprint=$fp; phase='building'; startedUtc=(Get-Date).ToUniversalTime().ToString('o') }
($dead | ConvertTo-Json -Compress) | Set-Content (Join-Path $lock 'build.lock\owner.json') -Encoding ASCII
$c = StartAcquire 'build' '_c.txt' 30                # debe robar y volverse OWNER
$crc = ReadRC $c '_c.txt'
$cout = Get-Content -Raw (Join-Path $lock '_c.txt')
Ok ($crc -eq 0) "acquire roba lock muerto y toma OWNER; actual=$crc"
Ok ($cout -match 'robando lock stale') "loguea el robo"
Release 'build' 'OK'

Write-Host "== test 4: lanes independientes (build vs tests) =="
Clean
& $coord -Lane build -Action acquire -OwnerPid $PID | Out-Null
$t = StartAcquire 'tests' '_t.txt' 30                # otra lane -> NO debe bloquearse
$trc = ReadRC $t '_t.txt'
Ok ($trc -eq 0) "lane tests toma OWNER en paralelo a lane build; actual=$trc"
Release 'build' 'OK'
Release 'tests' 'OK'

Write-Host "== test 5: release ajeno rechazado =="
Clean
& $coord -Lane build -Action acquire -OwnerPid $PID | Out-Null
& $coord -Lane build -Action release -Result OK -OwnerPid 999999 | Out-Null
Ok ($LASTEXITCODE -eq 1) "otro PID no puede liberar el lock"
Ok (Test-Path (Join-Path $lock 'build.lock')) "lock sigue presente tras release ajeno"
Release 'build' 'OK'

Clean
Write-Host ""
if($fails -eq 0){ Write-Host "=== ALL COORD TESTS PASSED ===" -Foreground Green; exit 0 }
else { Write-Host "=== $fails COORD TEST(S) FAILED ===" -Foreground Red; exit 1 }
