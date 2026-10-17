<#
.SYNOPSIS
    LlamaCode binary updater/installer for Windows (no compiler needed).

.DESCRIPTION
    Downloads the precompiled release asset (zip), verifies its SHA-256, waits
    for the running app to close, swaps the install folder atomically (the old
    one is kept until the new one is in place) and relaunches LlamaCode.

    "Actualizar" in the app writes this script (bundled in the qrc) to %TEMP%
    and runs it in a visible console with every parameter filled in. It also
    works standalone as an installer: with no -AssetUrl it asks GitHub for the
    latest release of -Channel and picks the Windows asset.

    User data lives in %APPDATA% / %LOCALAPPDATA%\LlamaCode: never touched here.

    Provenance (same as update-binary.sh): releases from 0.1.128 on carry a
    Sigstore attestation from release-binaries.yml. With the GitHub CLI logged
    in the package must verify against it (a hand-uploaded asset does not);
    without gh it is reported only. LC_REQUIRE_ATTESTATION=1 demands it whatever
    the version, and refuses when gh cannot check it.

    Rollback (same as update-binary.sh): the previous version stays as
    <install>.prev. If the new one exits with an error within LC_HEALTH_SECONDS
    (default 10) of the relaunch, it is moved to <install>.failed, the previous
    one is put back and relaunched. -Rollback does the same by hand, any time:
    the current version goes to <install>.failed and .prev comes back.

.NOTES
    ASCII only on purpose (Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI).
    Env var fallbacks (for 'irm | iex', where params do not exist):
      LC_CHANNEL, LC_ASSET_URL, LC_SHA256, LC_SHA256_URL, LC_INSTALL_DIR, LC_NORUN,
      LC_START_MENU_DIR
    -StartMenuDir / LC_START_MENU_DIR replace the user's Start Menu (and the
    folders scanned for legacy shortcuts) with that folder: tests use it so they
    never leave a shortcut to a temp exe in the real Start Menu.
#>
param(
    [string]$AssetUrl = $env:LC_ASSET_URL,
    [string]$Sha256 = $env:LC_SHA256,
    [string]$Sha256Url = $env:LC_SHA256_URL,
    [string]$InstallDir = $env:LC_INSTALL_DIR,
    [string]$Channel = $(if ($env:LC_CHANNEL) { $env:LC_CHANNEL } else { 'prod' }),
    [string]$Version = '',
    [int]$WaitPid = 0,
    [string]$LegacyExe = '',
    [string]$StartMenuDir = $env:LC_START_MENU_DIR,
    [switch]$NoLaunch,
    [switch]$NoShortcuts,
    [switch]$NoPause,
    [switch]$Rollback
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Repo = 'cristianlukas/UNLZ_Llamacode'
$Channel = $Channel.Trim().ToLower()
if ($env:LC_NORUN) { $NoLaunch = $true }
try {
    $Host.UI.RawUI.WindowTitle = 'LlamaCode - actualizando' + $(if ($Version) { " a v$Version" } else { '' })
} catch {}

function Info($m) {
    Write-Host "[*] $m" -ForegroundColor Cyan
    try {
        if ($Host.UI.RawUI.WindowTitle -like 'LlamaCode*') { $Host.UI.RawUI.WindowTitle = "LlamaCode - $m" }
    } catch {}
}
function Ok($m)  { Write-Host "[OK] $m" -ForegroundColor Green }
# SHA-256 via .NET: Get-FileHash vive en un modulo que PowerShell 5.1 no carga
# si lo lanzo PowerShell 7 (hereda su PSModulePath) -> "no se reconoce".
function Get-Sha256Hex([string]$path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($path)
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream)) -replace '-', '').ToLower() }
    finally { $stream.Dispose(); $sha.Dispose() }
}
function Die($m) { throw [System.Exception]::new("LCUPD: $m") }

# Asset name contract, shared with the CI (release-binaries.yml) and the app
# (AppController::selectReleaseAsset): LlamaCode-<tag>-windows-x64.zip
function Get-AssetName([string]$tag) { "LlamaCode-$tag-windows-x64.zip" }

function Get-DefaultInstallDir([string]$channel) {
    $name = if ($channel -eq 'debug') { 'LlamaCode-Debug' } else { 'LlamaCode' }
    Join-Path (Join-Path $env:LOCALAPPDATA 'Programs') $name
}

