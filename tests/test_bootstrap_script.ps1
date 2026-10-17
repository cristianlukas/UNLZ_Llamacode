$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ps  = [IO.File]::ReadAllText((Join-Path $root 'scripts\bootstrap.ps1'))
# SHA-256 via .NET: Get-FileHash vive en un modulo que PowerShell 5.1 no carga
# si lo lanzo PowerShell 7 (hereda su PSModulePath) -> "no se reconoce".
function Get-Sha256Hex([string]$path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($path)
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream)) -replace '-', '').ToLower() }
    finally { $stream.Dispose(); $sha.Dispose() }
}
$sh  = [IO.File]::ReadAllText((Join-Path $root 'scripts\bootstrap.sh'))
$app = [IO.File]::ReadAllText((Join-Path $root 'src\AppController.cpp'))
$qml = [IO.File]::ReadAllText((Join-Path $root 'qml\Main.qml'))
$nav = [IO.File]::ReadAllText((Join-Path $root 'qml\components\NavBar.qml'))
$fails = 0

function Check([bool]$condition, [string]$message) {
    if ($condition) { Write-Host "  PASS $message" }
    else { Write-Host "  FAIL $message" -ForegroundColor Red; $script:fails++ }
}

Write-Host '== bootstrap / actualizar ahora =='

# El detector consulta cristianlukas; si el bootstrap clona otro repo, "actualizar"
# baja codigo que no es el que disparo el aviso.
Check (-not $ps.Contains('guideahon')) 'bootstrap.ps1 no apunta al repo viejo'
Check (-not $sh.Contains('guideahon')) 'bootstrap.sh no apunta al repo viejo'
Check ($ps.Contains('cristianlukas/UNLZ_Llamacode')) 'bootstrap.ps1 clona el repo publicado'
Check ($sh.Contains('cristianlukas/UNLZ_Llamacode')) 'bootstrap.sh clona el repo publicado'

# El bootstrap debe instalar y verificar los componentes Qt declarados por CMake.
Check ($ps.Contains("`$QtAqtModules = @('qtmultimedia')")) 'instala el add-on Qt Multimedia'
# qtsvg NO es add-on en Qt 6 (viene en la base): pedirlo rompe aqt en una maquina limpia.
Check (-not ($ps -match "QtAqtModules = @\([^)]*'qtsvg'")) 'no pide qtsvg como modulo aqt'
Check ($ps.Contains("'Svg'")) 'igual verifica que Svg quede instalado'
Check ($ps.Contains("'QuickControls2'")) 'verifica Qt Quick Controls 2 requerido por CMake'
Check ($ps.Contains('windeployqt failed with exit code')) 'aborta si falla el deploy del runtime Qt'
Check ($ps.Contains("`$env:LC_FORCE -ne '1'")) 'sólo permite el reset destructivo con LC_FORCE=1'

# LC_DIR viene del app con la instalacion que corre; sin el guard, el
# reset --hard se lleva puesto lo no commiteado de ese checkout.
Check ($ps -match 'git -C \$Dir status --porcelain') 'chequea si el destino tiene cambios sin commitear'
$dirtyIdx = $ps.IndexOf('status --porcelain')
$resetIdx = $ps.IndexOf('git -C $Dir reset --hard')   # el comando, no el comentario
Check ($dirtyIdx -gt 0 -and $dirtyIdx -lt $resetIdx) 'el chequeo corre ANTES del reset --hard'
Check ($ps.Contains('LC_FORCE')) 'se puede forzar explicitamente con LC_FORCE'

# Matar la app antes de configurar dejaba al usuario sin app cuando algo fallaba.
$stopIdx      = $ps.IndexOf('Stop-LlamaCodeProcesses' + [Environment]::NewLine)
$configureIdx = $ps.IndexOf('Info "Configuring..."')
$buildIdx     = $ps.IndexOf('Info "Building ($Config)..."')
Check ($configureIdx -gt 0 -and $buildIdx -gt $configureIdx) 'configure y build en orden'
Check ($stopIdx -gt $configureIdx -and $stopIdx -lt $buildIdx) 'la app se cierra recien antes del build'

