<#
  test_session_guard.ps1 - regresion de los hooks de convivencia (tools/session_guard.ps1).

  No corre en ctest (es infra de harness en PS, no C++). Correr a mano:
      powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_session_guard.ps1
  Exit 0 = todo verde.

  Lo que mas importa aca NO es que bloquee, sino que NO bloquee de mas: un guard
  que se come 'git checkout -- <path>' (la salida segura que el propio guard
  recomienda) o 'git status' se desactiva a los dos dias y no protege nada.
#>
$ErrorActionPreference = 'Stop'
$root  = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$guard = Join-Path $root 'tools\session_guard.ps1'
$claimDir = Join-Path $root '.buildlock\claims'
$fails = 0
function Ok($cond,$msg){ if($cond){Write-Host "  PASS $msg"}else{Write-Host "  FAIL $msg" -Foreground Red; $script:fails++} }

# El guard solo actua si el tree tiene trabajo sin commitear: garantizo esa
# condicion con un probe propio (y lo saco al final).
$probe = Join-Path $root 'tests\_guard_probe.tmp'
'probe de test_session_guard' | Set-Content $probe -Encoding ASCII

# Corre el guard con un JSON por stdin y devuelve la salida cruda.
function RunGuard([string]$mode, $payload) {
    $json = ($payload | ConvertTo-Json -Depth 5 -Compress)
    $out = ($json | & powershell -NoProfile -ExecutionPolicy Bypass -File $guard -Mode $mode 2>&1) | Out-String
    return $out.Trim()
}
function GitGuard([string]$cmd) {
    return RunGuard 'git-guard' @{ session_id='s1'; tool_name='Bash'; tool_input=@{ command=$cmd } }
}

Write-Host "== test 0: los scripts de infra son ASCII puro =="
# Windows PowerShell 5.1 lee un .ps1 sin BOM como ANSI. Un caracter UTF-8 dentro
# de un STRING se decodifica mal y puede terminar el string: el em-dash (E2 80 94)
# da 'a EUR "' en CP1252, y ese ultimo byte es una comilla -> ParserError y el
# hook muere entero. En comentarios solo se ve feo; en strings rompe. Los hooks
# corren bajo el host que el harness elija, asi que: ASCII puro, sin excepciones.
foreach ($f in @('tools\session_guard.ps1','worktree.ps1','build_coord.ps1')) {
    $txt = [IO.File]::ReadAllText((Join-Path $root $f))
    $bad = [regex]::Matches($txt, '[^\x00-\x7F]')
    $sample = if ($bad.Count) { " (primero: '" + $bad[0].Value + "')" } else { '' }
    Ok ($bad.Count -eq 0) "$f sin caracteres no-ASCII$sample"
}

Write-Host "== test 1: git-guard BLOQUEA lo que barre el tree entero =="
foreach ($c in @(
    'git checkout -- .',
    'git checkout .',
    'git restore .',
    'git reset --hard origin/main',
    'git clean -fd',
    'git stash',
    'git add -A',
    'git add .'
)) {
    $o = GitGuard $c
    Ok ($o -match '"permissionDecision":"deny"') "bloquea: $c"
}

Write-Host "== test 2: git-guard DEJA PASAR lo seguro (no bloquear de mas) =="
foreach ($c in @(
    'git checkout -- src/core/agent/LlamaAgentBackend.cpp',  # por path = la salida recomendada
    'git restore --staged src/foo.cpp',                      # solo desestagea, no destruye
    'git add src/foo.cpp tests/bar.cpp',                     # por path
    'git status --porcelain',
    'git log --oneline -5',
    'git stash list',
    'git checkout -b session/nueva-rama',                    # crear rama no descarta nada
    'git diff',
    'cmake --build build --config Release'
)) {
    $o = GitGuard $c
    Ok (-not ($o -match 'deny')) "deja pasar: $c"
}

