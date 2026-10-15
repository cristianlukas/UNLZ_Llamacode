<#
.SYNOPSIS
    Packages a built LlamaCode.exe as the Windows release asset.

.DESCRIPTION
    Stages the exe, deploys the Qt runtime (windeployqt, same flags as
    build.bat/bootstrap.ps1), adds the MSVC CRT app-local (a clean Windows may
    not have it) and the install marker, then zips it and writes the .sha256.

      dist\LlamaCode-<tag>-windows-x64.zip
      dist\LlamaCode-<tag>-windows-x64.zip.sha256   ("<hex>  <name>", sha256sum format)

    The zip has the files at its root; update-binary.ps1 extracts it as the
    install folder. The channel comes from the tag: vX.Y.Z-debug = Debug build.
    Debug in MSVC is already optimized and links the release Qt DLLs (see
    CMakeLists.txt), so it is shipped as is, minus the PDB.

.EXAMPLE
    powershell -File scripts\package-windows.ps1 -Tag v0.1.127-debug -BuildDir build -QtDir C:\Qt\6.8.3\msvc2022_64

.NOTES
    ASCII only (Windows PowerShell 5.1).
#>
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [string]$BuildDir = 'build',
    [string]$QtDir = 'C:\Qt\6.8.3\msvc2022_64',
    [string]$OutDir = 'dist',
    [string]$CrtDir = '',
    # Source tree whose qml/ is scanned (CI packages a tag with the scripts of
    # the workflow's commit, so they can differ).
    [string]$SourceDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($SourceDir) { $root = [IO.Path]::GetFullPath((Join-Path (Get-Location) $SourceDir)) }

$m = [regex]::Match($Tag, '^v([0-9]+\.[0-9]+\.[0-9]+)(-debug)?$')
if (-not $m.Success) { throw "Invalid tag '$Tag' (vX.Y.Z or vX.Y.Z-debug)" }
$Version = $m.Groups[1].Value
$Channel = if ($m.Groups[2].Success) { 'debug' } else { 'prod' }
$Config = if ($Channel -eq 'debug') { 'Debug' } else { 'Release' }

$BuildDir = [IO.Path]::GetFullPath((Join-Path (Get-Location) $BuildDir))
$OutDir = [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutDir))
$exe = Join-Path $BuildDir "$Config\LlamaCode.exe"
if (-not (Test-Path $exe)) { throw "Built exe missing: $exe" }

$name = "LlamaCode-$Tag-windows-x64.zip"
$stage = Join-Path $OutDir 'stage-windows'
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item $exe $stage

$stagedExe = Join-Path $stage 'LlamaCode.exe'
$deployFlag = @(if ($Config -eq 'Release') { '--release' })
& (Join-Path $QtDir 'bin\windeployqt.exe') @deployFlag --qmldir (Join-Path $root 'qml') --no-translations --compiler-runtime $stagedExe
if ($LASTEXITCODE -ne 0) { throw "windeployqt failed ($LASTEXITCODE)" }
$labs = Join-Path $QtDir 'qml\Qt\labs\settings'
if (Test-Path $labs) { Copy-Item -Recurse -Force $labs (Join-Path $stage 'qml\Qt\labs\settings') }
# windeployqt drops the 25 MB vc_redist installer; the DLLs go app-local instead.
Remove-Item -Force (Join-Path $stage 'vc_redist*.exe') -ErrorAction SilentlyContinue

if (-not $CrtDir) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path $vswhere) {
        $vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
        if ($vs) {
            $CrtDir = Get-ChildItem -Directory (Join-Path $vs 'VC\Redist\MSVC') -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending | ForEach-Object {
                    Get-ChildItem -Directory (Join-Path $_.FullName 'x64') -Filter 'Microsoft.VC*.CRT' -ErrorAction SilentlyContinue
                } | Select-Object -First 1 -ExpandProperty FullName
        }
    }
}
if ($CrtDir -and (Test-Path $CrtDir)) {
    Copy-Item (Join-Path $CrtDir '*.dll') $stage -Force
    Write-Host "[OK] MSVC CRT app-local from $CrtDir"
} else {
    Write-Host '[WARN] MSVC CRT not found; the package relies on the system VC++ runtime.'
}

Get-ChildItem $stage -Recurse -Include '*.pdb', '*.ilk', '*.lib', '*.exp' | Remove-Item -Force

# Marker: the app recognizes a binary install (updates in place, never builds).
[ordered]@{
    kind = 'binary'; channel = $Channel; version = $Version; tag = $Tag; platform = 'windows-x64'
} | ConvertTo-Json | Set-Content -Path (Join-Path $stage 'llamacode-install.json') -Encoding ASCII

$zip = Join-Path $OutDir $name
if (Test-Path $zip) { Remove-Item -Force $zip }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip, [IO.Compression.CompressionLevel]::Optimal, $false)
$hash = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLower()
[IO.File]::WriteAllText("$zip.sha256", "$hash  $name`n")

$mb = '{0:N1}' -f ((Get-Item $zip).Length / 1MB)
Write-Host "[OK] $zip ($mb MB)"
Write-Host "[OK] sha256 $hash"