# Con 'irm | iex' el script corre en la sesion del usuario: un 'exit' cierra la
# terminal y el error se pierde (le paso a un usuario: "instalo cosas y se cerro").
$body = $ps.Substring($ps.IndexOf('$LogPath = '))
$bodyNoFinal = $body.Substring(0, $body.LastIndexOf('if ($BootstrapFailed -and $RunAsFile) { exit 1 }'))
Check (-not ($bodyNoFinal -match '(?m)^\s*[^#\r\n]*\bexit\s+\d')) 'ningun exit dentro del cuerpo (solo el final, y solo corrido como archivo)'
Check ($ps -match 'function Die\(\$m\)\s*\{\s*throw') 'Die lanza en vez de salir'
Check ($ps.Contains('$RunAsFile = [bool]$PSCommandPath')) 'distingue iex de -File'
# El alias de la Microsoft Store pasa Get-Command pero no es Python.
Check ($ps.Contains("-like '*\WindowsApps\*'")) 'descarta el alias python de la Microsoft Store'
Check (-not ($ps -match '(?m)^\s*python -m')) 'usa el Python verificado ($Py), no el del PATH'
Check ($ps.Contains('aqt install-qt failed')) 'aborta con mensaje si falla aqt'

# El bootstrap hace 'git clone' en Windows: un solo path trackeado invalido en
# NTFS (salto de linea, < > : " | ? *, punto/espacio final) hace fallar el
# checkout y nadie puede instalar. Paso con receipts de benchmark cuyo nombre
# arrastraba '\n</prod>'.
$tracked = (& git -C $root ls-files -z) -split "`0" | Where-Object { $_ }
$badPaths = @($tracked | Where-Object { $_ -match '[\x00-\x1f<>:"|?*]|[ .]$|[ .]/' })
Check ($badPaths.Count -eq 0) "todos los paths trackeados son validos en Windows ($($badPaths.Count) invalidos)"
$badPaths | Select-Object -First 5 | ForEach-Object { Write-Host "        $_" -ForegroundColor Red }

# artifacts/ tiene rutas de ~240 chars; bajo %USERPROFILE% superan MAX_PATH.
Check ($ps.Contains('git -c core.longpaths=true clone')) 'clona con core.longpaths (rutas > 260)'
Check ($ps.Contains('git -C $Dir config core.longpaths true')) 'deja core.longpaths en el checkout para updates'

# Debug enlaza Qt release en MSVC: windeployqt --debug deja el exe sin DLLs.
Check (-not $ps.Contains("'--debug'")) 'no fuerza windeployqt --debug (Debug usa Qt release)'
Check ($ps.Contains('windeployqt.exe" @DeployFlag')) 'en Debug deja que windeployqt detecte las DLL del exe'

# Linux: probado en WSL (Ubuntu 24.04 limpio).
# Multimedia es add-on de aqt; sin pedirlo CMake no encuentra Qt6Multimedia.
Check ($sh.Contains('QT_AQT_MODULES=(qtmultimedia)')) 'bootstrap.sh instala el add-on Qt Multimedia'
Check ($sh.Contains('--modules "${QT_AQT_MODULES[@]}"')) 'bootstrap.sh le pasa los modulos a aqt'
Check ($sh.Contains('QT_REQUIRED_COMPONENTS=(Core Quick QuickControls2 Sql Concurrent Network Widgets Multimedia Svg)')) 'bootstrap.sh verifica los componentes Qt que pide CMake'
# libQt6Multimedia.so tiene NEEDED libpulse.so.0: sin ella falla el link (pa_*@PULSE_0).
Check ($sh -match 'libdbus-1-3 libpulse0') 'apt instala libpulse0'
Check ($sh.Contains('pulseaudio-libs')) 'dnf instala pulseaudio-libs'
Check ($sh -match 'dbus libpulse libsecret') 'pacman instala libpulse'
# La app no hereda la terminal: si no, su log ensucia el prompt y muere al cerrarla.
Check ($sh.Contains('setsid nohup "$EXE" ) >"$APP_LOG" 2>&1 </dev/null &')) 'bootstrap.sh lanza la app desacoplada de la terminal (redireccion sobre todo el bloque)'