Write-Host "== test 3: git-guard explica como seguir =="
# Asertar sobre el JSON crudo da falsos negativos: ConvertTo-Json escapa '<' como
# < y codifica los saltos como '\n'. El consumidor parsea el JSON, asi que lo
# que importa es el string YA DECODIFICADO.
$reason = (GitGuard 'git checkout -- .' | ConvertFrom-Json).hookSpecificOutput.permissionDecisionReason
Ok ($reason -match 'worktree\.ps1')          "el bloqueo sugiere aislarse en un worktree"
Ok ($reason -match 'git add <path1>')        "el bloqueo ofrece la alternativa por path"
Ok ($reason -match 'git checkout -- <tu/archivo>') "el bloqueo ofrece revertir por path"
# El bug que esto caza: escribir "\n" en un string de PowerShell no produce un
# salto (es backslash-n literal); hay que usar backtick-n.
Ok (-not ($reason -match '\\n'))             "sin backslash-n literal en el texto decodificado"
Ok ($reason -match "`n")                     "los saltos son saltos de verdad"

Write-Host "== test 4: edit-claim avisa solo si OTRA sesion viva toco el archivo =="
if (Test-Path $claimDir) { Remove-Item -Recurse -Force $claimDir -ErrorAction SilentlyContinue }
$target = Join-Path $root 'src\core\agent\LlamaAgentBackend.cpp'
$o1 = RunGuard 'edit-claim' @{ session_id='sess-A'; tool_name='Edit'; tool_input=@{ file_path=$target } }
Ok (-not ($o1 -match 'OJO')) "primera sesion en tocar el archivo: sin aviso"
$o2 = RunGuard 'edit-claim' @{ session_id='sess-A'; tool_name='Edit'; tool_input=@{ file_path=$target } }
Ok (-not ($o2 -match 'OJO')) "la MISMA sesion re-editando: sin aviso (no se avisa a si misma)"
$o3 = RunGuard 'edit-claim' @{ session_id='sess-B'; tool_name='Edit'; tool_input=@{ file_path=$target } }
Ok ($o3 -match 'OJO: otra sesion edito') "otra sesion sobre el mismo archivo: avisa"
Ok ($o3 -match 'additionalContext')       "el aviso entra como additionalContext"
Ok (-not ($o3 -match 'deny'))             "avisa pero NO bloquea (decision del usuario)"
$other = Join-Path $root 'src\core\agent\SubAgentRunner.cpp'
$o4 = RunGuard 'edit-claim' @{ session_id='sess-B'; tool_name='Edit'; tool_input=@{ file_path=$other } }
Ok (-not ($o4 -match 'OJO')) "archivo distinto: sin aviso (el claim es por archivo, no por sesion)"

Write-Host "== test 5: edit-claim ignora claims stale (sesion muerta no traba a nadie) =="
Get-ChildItem $claimDir -Filter 'sess-A__*' -File | ForEach-Object {
    $_.LastWriteTime = (Get-Date).AddMinutes(-120)   # mas viejo que $staleMin (90)
}
Get-ChildItem $claimDir -Filter 'sess-B__*' -File | Remove-Item -Force
$o5 = RunGuard 'edit-claim' @{ session_id='sess-C'; tool_name='Edit'; tool_input=@{ file_path=$target } }
Ok (-not ($o5 -match 'OJO')) "claim de hace 2h no genera aviso"

Write-Host "== test 6: session-start avisa si el tree ya tiene trabajo en curso =="
$o6 = RunGuard 'session-start' @{ session_id='sess-D' }
Ok ($o6 -match 'sin commitear')   "lista que hay trabajo sin commitear"
Ok ($o6 -match 'worktree\.ps1')   "sugiere el worktree"
Ok ($o6 -match 'SessionStart')    "emite el hookEventName correcto"

# Limpieza
Remove-Item $probe -Force -ErrorAction SilentlyContinue
if (Test-Path $claimDir) { Remove-Item -Recurse -Force $claimDir -ErrorAction SilentlyContinue }

Write-Host ""
if($fails -eq 0){ Write-Host "=== ALL SESSION-GUARD TESTS PASSED ===" -Foreground Green; exit 0 }
else { Write-Host "=== $fails SESSION-GUARD TEST(S) FAILED ===" -Foreground Red; exit 1 }
