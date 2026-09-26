$ErrorActionPreference = 'Stop'

$benchmark = Join-Path $PSScriptRoot '..\tools\benchmark_ling_cpu.ps1'
$output = @(& $benchmark -SelfTest)
if ($output -notcontains 'SELFTEST PASS: scorer, documentos sintéticos, agregación y matriz Q4/Q6 × 4k/8k × thinking on/off.') {
    throw "La auto-prueba del benchmark no pasó: $($output -join ' ')"
}

$guarded = $false
try {
    & $benchmark | Out-Null
} catch {
    $guarded = $_.Exception.Message -match 'Falta -ServerPath'
}
if (-not $guarded) { throw 'El benchmark debe exigir runtime y dos archivos de modelo antes de comenzar.' }

Write-Output 'PASS: benchmark Ling CPU self-test y guardas de entrada.'
