@echo off
setlocal
rem ── LlamaCode launcher ──────────────────────────────────────────────────────
rem Double-click THIS instead of build\Debug\LlamaCode.exe.
rem If a BUILD_PENDING flag exists (set whenever source changed), it rebuilds
rem Debug first, clears the flag on success, then launches the app. Otherwise it
rem launches the existing exe directly.
cd /d "%~dp0"

set "FLAG=%~dp0BUILD_PENDING"
set "EXE=%~dp0build\Debug\LlamaCode.exe"

if exist "%FLAG%" (
    echo [LlamaCode] BUILD_PENDING detectado. Recompilando Debug...
    cmake --build build --config Debug --parallel
    if errorlevel 1 (
        echo.
        echo [LlamaCode] BUILD FALLIDO. No se borra el flag. Revisa los errores arriba.
        pause
        exit /b 1
    )
    del "%FLAG%" >nul 2>&1
    echo [LlamaCode] Build OK. Flag borrado.
) else (
    echo [LlamaCode] Sin rebuild pendiente. Abriendo app...
)

if not exist "%EXE%" (
    echo [LlamaCode] No existe el exe: "%EXE%". Forzando build...
    cmake --build build --config Debug --parallel || ( pause & exit /b 1 )
)

start "" "%EXE%"
endlocal