# El instalador por defecto instala Prod (Release); Debug es opt-in (LC_CONFIG=Debug).
Check ($ps.Contains("`$Config  = if (`$env:LC_CONFIG) { `$env:LC_CONFIG } else { 'Release' }")) 'bootstrap.ps1 instala Release (Prod) por defecto'
Check ($sh.Contains('CONFIG="${LC_CONFIG:-Release}"')) 'bootstrap.sh instala Release (Prod) por defecto'

# Lado del app.
Check ($app.Contains('installRootForExePath(QCoreApplication::applicationFilePath())')) 'el app calcula la raiz de instalacion'
Check ($app -match '\$env:LC_DIR=') 'el app le pasa LC_DIR al bootstrap'
Check ($app.Contains('launcher.setCreateProcessArgumentsModifier(showInNewConsole)')) 'la consola del update es visible (Qt la lanzaba con CREATE_NO_WINDOW)'
Check ($app.Contains('args->inheritHandles = FALSE')) 'la consola del update no hereda los std handles nulos de la app'
Check ($app.Contains('QStringLiteral("-NoExit")')) 'la consola del update queda abierta para ver el error'
Check ($app.Contains('updateStarted = launcher.startDetached()')) 'confirma que el bootstrap arranco antes de cerrar la app'
Check ($nav.Contains('visible: Qt.platform.os === "windows" && App.updateAvailable')) 'muestra el boton junto a Configuracion solo si Windows detecta una release nueva'
$settingsLabel = $nav.IndexOf('text: (App.langV, App.l("nav.settings"))')
$updateButton = $nav.IndexOf('visible: Qt.platform.os === "windows" && App.updateAvailable')
Check ($settingsLabel -gt 0 -and $updateButton -gt $settingsLabel) 'ubica el boton en la fila de Configuracion'
Check ($nav.Contains('root.updateRequested()')) 'el boton de la barra lateral solicita actualizar'
Check ($qml.Contains('window.forceQuit = true')) 'el boton permite salir aunque cerrar normalmente minimice a la bandeja'
Check ($qml.Contains('onUpdateRequested: App.updateToLatest()')) 'el boton re-chequea la ultima release antes de actualizar'
Check ($qml.Contains('function onUpdateLaunchFinished(started)')) 'la app se cierra solo si el update arranco'
Check ($qml.Contains('App.updateAvailable && Qt.platform.os !== "windows"')) 'mantiene el popup de releases para otras plataformas'
Check ($ps.Contains('Local\LlamaCodeBootstrap')) 'un solo bootstrap a la vez (mutex)'
Check ($ps.Contains('$BootstrapMutex.ReleaseMutex()')) 'libera el mutex al terminar'

Write-Host '== update-binary.ps1 (Actualizar con binario precompilado) =='
$ub = Join-Path $root 'scripts\update-binary.ps1'
$ubText = [IO.File]::ReadAllText($ub)
$ubBytes = [IO.File]::ReadAllBytes($ub)
Check (@($ubBytes | Where-Object { $_ -gt 127 }).Count -eq 0) 'update-binary.ps1 es ASCII puro (PS 5.1 lo lee como ANSI)'
foreach ($f in 'scripts\package-windows.ps1') {
    $b = [IO.File]::ReadAllBytes((Join-Path $root $f))
    Check (@($b | Where-Object { $_ -gt 127 }).Count -eq 0) "$f es ASCII puro"
}
# Mismo nombre de asset en los tres lados (CI, app, actualizador).
$wf = [IO.File]::ReadAllText((Join-Path $root '.github\workflows\release-binaries.yml'))
Check ($ubText.Contains('"LlamaCode-$tag-windows-x64.zip"')) 'el actualizador busca LlamaCode-<tag>-windows-x64.zip'
Check ($app.Contains('LlamaCode-%1-windows-x64.zip')) 'el app elige el mismo nombre'
Check ($wf.Contains('LlamaCode-$env:TAG-windows-x64.zip')) 'el CI sube el mismo nombre'
Check ($ubText.Contains("'Local\LlamaCodeBootstrap'")) 'comparte el mutex con bootstrap.ps1 (un update a la vez)'
# PS 5.1: @(Invoke-RestMethod) envuelve el array JSON en UN elemento y el
# instalador standalone no encontraba ninguna release (paso con v0.1.127-debug).
Check (-not ($ubText -match '@\(\s*Invoke-RestMethod')) 'no envuelve Invoke-RestMethod en @() (array de un elemento en PS 5.1)'
Check ($app.Contains('launcher.setCreateProcessArgumentsModifier(showInNewConsole);' + "`n" + '    return launcher.startDetached();') -or
       ($app -match 'showInNewConsole\);\s*\r?\n\s*return launcher\.startDetached\(\);')) 'el update binario corre en una consola visible'

