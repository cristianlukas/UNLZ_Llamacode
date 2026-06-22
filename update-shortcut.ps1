param(
    [string]$Config = "Debug",
    [string]$ShortcutName = "LlamaCode",
    [string]$Icon = "assets\app_icon.ico",
    [string]$ShortcutPath
)

$AppUserModelId = "LlamaCode.Desktop.App"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ShortcutPath -or [string]::IsNullOrWhiteSpace($ShortcutPath)) {
    $ShortcutPath = Join-Path $projectRoot "$ShortcutName.lnk"
}

$exePath  = Join-Path $projectRoot "build\$Config\LlamaCode.exe"
$iconPath = Join-Path $projectRoot $Icon

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[ComImport]
[Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPropertyStore
{
    void GetCount(out uint cProps);
    void GetAt(uint iProp, out PROPERTYKEY pkey);
    void GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);
    void SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);
    void Commit();
}

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public struct PROPERTYKEY
{
    public Guid fmtid;
    public uint pid;
}

[StructLayout(LayoutKind.Explicit)]
public struct PROPVARIANT
{
    [FieldOffset(0)] public ushort vt;
    [FieldOffset(8)] public IntPtr p;

    public static PROPVARIANT FromString(string value)
    {
        return new PROPVARIANT
        {
            vt = 31, // VT_LPWSTR
            p = Marshal.StringToCoTaskMemUni(value)
        };
    }
}

public static class LlamaCodeShortcutPropertyStore
{
    private const uint GPS_READWRITE = 0x00000002;

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    private static extern void SHGetPropertyStoreFromParsingName(
        [MarshalAs(UnmanagedType.LPWStr)] string pszPath,
        IntPtr pbc,
        uint flags,
        ref Guid riid,
        [MarshalAs(UnmanagedType.Interface)] out IPropertyStore propertyStore);

    [DllImport("ole32.dll")]
    private static extern int PropVariantClear(ref PROPVARIANT pvar);

    public static void SetAppUserModelId(string shortcutPath, string appUserModelId)
    {
        IPropertyStore propertyStore = null;
        try
        {
            var propertyStoreId = new Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99");
            SHGetPropertyStoreFromParsingName(shortcutPath, IntPtr.Zero, GPS_READWRITE, ref propertyStoreId, out propertyStore);

            var key = new PROPERTYKEY
            {
                fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
                pid = 5
            };
            var value = PROPVARIANT.FromString(appUserModelId);
            try
            {
                propertyStore.SetValue(ref key, ref value);
                propertyStore.Commit();
            }
            finally
            {
                PropVariantClear(ref value);
            }
        }
        finally
        {
            if (propertyStore != null)
                Marshal.ReleaseComObject(propertyStore);
        }
    }
}
"@

function Set-LlamaCodeShortcutAppId {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path $Path) {
        [LlamaCodeShortcutPropertyStore]::SetAppUserModelId($Path, $AppUserModelId)
    }
}

function Update-LlamaCodeShortcutFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    $shortcut = $wsh.CreateShortcut($Path)

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
    Set-LlamaCodeShortcutAppId -Path $Path
}

$wsh = New-Object -ComObject WScript.Shell
Update-LlamaCodeShortcutFile -Path $ShortcutPath

$updatedPinnedShortcuts = @()
$taskbarDir = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
if ((Test-Path $exePath) -and (Test-Path $taskbarDir)) {
    $expectedTarget = [System.IO.Path]::GetFullPath($exePath)
    Get-ChildItem -LiteralPath $taskbarDir -Filter "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
        $pinned = $wsh.CreateShortcut($_.FullName)
        if (-not [string]::IsNullOrWhiteSpace($pinned.TargetPath)) {
            $pinnedTarget = [System.IO.Path]::GetFullPath($pinned.TargetPath)
            if ([string]::Equals($pinnedTarget, $expectedTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
                Update-LlamaCodeShortcutFile -Path $_.FullName
                $updatedPinnedShortcuts += $_.FullName
            }
        }
    }
}

$saved = $wsh.CreateShortcut($ShortcutPath)
[PSCustomObject]@{
    ShortcutPath      = $ShortcutPath
    TargetPath        = $saved.TargetPath
    Arguments         = $saved.Arguments
    WorkingDirectory  = $saved.WorkingDirectory
    IconLocation      = $saved.IconLocation
    AppUserModelID    = $AppUserModelId
    UpdatedPinned     = $updatedPinnedShortcuts
} | Format-List
