<#
.SYNOPSIS
    LlamaCode zero-to-running bootstrap for Windows.

.DESCRIPTION
    Installs every dependency (git, Python, CMake, VS Build Tools 2022 v143,
    Qt 6.8.3 msvc2022_64), clones the repo into an isolated folder, builds, and
    deploys the Qt runtime next to the binary.

.EXAMPLE
    irm https://raw.githubusercontent.com/guideahon/LlamaCode/main/scripts/bootstrap.ps1 | iex

.NOTES
    Override defaults via env vars before running:
      $env:LC_DIR     = "C:\path\to\install"   # default: %USERPROFILE%\LlamaCode
      $env:LC_BRANCH  = "main"
      $env:LC_CONFIG  = "Release"               # Release|Debug
      $env:LC_NORUN   = "1"                      # skip launching at the end
#>

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ── Config ──────────────────────────────────────────────────────────────────
$Repo    = 'https://github.com/guideahon/LlamaCode.git'
$Dir     = if ($env:LC_DIR)    { $env:LC_DIR }    else { Join-Path $env:USERPROFILE 'LlamaCode' }
$Branch  = if ($env:LC_BRANCH) { $env:LC_BRANCH } else { 'main' }
$Config  = if ($env:LC_CONFIG) { $env:LC_CONFIG } else { 'Release' }
$QtVer   = '6.8.3'
$QtArch  = 'win64_msvc2022_64'
$QtDir   = "C:\Qt\$QtVer\msvc2022_64"

function Info($m)  { Write-Host "[*] $m"  -ForegroundColor Cyan }
function Ok($m)    { Write-Host "[OK] $m" -ForegroundColor Green }
function Die($m)   { Write-Host "[ERROR] $m" -ForegroundColor Red; exit 1 }

function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path','Machine')
    $user    = [Environment]::GetEnvironmentVariable('Path','User')
    $env:Path = "$machine;$user"
}

Write-Host ""
Write-Host "=== LlamaCode bootstrap (Windows) ===" -ForegroundColor Magenta
Write-Host "Target: $Dir  branch=$Branch  config=$Config"
Write-Host ""

# ── winget (required, cannot self-install) ──────────────────────────────────
if (-not (Have winget)) {
    Die "winget not found. Install 'App Installer' from the Microsoft Store, then re-run."
}

# ── git ─────────────────────────────────────────────────────────────────────
if (-not (Have git)) {
    Info "Installing Git..."
    winget install --id Git.Git --exact --source winget --accept-source-agreements --accept-package-agreements
    Refresh-Path
}
if (-not (Have git)) { Die "Git not on PATH after install. Open a new terminal and re-run." }
Ok "git"

# ── Python ──────────────────────────────────────────────────────────────────
if (-not (Have python)) {
    Info "Installing Python..."
    winget install --id Python.Python.3.12 --exact --source winget --accept-source-agreements --accept-package-agreements
    Refresh-Path
}
if (-not (Have python)) { Die "Python not on PATH after install. Open a new terminal and re-run." }
Ok "python"

# ── CMake ───────────────────────────────────────────────────────────────────
$CMake = "$env:ProgramFiles\CMake\bin\cmake.exe"
if (-not (Test-Path $CMake)) {
    if (Have cmake) { $CMake = (Get-Command cmake).Source }
    else {
        Info "Installing CMake..."
        winget install --id Kitware.CMake --exact --source winget --accept-source-agreements --accept-package-agreements
        Refresh-Path
        if (-not (Test-Path $CMake)) { if (Have cmake) { $CMake = (Get-Command cmake).Source } }
    }
}
if (-not (Test-Path $CMake)) { Die "CMake not found after install." }
Ok "cmake: $CMake"

# ── Visual Studio Build Tools 2022 (v143) ───────────────────────────────────
$HasVs = (Test-Path "C:\BuildTools2022\MSBuild\Current\Bin\MSBuild.exe") -or `
         (Test-Path "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe")
if (-not $HasVs) {
    Info "Installing Visual Studio Build Tools 2022 (v143) -- this is large, be patient..."
    winget install --id Microsoft.VisualStudio.2022.BuildTools --exact `
        --override "--quiet --wait --norestart --nocache --installPath C:\BuildTools2022 --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.VC.v143.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621" `
        --accept-source-agreements --accept-package-agreements
}
$Generator = if (Test-Path "C:\BuildTools2022\MSBuild\Current\Bin\MSBuild.exe") { "Visual Studio 17 2022" }
             elseif (Test-Path "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe") { "Visual Studio 17 2022" }
             else { Die "VS Build Tools 2022 not found after install." }
Ok "VS Build Tools 2022 ($Generator)"

# ── Qt 6.8.3 (msvc2022_64) via aqtinstall ───────────────────────────────────
if (-not (Test-Path "$QtDir\lib\cmake\Qt6\Qt6Config.cmake")) {
    Info "Installing Qt $QtVer ($QtArch) via aqtinstall..."
    python -m pip install --user --upgrade aqtinstall
    python -m aqt install-qt windows desktop $QtVer $QtArch -O C:\Qt
}
if (-not (Test-Path "$QtDir\lib\cmake\Qt6\Qt6Config.cmake")) { Die "Qt6 not found at $QtDir after install." }
Ok "Qt6: $QtDir"

# ── Clone / update ──────────────────────────────────────────────────────────
if (Test-Path (Join-Path $Dir '.git')) {
    Info "Repo exists -- pulling latest..."
    git -C $Dir fetch --depth 1 origin $Branch
    git -C $Dir checkout $Branch
    git -C $Dir reset --hard "origin/$Branch"
} else {
    Info "Cloning into $Dir ..."
    git clone --depth 1 --branch $Branch $Repo $Dir
}
Ok "source ready"

# ── Build ───────────────────────────────────────────────────────────────────
$BuildDir = Join-Path $Dir 'build'
Info "Configuring..."
& $CMake -S $Dir -B $BuildDir -G $Generator -A x64 -DCMAKE_PREFIX_PATH="$QtDir"
if ($LASTEXITCODE -ne 0) { Die "CMake configure failed." }

Info "Building ($Config)..."
& $CMake --build $BuildDir --config $Config -- /maxcpucount
if ($LASTEXITCODE -ne 0) { Die "Build failed." }

# ── Deploy Qt runtime ───────────────────────────────────────────────────────
$ExeDir  = Join-Path $BuildDir $Config
$ExePath = Join-Path $ExeDir 'LlamaCode.exe'
if (-not (Test-Path $ExePath)) { Die "Built exe missing at $ExePath" }

$DeployFlag = if ($Config -ieq 'Debug') { '--debug' } else { '--release' }
Info "Deploying Qt runtime..."
& "$QtDir\bin\windeployqt.exe" $DeployFlag --qmldir (Join-Path $Dir 'qml') --no-translations --compiler-runtime $ExePath
# Qt.labs.settings is not always picked up by windeployqt.
$LabsSrc = "$QtDir\qml\Qt\labs\settings"
if (Test-Path $LabsSrc) {
    Copy-Item -Recurse -Force $LabsSrc (Join-Path $ExeDir 'qml\Qt\labs\settings')
}

Write-Host ""
Ok "Done. Binary: $ExePath"
Write-Host ""

if (-not $env:LC_NORUN) {
    Info "Launching LlamaCode..."
    Start-Process -FilePath $ExePath -WorkingDirectory $ExeDir
}