function Resolve-LatestAsset([string]$channel) {
    $headers = @{ 'Accept' = 'application/vnd.github+json'; 'User-Agent' = 'LlamaCode-updater' }
    # Sin @(...): en PS 5.1 Invoke-RestMethod emite el array JSON como UN objeto
    # y @() lo envolveria en un array de un solo elemento (no veia ninguna release).
    $releases = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Repo/releases?per_page=50"
    $pattern = if ($channel -eq 'debug') { '^v(\d+\.\d+\.\d+)-debug$' } else { '^v(\d+\.\d+\.\d+)$' }
    $best = $null; $bestVer = $null
    foreach ($r in $releases) {
        if ($r.draft -or ([bool]$r.prerelease -ne ($channel -eq 'debug'))) { continue }
        $m = [regex]::Match([string]$r.tag_name, $pattern)
        if (-not $m.Success) { continue }
        $name = Get-AssetName $r.tag_name
        $asset = @($r.assets | Where-Object { $_.name -eq $name }) | Select-Object -First 1
        if (-not $asset) { continue }
        $ver = [version]$m.Groups[1].Value
        if (-not $bestVer -or $ver -gt $bestVer) { $best = @{ release = $r; asset = $asset }; $bestVer = $ver }
    }
    if (-not $best) { Die "No $channel release with a Windows binary was found on GitHub." }
    $digest = ''
    if ($best.asset.PSObject.Properties['digest'] -and "$($best.asset.digest)" -like 'sha256:*') {
        $digest = "$($best.asset.digest)".Substring(7)
    }
    $shaAsset = @($best.release.assets | Where-Object { $_.name -eq "$($best.asset.name).sha256" }) | Select-Object -First 1
    return @{
        Url = $best.asset.browser_download_url
        Sha256 = $digest
        Sha256Url = $(if ($shaAsset) { $shaAsset.browser_download_url } else { '' })
        Version = $bestVer.ToString()
    }
}

