param(
    [string]$Config = "Debug",
    [string]$ShortcutName = "LlamaCode",
    [string]$Icon = "assets\app_icon.ico",
    [string]$ShortcutPath
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ShortcutPath -or [string]::IsNullOrWhiteSpace($ShortcutPath)) {
    $ShortcutPath = Join-Path $projectRoot "$ShortcutName.lnk"
}

$exePath  = Join-Path $projectRoot "build\$Config\LlamaCode.exe"
$iconPath = Join-Path $projectRoot $Icon

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($ShortcutPath)

if (Test-Path $exePath) {
    $shortcut.TargetPath = $exePath
    $shortcut.Arguments = ""
    $shortcut.WorkingDirectory = Split-Path -Parent $exePath
    # Prefer the standalone .ico so Debug/Release shortcuts visibly differ even
    # if Windows caches the embedded exe icon.
    if (Test-Path $iconPath) {
        $shortcut.IconLocation = "$iconPath,0"
    } else {
        $shortcut.IconLocation = "$exePath,0"
    }
} else {
    $shortcut.TargetPath = "$env:WINDIR\System32\cmd.exe"
    $shortcut.Arguments = "/c start `"`" `".\build\$Config\LlamaCode.exe`""
    $shortcut.WorkingDirectory = $projectRoot
    if (Test-Path $iconPath) {
        $shortcut.IconLocation = "$iconPath,0"
    }
}

$shortcut.Save()

$saved = $wsh.CreateShortcut($ShortcutPath)
[PSCustomObject]@{
    ShortcutPath      = $ShortcutPath
    TargetPath        = $saved.TargetPath
    Arguments         = $saved.Arguments
    WorkingDirectory  = $saved.WorkingDirectory
    IconLocation      = $saved.IconLocation
} | Format-List
