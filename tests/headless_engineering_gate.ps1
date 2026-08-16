param([switch]$Build)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildDir = Join-Path $root "build_tests"
$qtBin = "C:\Qt\6.8.3\msvc2022_64\bin"
$env:QT_QPA_PLATFORM = "offscreen"
$env:PATH = "$qtBin;$env:PATH"

if ($Build) {
    & cmake --build $buildDir --config Debug --target `
        test_engineering_workflows test_task_security_policy test_tasks `
        test_appcontroller test_control_api -- /maxcpucount:1
    if ($LASTEXITCODE -ne 0) { throw "Falló la compilación del gate headless" }
}

$tests = @(
    "test_engineering_workflows",
    "test_task_security_policy",
    "test_tasks",
    "test_appcontroller",
    "test_control_api"
)
foreach ($name in $tests) {
    $exe = Join-Path $buildDir "Debug\$name.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Falta $exe. Ejecutá este script con -Build o tests.bat Debug."
    }
    Write-Host "=== $name ==="
    & $exe -o - -txt
    if ($LASTEXITCODE -ne 0) { throw "$name falló con código $LASTEXITCODE" }
}

& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $PSScriptRoot "headless_engineering_workflows.ps1")
if ($LASTEXITCODE -ne 0) { throw "Falló el smoke HTTP del daemon" }
Write-Host "OK: gate headless de workflows completo"