$tmp = Join-Path ([IO.Path]::GetTempPath()) ('lc-ub-test-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    function New-FakePackage([string]$name, [string]$content) {
        $pkg = Join-Path $tmp "pkg-$name"
        New-Item -ItemType Directory -Force -Path $pkg | Out-Null
        Copy-Item (Join-Path $env:WINDIR 'System32\where.exe') (Join-Path $pkg 'LlamaCode.exe')
        Set-Content -Path (Join-Path $pkg 'version.txt') -Value $content -Encoding ASCII
        $zip = Join-Path $tmp "$name.zip"
        [IO.Compression.ZipFile]::CreateFromDirectory($pkg, $zip)
        $h = Get-Sha256Hex $zip
        [IO.File]::WriteAllText("$zip.sha256", "$h  $name.zip`n")
        return @{ Zip = $zip; Hash = $h }
    }
    function Invoke-Updater([string[]]$extra) {
        $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $ub @extra -NoLaunch -NoShortcuts -NoPause 2>&1 | Out-String
        return @{ Code = $LASTEXITCODE; Out = $out }
    }
    $install = Join-Path $tmp 'Programs\LlamaCode'
    New-Item -ItemType Directory -Force -Path $install | Out-Null
    Set-Content -Path (Join-Path $install 'version.txt') -Value 'v1' -Encoding ASCII
    Set-Content -Path (Join-Path $install 'stale.dll') -Value 'x' -Encoding ASCII

    # 1) Hash correcto (por .sha256): reemplaza la carpeta entera.
    $v2 = New-FakePackage 'v2' 'v2'
    $r = Invoke-Updater @('-AssetUrl', $v2.Zip, '-Sha256Url', "$($v2.Zip).sha256", '-InstallDir', $install)
    Check ($r.Code -eq 0) "instala con hash verificado (exit $($r.Code))"
    Check ((Get-Content (Join-Path $install 'version.txt')) -eq 'v2') 'la carpeta queda con la version nueva'
    Check (-not (Test-Path (Join-Path $install 'stale.dll'))) 'no quedan archivos de la version vieja (swap de carpeta, no merge)'
    Check (-not (Test-Path "$install.old") -and -not (Test-Path "$install.new")) 'no deja .old ni .new'

    # 2) Hash equivocado: no toca nada.
    $v3 = New-FakePackage 'v3' 'v3'
    $r = Invoke-Updater @('-AssetUrl', $v3.Zip, '-Sha256', ('0' * 64), '-InstallDir', $install)
    Check ($r.Code -eq 1) 'hash equivocado sale 1'
    Check ($r.Out -match 'SHA-256 mismatch') 'explica que el hash no coincide'
    Check ((Get-Content (Join-Path $install 'version.txt')) -eq 'v2') 'con hash equivocado la instalacion queda intacta'

    # 3) Sin hash: se niega a instalar sin verificar.
    $r = Invoke-Updater @('-AssetUrl', $v3.Zip, '-InstallDir', $install)
    Check ($r.Code -eq 1 -and $r.Out -match 'unverified') 'sin SHA-256 no instala'
    Check ((Get-Content (Join-Path $install 'version.txt')) -eq 'v2') 'sin hash la instalacion queda intacta'

    # 4) Paquete sin LlamaCode.exe en la raiz: no reemplaza.
    $bad = Join-Path $tmp 'bad'; New-Item -ItemType Directory -Force -Path (Join-Path $bad 'sub') | Out-Null
    Set-Content -Path (Join-Path $bad 'sub\x.txt') -Value 'x'
    $badZip = Join-Path $tmp 'bad.zip'; [IO.Compression.ZipFile]::CreateFromDirectory($bad, $badZip)
    $r = Invoke-Updater @('-AssetUrl', $badZip, '-Sha256', (Get-Sha256Hex $badZip), '-InstallDir', $install)
    Check ($r.Code -eq 1 -and $r.Out -match 'no LlamaCode.exe') 'rechaza un paquete sin LlamaCode.exe'
    Check ((Get-Content (Join-Path $install 'version.txt')) -eq 'v2') 'con paquete roto la instalacion queda intacta'

    # 5) Migracion: carpeta destino inexistente (checkout -> Programs).
    $fresh = Join-Path $tmp 'Programs\LlamaCode-Debug'
    $r = Invoke-Updater @('-AssetUrl', $v3.Zip, '-Sha256', $v3.Hash.ToUpper(), '-InstallDir', $fresh, '-Channel', 'debug')
    Check ($r.Code -eq 0 -and (Test-Path (Join-Path $fresh 'LlamaCode.exe'))) 'instala en una carpeta nueva (migracion desde checkout)'

    # 6) 'irm | iex' (instalador standalone): sin param, por variables de entorno, sin exit.
    #    Bajo iex no hay -NoShortcuts: el acceso va a LC_START_MENU_DIR. Antes iba
    #    al menu Inicio REAL y dejaba LlamaCode.lnk apuntando a un exe en TEMP.
    $iexDir = Join-Path $tmp 'iex'
    $fakeStartMenu = Join-Path $tmp 'StartMenu'
    $realStartMenu = [Environment]::GetFolderPath('Programs')
    function Get-RealStartMenuLinks {
        if (-not $realStartMenu -or -not (Test-Path $realStartMenu)) { return @() }
        $w = New-Object -ComObject WScript.Shell
        @(Get-ChildItem -LiteralPath $realStartMenu -Filter '*.lnk' -ErrorAction SilentlyContinue | ForEach-Object {
            "$($_.Name)|$($_.LastWriteTimeUtc.Ticks)|$($w.CreateShortcut($_.FullName).TargetPath)"
        })
    }
    $realBefore = (Get-RealStartMenuLinks) -join "`n"
    $cmd = "`$env:LC_ASSET_URL='$($v2.Zip)'; `$env:LC_SHA256='$($v2.Hash)'; `$env:LC_INSTALL_DIR='$iexDir'; `$env:LC_NORUN='1'; " +
           "`$env:LC_START_MENU_DIR='$fakeStartMenu'; Get-Content -Raw '$ub' | iex; 'IEX-SURVIVED'"
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -Command $cmd 2>&1 | Out-String
    Check ($out -match 'IEX-SURVIVED') 'bajo iex no cierra la sesion (sin exit)'
    Check ((Get-Content (Join-Path $iexDir 'version.txt') -ErrorAction SilentlyContinue) -eq 'v2') 'bajo iex instala desde LC_ASSET_URL/LC_SHA256'
    $fakeLnk = Join-Path $fakeStartMenu 'LlamaCode.lnk'
    $fakeTarget = if (Test-Path $fakeLnk) { (New-Object -ComObject WScript.Shell).CreateShortcut($fakeLnk).TargetPath } else { '' }
    Check ($fakeTarget -ieq (Join-Path $iexDir 'LlamaCode.exe')) 'LC_START_MENU_DIR recibe el acceso del menu Inicio'
    $realAfter = (Get-RealStartMenuLinks) -join "`n"
    Check ($realAfter -eq $realBefore) 'el menu Inicio real queda intacto'
    Check (-not ($realAfter -match [regex]::Escape($tmp))) 'ningun acceso del menu Inicio real apunta al TEMP del test'
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

if ($fails) { throw "$fails bootstrap regression(s) failed" }
Write-Host 'All bootstrap regressions passed.'
