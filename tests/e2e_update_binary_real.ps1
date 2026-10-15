# E2E del "Actualizar" binario en Windows con una release REAL de GitHub, en una
# carpeta temporal: nunca toca la instalacion del usuario ni lanza la app.
#   descarga el zip de la release + su .sha256 -> verifica -> instala
#   reinstala (queda .prev) -> -Rollback -> limpia
# Releases firmadas (>= 0.1.128) con gh logueado: exige la procedencia
# (LC_REQUIRE_ATTESTATION=1). Una anterior a la firma tiene que instalar igual.
# Fuera de ctest: baja ~2 x 56 MB.
#   powershell -File tests\e2e_update_binary_real.ps1 [-Tag v0.1.127-debug]
param([string]$Tag = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root 'scripts\update-binary.ps1'
$repo = 'cristianlukas/UNLZ_Llamacode'
$fails = 0
function Check([bool]$condition, [string]$message) {
    if ($condition) { Write-Host "  PASS $message" }
    else { Write-Host "  FAIL $message" -ForegroundColor Red; $script:fails++ }
}

[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$headers = @{ 'User-Agent' = 'LlamaCode-e2e'; 'Accept' = 'application/vnd.github+json' }
if (-not $Tag) {
    # La release mas nueva (Prod o Debug) que ya tenga el zip de Windows.
    $releases = Invoke-RestMethod -Headers $headers "https://api.github.com/repos/$repo/releases?per_page=20"
    $rel = $releases | Where-Object { $_.assets | Where-Object { $_.name -like '*-windows-x64.zip' } } | Select-Object -First 1
} else {
    $rel = Invoke-RestMethod -Headers $headers "https://api.github.com/repos/$repo/releases/tags/$Tag"
}
if (-not $rel) { throw 'No hay ninguna release con el zip de Windows.' }
$zip = $rel.assets | Where-Object { $_.name -like '*-windows-x64.zip' } | Select-Object -First 1
$sha = $rel.assets | Where-Object { $_.name -eq "$($zip.name).sha256" } | Select-Object -First 1
$version = ($rel.tag_name -replace '^v', '' -replace '-.*$', '')
Write-Host "== e2e update-binary.ps1: $($rel.tag_name) ($($zip.name), $([int]($zip.size / 1MB)) MB) =="

$work = Join-Path $env:TEMP ('lc-e2e-update-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
$inst = Join-Path $work 'LlamaCode'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$gh = Get-Command gh -ErrorAction SilentlyContinue
$ghReady = $false
if ($gh) { & $gh.Source auth status *> $null; $ghReady = ($LASTEXITCODE -eq 0) }
$signed = ([version]$version -ge [version]'0.1.128')
if ($ghReady -and $signed) { $env:LC_REQUIRE_ATTESTATION = '1' }

function Invoke-Updater([string[]]$extra) {
    $args = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $script,
              '-AssetUrl', $zip.browser_download_url, '-InstallDir', $inst,
              '-Version', $version, '-NoLaunch', '-NoShortcuts', '-NoPause') + $extra
    if ($sha) { $args += @('-Sha256Url', $sha.browser_download_url) }
    $out = & powershell @args 2>&1 | Out-String
    return @{ Code = $LASTEXITCODE; Out = $out }
}

try {
    $r = Invoke-Updater @()
    Check ($r.Code -eq 0) "instala la release real (rc=$($r.Code))"
    Check ($r.Out -match 'SHA-256 verified') 'verifica el SHA-256 contra el de la release'
    if ($ghReady -and $signed) {
        Check ($r.Out -match 'Provenance verified') 'la procedencia firmada se verifica con gh'
    } elseif (-not $signed) {
        Check ($r.Out -notmatch 'Provenance check failed') 'una release anterior a la firma no exige procedencia'
    } else {
        Write-Host '  SKIP procedencia (gh no esta logueado)'
    }
    $exe = Join-Path $inst 'LlamaCode.exe'
    Check (Test-Path -LiteralPath $exe) 'queda LlamaCode.exe en la carpeta'
    Check (Test-Path -LiteralPath (Join-Path $inst 'Qt6Core.dll')) 'el paquete trae el runtime de Qt (windeployqt)'
    if (Test-Path -LiteralPath $exe) {
        $fv = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
        Write-Host "  info: version del exe = $fv"
    }
    $r2 = Invoke-Updater @()
    Check ($r2.Code -eq 0 -and (Test-Path -LiteralPath "$inst.prev")) 'reinstalar deja la anterior en .prev'
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $script -Rollback -InstallDir $inst -NoLaunch -NoPause 2>&1 | Out-String
    Check ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $exe) -and (Test-Path -LiteralPath "$inst.failed")) '-Rollback vuelve a la anterior'
} finally {
    Remove-Item Env:LC_REQUIRE_ATTESTATION -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force -LiteralPath $work -ErrorAction SilentlyContinue
}
if ($fails) { throw "$fails e2e check(s) failed" }
Write-Host 'e2e update-binary OK.'