# Local paths (and file://) are accepted so the regression test can run the
# whole flow offline against a fake zip.
function Get-LocalPath([string]$url) {
    if ($url -match '^file:///?(.+)$') { return ($Matches[1] -replace '/', '\') }
    if ($url -notmatch '^[a-z][a-z0-9+.-]*://' -and (Test-Path -LiteralPath $url)) { return $url }
    return $null
}

function Save-Url([string]$url, [string]$dest, [switch]$Quiet) {
    $local = Get-LocalPath $url
    if ($local) { Copy-Item -LiteralPath $local -Destination $dest -Force; return }
    # Transient errors (a 504 from GitHub, a dropped connection) are retried like
    # curl --retry 3 on Linux; a 4xx is final.
    for ($attempt = 1; ; $attempt++) {
        try { Save-UrlOnce $url $dest -Quiet:$Quiet; return } catch {
            $status = 0
            $we = $_.Exception.InnerException
            if (-not $we) { $we = $_.Exception }
            if ($we -is [Net.WebException] -and $we.Response) { $status = [int]$we.Response.StatusCode }
            $transient = ($status -eq 0) -or ($status -ge 500) -or ($status -eq 408) -or ($status -eq 429)
            if (-not $transient -or $attempt -ge 4) { throw }
            Info "Download failed ($(if ($status) { "HTTP $status" } else { 'network' })); retrying ($attempt/3)..."
            Start-Sleep -Seconds ([Math]::Min(8, 2 * $attempt))
        }
    }
}

function Save-UrlOnce([string]$url, [string]$dest, [switch]$Quiet) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $req = [Net.HttpWebRequest]::Create($url)
    $req.UserAgent = 'LlamaCode-updater'
    $req.AllowAutoRedirect = $true
    $resp = $req.GetResponse()
    try {
        $total = $resp.ContentLength
        $in = $resp.GetResponseStream()
        $out = [IO.File]::Create($dest)
        try {
            $buf = New-Object byte[] (1024 * 256)
            $done = [long]0; $lastPct = -1
            while (($n = $in.Read($buf, 0, $buf.Length)) -gt 0) {
                $out.Write($buf, 0, $n)
                $done += $n
                if (-not $Quiet -and $total -gt 0) {
                    $pct = [int](100 * $done / $total)
                    if ($pct -ne $lastPct -and ($pct % 5 -eq 0)) {
                        $lastPct = $pct
                        $mb = '{0:N1} / {1:N1} MB' -f ($done / 1MB), ($total / 1MB)
                        Write-Progress -Activity 'Descargando LlamaCode' -Status "$pct% ($mb)" -PercentComplete $pct
                        Write-Host "    $pct% ($mb)"
                    }
                }
            }
        } finally { $out.Dispose(); $in.Dispose() }
        if (-not $Quiet) { Write-Progress -Activity 'Descargando LlamaCode' -Completed }
        if ($total -gt 0 -and $done -ne $total) { Die "Download incomplete ($done of $total bytes)." }
    } finally { $resp.Close() }
}

# First token of a sha256sum-style line ("<hex>  <name>") or a bare hex string.
function Get-ExpectedHash([string]$text) {
    $m = [regex]::Match("$text", '(?i)\b([0-9a-f]{64})\b')
    if ($m.Success) { return $m.Groups[1].Value.ToLower() }
    return ''
}

function Test-UnderDir([string]$path, [string]$dir) {
    if (-not $path -or -not $dir) { return $false }
    $p = [IO.Path]::GetFullPath($path).TrimEnd('\') + '\'
    $d = [IO.Path]::GetFullPath($dir).TrimEnd('\') + '\'
    return $p.StartsWith($d, [StringComparison]::OrdinalIgnoreCase)
}

function Stop-InstalledProcesses([string]$dir) {
    # Only processes running FROM the install folder (the app, its scheduler
    # daemon): they hold the files the swap has to move. llama-server lives elsewhere.
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -and (Test-UnderDir $_.Path $dir) } catch { $false }
    } | ForEach-Object {
        Info "Closing $($_.ProcessName) (PID $($_.Id))..."
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

function Move-WithRetry([string]$from, [string]$to) {
    for ($i = 0; $i -lt 15; $i++) {
        try { Move-Item -LiteralPath $from -Destination $to -ErrorAction Stop; return } catch {
            if ($i -eq 14) { throw }
            Start-Sleep -Milliseconds 1000
        }
    }
}

# Put <install>.prev back in place; the current one is kept as <install>.failed.
function Restore-Previous([string]$dir) {
    $prev = "$dir.prev"
    if (-not (Test-Path -LiteralPath $prev)) { Die "There is no previous version to go back to ($prev)." }
    Stop-InstalledProcesses $dir
    Start-Sleep -Milliseconds 500
    $failed = "$dir.failed"
    if (Test-Path -LiteralPath $failed) { Remove-Item -Recurse -Force -LiteralPath $failed -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $dir) { Move-WithRetry $dir $failed }
    Move-WithRetry $prev $dir
    Ok "Previous version restored (the other one is kept in $failed)."
}

# Launch and watch the first seconds: a crash right after starting (missing DLL,
# bad release) means the update broke the app. Exit code 0 is fine (it handed
# off to an instance that was already open).
function Start-AndCheck([string]$exe, [string]$workDir) {
    $style = if ($env:LC_TEST_HIDDEN_LAUNCH) { 'Hidden' } else { 'Normal' }
    $proc = Start-Process -FilePath $exe -WorkingDirectory $workDir -WindowStyle $style -PassThru
    $seconds = 10
    if ($env:LC_HEALTH_SECONDS) { $seconds = [int]$env:LC_HEALTH_SECONDS }
    if ($proc.WaitForExit($seconds * 1000)) {
        if ($proc.ExitCode -ne 0) { return $proc.ExitCode }
    }
    return 0
}

function Set-Shortcut([string]$path, [string]$target, [string]$workDir) {
    $parent = Split-Path -Parent $path
    if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $wsh = New-Object -ComObject WScript.Shell
    $lnk = $wsh.CreateShortcut($path)
    $lnk.TargetPath = $target
    $lnk.WorkingDirectory = $workDir
    $lnk.Description = 'UNLZ LlamaCode'
    $lnk.IconLocation = "$target,0"
    $lnk.Save()
}

# Shortcuts that launched the OLD exe (a git checkout before migrating, or a zip
# extracted elsewhere) now launch the new one: Start Menu, Desktop and pinned
# taskbar entries.
function Update-LegacyShortcuts([string]$legacyExe, [string]$newExe, [string]$workDir) {
    if (-not $legacyExe -or ($legacyExe -ieq $newExe)) { return }
    if ($StartMenuDir) {
        # Redirected (tests): nothing of the real user profile is scanned.
        $roots = @($StartMenuDir) | Where-Object { Test-Path $_ }
    } else {
        $roots = @(
            [Environment]::GetFolderPath('Programs'),
            [Environment]::GetFolderPath('Desktop'),
            (Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar')
        ) | Where-Object { $_ -and (Test-Path $_) }
    }
    $wsh = New-Object -ComObject WScript.Shell
    foreach ($root in $roots) {
        Get-ChildItem -LiteralPath $root -Filter *.lnk -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $lnk = $wsh.CreateShortcut($_.FullName)
                if ($lnk.TargetPath -and ($lnk.TargetPath -ieq $legacyExe)) {
                    $lnk.TargetPath = $newExe
                    $lnk.WorkingDirectory = $workDir
                    $lnk.IconLocation = "$newExe,0"
                    $lnk.Save()
                    Ok "Shortcut now points to the new install: $($_.FullName)"
                }
            } catch {}
        }
    }
    # "Start with Windows" (HKCU Run) stores the exe path too.
    $run = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    if (Test-Path $run) {
        $props = Get-ItemProperty -Path $run
        foreach ($p in $props.PSObject.Properties) {
            if ($p.Name -like 'PS*') { continue }
            $val = "$($p.Value)"
            if ($val.IndexOf($legacyExe, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $new = [regex]::Replace($val, [regex]::Escape($legacyExe), $newExe.Replace('$', '$$'), 'IgnoreCase')
                Set-ItemProperty -Path $run -Name $p.Name -Value $new
                Ok "Startup entry '$($p.Name)' now points to the new install."
            }
        }
    }
}

$UpdateFailed = $false
$Mutex = $null
$LogPath = Join-Path $env:TEMP 'llamacode-update.log'
$Transcribing = $false
try { Start-Transcript -Path $LogPath -Force | Out-Null; $Transcribing = $true } catch {}
try {
    Write-Host ''
    Write-Host '=== LlamaCode update (precompiled binary) ===' -ForegroundColor Magenta
    # Same mutex as bootstrap.ps1: one update/build at a time.
    $Mutex = New-Object System.Threading.Mutex($false, 'Local\LlamaCodeBootstrap')
    $have = $false
    try { $have = $Mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $have = $true }
    if (-not $have) {
        $Mutex.Dispose(); $Mutex = $null
        Die 'Another LlamaCode update is already running in another window. Wait for it to finish.'
    }
    if ($Channel -notin @('prod', 'debug')) { Die "Invalid channel: $Channel (prod|debug)" }

    if ($Rollback) {
        if (-not $InstallDir) { $InstallDir = Get-DefaultInstallDir $Channel }
        $InstallDir = [IO.Path]::GetFullPath($InstallDir).TrimEnd('\')
        Info "Going back to the previous version in $InstallDir..."
        Restore-Previous $InstallDir
        if (-not $NoLaunch) { Start-Process -FilePath (Join-Path $InstallDir 'LlamaCode.exe') -WorkingDirectory $InstallDir }
        Write-Host ''
        Ok 'Rollback complete.'
        return
    }

    if (-not $AssetUrl) {
        Info "Looking up the latest $Channel release on GitHub..."
        $latest = Resolve-LatestAsset $Channel
        $AssetUrl = $latest.Url
        if (-not $Sha256) { $Sha256 = $latest.Sha256 }
        if (-not $Sha256Url) { $Sha256Url = $latest.Sha256Url }
        if (-not $Version) { $Version = $latest.Version }
    }
    if (-not $InstallDir) { $InstallDir = Get-DefaultInstallDir $Channel }
    $InstallDir = [IO.Path]::GetFullPath($InstallDir).TrimEnd('\')
    Write-Host "Version : $(if ($Version) { $Version } else { '(unknown)' }) ($Channel)"
    Write-Host "Install : $InstallDir"
    Write-Host "Source  : $AssetUrl"
    Write-Host ''

    # ---- Download + verify (nothing is touched until the hash matches) ------
    $Work = Join-Path $env:TEMP ("llamacode-update-" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Force -Path $Work | Out-Null
    $Zip = Join-Path $Work 'LlamaCode.zip'
    Info 'Downloading...'
    Save-Url $AssetUrl $Zip
    $Expected = Get-ExpectedHash $Sha256
    if (-not $Expected -and $Sha256Url) {
        $shaFile = Join-Path $Work 'asset.sha256'
        Save-Url $Sha256Url $shaFile -Quiet
        $Expected = Get-ExpectedHash ([IO.File]::ReadAllText($shaFile))
    }
    if (-not $Expected) { Die 'The release has no SHA-256 for this file; refusing to install an unverified binary.' }
    $Actual = Get-Sha256Hex $Zip
    if ($Actual -ne $Expected) {
        Die "SHA-256 mismatch: expected $Expected, got $Actual. The download is corrupt or was tampered with; nothing was changed."
    }
    Ok "SHA-256 verified ($Actual)"

    # ---- Provenance (the hash only proves the download matches the release) --
    $attestedSince = [version]'0.1.128'
    $verObj = $null
    if ($Version) { try { $verObj = [version]($Version -replace '^v', '' -replace '-.*$', '') } catch {} }
    $wantAttest = ($verObj -and $verObj -ge $attestedSince) -or [bool]$env:LC_REQUIRE_ATTESTATION
    if ($wantAttest) {
        # gh writes its progress to stderr. Under ErrorActionPreference=Stop,
        # Windows PowerShell 5.1 turns captured native stderr into a terminating
        # error, so the check aborted with an empty [ERROR] and nothing installed.
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        $ghReady = $false
        $attestOut = ''
        $attestRc = 1
        $eap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            if ($gh) { & $gh.Source auth status *> $null; $ghReady = ($LASTEXITCODE -eq 0) }
            if ($ghReady) {
                Info 'Verifying build provenance...'
                $attestOut = & $gh.Source attestation verify $Zip --repo $Repo `
                    --signer-workflow "$Repo/.github/workflows/release-binaries.yml" 2>&1 |
                    ForEach-Object { "$_" } | Out-String
                $attestRc = $LASTEXITCODE
            }
        } finally { $ErrorActionPreference = $eap }
        if ($ghReady) {
            if ($attestRc -eq 0) {
                Ok "Provenance verified: built by $Repo (release-binaries.yml)"
            } else {
                ($attestOut.Trim() -split "`n" | Select-Object -Last 5) | ForEach-Object { Write-Host "        $_" }
                Die "Provenance check failed: this package was not built by the $Repo release workflow. Nothing was changed."
            }
        } elseif ($env:LC_REQUIRE_ATTESTATION) {
            # Required means required: never fall back to the hash alone.
            Die 'LC_REQUIRE_ATTESTATION is set but the provenance cannot be checked: install the GitHub CLI and run gh auth login. Nothing was changed.'
        } else {
            Write-Host '[!] Provenance not verified (needs the GitHub CLI: gh auth login).' -ForegroundColor Yellow
            Write-Host '    The SHA-256 above only proves the download matches the release asset.'
        }
    }

    # ---- Stage next to the target (same volume: the swap is a rename) -------
    $Parent = Split-Path -Parent $InstallDir
    if (-not (Test-Path $Parent)) { New-Item -ItemType Directory -Force -Path $Parent | Out-Null }
    $Staging = "$InstallDir.new"
    if (Test-Path $Staging) { Remove-Item -Recurse -Force -LiteralPath $Staging }
    Info 'Extracting...'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($Zip, $Staging)
    if (-not (Test-Path (Join-Path $Staging 'LlamaCode.exe'))) {
        Remove-Item -Recurse -Force -LiteralPath $Staging -ErrorAction SilentlyContinue
        Die 'The downloaded package has no LlamaCode.exe at its root.'
    }

    # ---- Wait for the app, then swap ----------------------------------------
    if ($WaitPid -gt 0) {
        $proc = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
        if ($proc) {
            Info 'Waiting for LlamaCode to close...'
            if (-not $proc.WaitForExit(60000)) { Info 'LlamaCode did not close in 60 s; closing it.' }
        }
    }
    Stop-InstalledProcesses $InstallDir
    Start-Sleep -Milliseconds 500

    # The previous version is kept as .prev (one level) for the rollback below or
    # for -Rollback later. .old was the name before rollback existed.
    $Old = $null
    if (Test-Path -LiteralPath $InstallDir) {
        $Old = "$InstallDir.prev"
        foreach ($stale in @($Old, "$InstallDir.old")) {
            if (Test-Path -LiteralPath $stale) { Remove-Item -Recurse -Force -LiteralPath $stale -ErrorAction SilentlyContinue }
        }
        if (Test-Path -LiteralPath $Old) { Die "Could not remove the older backup $Old (in use?). Close it and retry." }
        Info 'Replacing the install folder...'
        Move-WithRetry $InstallDir $Old
    }
    try {
        Move-WithRetry $Staging $InstallDir
    } catch {
        # Put the previous version back: the user keeps a working app.
        if ($Old -and -not (Test-Path -LiteralPath $InstallDir)) { Move-Item -LiteralPath $Old -Destination $InstallDir }
        Die "Could not move the new version into place: $($_.Exception.Message)"
    }
    Remove-Item -Recurse -Force -LiteralPath $Work -ErrorAction SilentlyContinue
    $Exe = Join-Path $InstallDir 'LlamaCode.exe'
    Ok "Installed: $Exe"

    if (-not $NoShortcuts) {
        $name = if ($Channel -eq 'debug') { 'LlamaCode-Debug' } else { 'LlamaCode' }
        $startMenu = if ($StartMenuDir) { $StartMenuDir } else { [Environment]::GetFolderPath('Programs') }
        if (-not $startMenu) { $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs' }
        Set-Shortcut (Join-Path $startMenu "$name.lnk") $Exe $InstallDir
        Ok "Start Menu shortcut: $name"
        Update-LegacyShortcuts $LegacyExe $Exe $InstallDir
    }

    if (-not $NoLaunch) {
        Info 'Launching LlamaCode...'
        $rc = Start-AndCheck $Exe $InstallDir
        if ($rc -ne 0) {
            Write-Host "[ERROR] The new version exited with code $rc right after starting." -ForegroundColor Red
            if ($Old -and (Test-Path -LiteralPath $Old)) {
                Info 'Restoring the previous version...'
                Restore-Previous $InstallDir
                $style = if ($env:LC_TEST_HIDDEN_LAUNCH) { 'Hidden' } else { 'Normal' }
                Start-Process -FilePath $Exe -WorkingDirectory $InstallDir -WindowStyle $style
            }
            Die "Update rolled back: the new version did not start. Log: $LogPath"
        }
    }
    # Working update: a version that failed before is no longer worth keeping.
    if (Test-Path -LiteralPath "$InstallDir.failed") {
        Remove-Item -Recurse -Force -LiteralPath "$InstallDir.failed" -ErrorAction SilentlyContinue
    }
    Write-Host ''
    Ok 'Update complete.'
} catch {
    $UpdateFailed = $true
    $msg = $_.Exception.Message -replace '^LCUPD: ', ''
    Write-Host ''
    Write-Host "[ERROR] $msg" -ForegroundColor Red
    if ($_.Exception.Message -notlike 'LCUPD: *') {
        Write-Host "        at: $($_.InvocationInfo.PositionMessage)" -ForegroundColor DarkGray
    }
    Write-Host "        Log: $LogPath" -ForegroundColor Yellow
} finally {
    if ($Mutex) { try { $Mutex.ReleaseMutex() } catch {}; $Mutex.Dispose() }
    if ($Transcribing) { try { Stop-Transcript | Out-Null } catch {} }
}

# Run as a file (the app, the test): keep a failed window open so the error is
# read, then exit with a code. Under 'irm | iex' never exit (it closes the shell).
if ($PSCommandPath) {
    if ($UpdateFailed) {
        if (-not $NoPause) { try { Read-Host 'Press Enter to close' | Out-Null } catch {} }
        exit 1
    }
    if (-not $NoPause) { Start-Sleep -Seconds 3 }
    exit 0
}
