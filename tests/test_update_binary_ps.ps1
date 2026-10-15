# Test de scripts/update-binary.ps1 ("Actualizar" con binario en Windows) contra
# zips falsos locales: nunca baja nada ni toca la instalacion real. Cubre el swap
# de carpeta, el hash, y el rollback (automatico si la version nueva no arranca,
# y manual con -Rollback). Fuera de ctest, como el resto de la infra PS.
#   powershell -File tests\test_update_binary_ps.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root 'scripts\update-binary.ps1'
$fails = 0
function Check([bool]$condition, [string]$message) {
    if ($condition) { Write-Host "  PASS $message" }
    else { Write-Host "  FAIL $message" -ForegroundColor Red; $script:fails++ }
}

$work = Join-Path $env:TEMP ('lc-update-test-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $work | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
# SHA-256 via .NET: Get-FileHash vive en un modulo que PowerShell 5.1 no carga
# si lo lanzo PowerShell 7 (hereda su PSModulePath) -> "no se reconoce".
function Get-Sha256Hex([string]$path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($path)
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream)) -replace '-', '').ToLower() }
    finally { $stream.Dispose(); $sha.Dispose() }
}

# Paquete falso: LlamaCode.exe es una copia de un exe del sistema que sale al
# instante con el codigo elegido (whoami = 0 "arranco y paso la posta",
# where sin argumentos = 2 "murio al arrancar") + version.txt.
function New-Package([string]$name, [string]$version, [string]$exeSource) {
    $dir = Join-Path $work "pkg-$name"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Copy-Item -LiteralPath $exeSource -Destination (Join-Path $dir 'LlamaCode.exe')
    Set-Content -LiteralPath (Join-Path $dir 'version.txt') -Value $version -NoNewline
    $zip = Join-Path $work "$name.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    [IO.Compression.ZipFile]::CreateFromDirectory($dir, $zip)
    $hash = Get-Sha256Hex $zip
    return @{ Zip = $zip; Hash = $hash }
}
function Invoke-Update([hashtable]$pkg, [string[]]$extra) {
    $args = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $script,
              '-AssetUrl', $pkg.Zip, '-Sha256', $pkg.Hash, '-InstallDir', $inst,
              '-NoShortcuts', '-NoPause') + $extra
    $out = & powershell @args 2>&1 | Out-String
    return @{ Code = $LASTEXITCODE; Out = $out }
}
function Version-Of([string]$dir) {
    $f = Join-Path $dir 'version.txt'
    if (Test-Path -LiteralPath $f) { return [IO.File]::ReadAllText($f) } else { return '' }
}

$env:LC_TEST_HIDDEN_LAUNCH = '1'
$env:LC_HEALTH_SECONDS = '3'
$good = Join-Path $env:SystemRoot 'System32\whoami.exe'
$bad = Join-Path $env:SystemRoot 'System32\where.exe'
$inst = Join-Path $work 'LlamaCode'

