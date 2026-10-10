$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ps  = [IO.File]::ReadAllText((Join-Path $root 'scripts\bootstrap.ps1'))
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
Check ($ps.Contains("`$QtAqtModules = @('qtmultimedia', 'qtsvg')")) 'instala los add-ons Qt Multimedia y Svg'
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

# Lado del app.
Check ($app.Contains('installRootForExePath(QCoreApplication::applicationFilePath())')) 'el app calcula la raiz de instalacion'
Check ($app -match '\$env:LC_DIR=') 'el app le pasa LC_DIR al bootstrap'
Check ($app.Contains('QStringLiteral("-NoExit")')) 'la consola del update queda abierta para ver el error'
Check ($app.Contains('updateStarted = QProcess::startDetached')) 'confirma que el bootstrap arranco antes de cerrar la app'
Check ($nav.Contains('visible: Qt.platform.os === "windows" && App.updateAvailable')) 'muestra el boton junto a Configuracion solo si Windows detecta una release nueva'
$settingsLabel = $nav.IndexOf('text: (App.langV, App.l("nav.settings"))')
$updateButton = $nav.IndexOf('visible: Qt.platform.os === "windows" && App.updateAvailable')
Check ($settingsLabel -gt 0 -and $updateButton -gt $settingsLabel) 'ubica el boton en la fila de Configuracion'
Check ($nav.Contains('root.updateRequested()')) 'el boton de la barra lateral solicita actualizar'
Check ($qml.Contains('window.forceQuit = true')) 'el boton permite salir aunque cerrar normalmente minimice a la bandeja'
Check ($qml.Contains('App.handleUpdateDecision("updateNow")')) 'el boton ejecuta el flujo de instalacion existente'
Check ($qml.Contains('App.updateAvailable && Qt.platform.os !== "windows"')) 'mantiene el popup de releases para otras plataformas'

if ($fails) { throw "$fails bootstrap regression(s) failed" }
Write-Host 'All bootstrap regressions passed.'