try {
    Write-Host '== update-binary.ps1 =='
    $v1 = New-Package 'v1' 'v1' $good
    $r = Invoke-Update $v1 @('-NoLaunch')
    Check ($r.Code -eq 0) "instala v1 (rc=$($r.Code))"
    Check ((Version-Of $inst) -eq 'v1') 'la carpeta queda con v1'

    $v2 = New-Package 'v2' 'v2' $good
    $r = Invoke-Update $v2 @()
    Check ($r.Code -eq 0) "actualiza a v2 y arranca (rc=$($r.Code))"
    Check ((Version-Of $inst) -eq 'v2') 'la carpeta queda con v2'
    Check ((Version-Of "$inst.prev") -eq 'v1') 'la version anterior queda en .prev (rollback posible)'

    # Hash equivocado: nada se toca.
    $v3 = New-Package 'v3' 'v3' $good
    $wrong = @{ Zip = $v3.Zip; Hash = ('0' * 64) }
    $r = Invoke-Update $wrong @('-NoLaunch')
    Check ($r.Code -eq 1 -and $r.Out -match 'SHA-256 mismatch') 'hash equivocado: sale 1 y lo explica'
    Check ((Version-Of $inst) -eq 'v2' -and (Version-Of "$inst.prev") -eq 'v1') 'con hash equivocado nada cambia'

    # Rollback automatico: la version nueva muere al arrancar -> vuelve la anterior.
    $broken = New-Package 'broken' 'v4-rota' $bad
    $r = Invoke-Update $broken @()
    Check ($r.Code -eq 1 -and $r.Out -match 'rolled back') "version que no arranca: sale 1 y avisa el rollback (rc=$($r.Code))"
    Check ((Version-Of $inst) -eq 'v2') 'tras el rollback automatico vuelve v2'
    Check ((Version-Of "$inst.failed") -eq 'v4-rota') 'la version rota queda en .failed para revisarla'

    # Rollback manual: -Rollback vuelve a .prev en cualquier momento.
    $r = Invoke-Update $v3 @()
    Check ((Version-Of $inst) -eq 'v3' -and (Version-Of "$inst.prev") -eq 'v2') 'actualiza a v3 (v2 en .prev)'
    Check (-not (Test-Path -LiteralPath "$inst.failed")) 'un update que funciona borra el .failed anterior'
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $script -Rollback -InstallDir $inst -NoLaunch -NoPause 2>&1 | Out-String
    Check ($LASTEXITCODE -eq 0) "-Rollback sale 0 (rc=$LASTEXITCODE)"
    Check ((Version-Of $inst) -eq 'v2') '-Rollback deja v2 instalada'
    Check ((Version-Of "$inst.failed") -eq 'v3') '-Rollback guarda la que saco en .failed'
    Remove-Item -Recurse -Force -LiteralPath "$inst.prev" -ErrorAction SilentlyContinue
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $script -Rollback -InstallDir $inst -NoLaunch -NoPause 2>&1 | Out-String
    Check ($LASTEXITCODE -eq 1 -and $out -match 'no previous version') 'sin .prev, -Rollback falla claro y no toca nada'
    Check ((Version-Of $inst) -eq 'v2') 'sin .prev la instalacion queda intacta'

    # Procedencia (attestation del CI) con un gh falso primero en el PATH: nunca
    # llama al gh real.
    $ghBin = Join-Path $work 'ghbin'
    New-Item -ItemType Directory -Force -Path $ghBin | Out-Null
    $ghCmd = @(
        '@echo off',
        'if "%1"=="auth" exit %FAKE_GH_AUTH_RC%',
        'if "%1"=="attestation" (',
        '  if "%FAKE_GH_ATTEST_FAIL%"=="1" (echo Error: HTTP 404: no attestations found & exit 1)',
        '  echo Loaded 1 attestation from GitHub API & exit 0',
        ')',
        'exit /b 0')
    Set-Content -LiteralPath (Join-Path $ghBin 'gh.cmd') -Value $ghCmd -Encoding ASCII
    $oldPath = $env:PATH
    $env:PATH = "$ghBin;$env:PATH"
    try {
        $att = Join-Path $work 'Attested'
        $script:inst = $att
        $env:FAKE_GH_AUTH_RC = '0'
        $env:FAKE_GH_ATTEST_FAIL = '1'
        $a1 = New-Package 'a1' 'a1' $good
        $r = Invoke-Update $a1 @('-NoLaunch', '-Version', '0.1.130')
        Check ($r.Code -eq 1 -and $r.Out -match 'Provenance check failed' -and $r.Out -match '404') "release firmada sin attestation valida: no instala (rc=$($r.Code))"
        Check (-not (Test-Path -LiteralPath $att)) 'sin attestation valida no se toca la instalacion'
        $env:FAKE_GH_ATTEST_FAIL = '0'
        $r = Invoke-Update $a1 @('-NoLaunch', '-Version', '0.1.130')
        Check ($r.Code -eq 0 -and $r.Out -match 'Provenance verified') "attestation valida: instala (rc=$($r.Code))"
        Check ((Version-Of $att) -eq 'a1') 'con attestation valida queda instalada'
        # Releases viejas (antes de 0.1.128) no traen firma: no se exige.
        $env:FAKE_GH_ATTEST_FAIL = '1'
        $a2 = New-Package 'a2' 'a2' $good
        $r = Invoke-Update $a2 @('-NoLaunch', '-Version', '0.1.120')
        Check ($r.Code -eq 0 -and $r.Out -notmatch 'Provenance') 'una release anterior a las firmadas no pide procedencia'
        # LC_REQUIRE_ATTESTATION: sin gh logueado no cae al hash solo.
        $env:FAKE_GH_AUTH_RC = '1'
        $env:LC_REQUIRE_ATTESTATION = '1'
        $a3 = New-Package 'a3' 'a3' $good
        $r = Invoke-Update $a3 @('-NoLaunch')
        Check ($r.Code -eq 1 -and $r.Out -match 'cannot be checked' -and (Version-Of $att) -eq 'a2') 'LC_REQUIRE_ATTESTATION sin gh logueado: no instala'
    } finally {
        $env:PATH = $oldPath
        Remove-Item Env:FAKE_GH_AUTH_RC, Env:FAKE_GH_ATTEST_FAIL, Env:LC_REQUIRE_ATTESTATION -ErrorAction SilentlyContinue
    }
} finally {
    Remove-Item Env:LC_TEST_HIDDEN_LAUNCH, Env:LC_HEALTH_SECONDS -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force -LiteralPath $work -ErrorAction SilentlyContinue
}

if ($fails) { throw "$fails update-binary regression(s) failed" }
Write-Host 'All update-binary regressions passed.'
