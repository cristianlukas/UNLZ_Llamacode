<#
  session_guard.ps1 - hooks de convivencia entre sesiones que comparten el tree.

  El problema: build_coord.ps1 serializa builds y worktree.ps1 aisla trees, pero
  las dos son opt-in - hay que ACORDARSE de usarlas. Los choques reales (dos
  sesiones editando el mismo archivo, un `git checkout --` que se come trabajo
  ajeno, "modified on disk") pasan antes y sin que nadie se acuerde de nada. Los
  hooks los ejecuta el harness solo, asi que son el unico lugar donde esto se
  aplica sin disciplina humana.

  Tres modos (los engancha .claude/settings.json):

    -Mode session-start   SessionStart. Si el tree ya tiene trabajo sin commitear,
                          lo lista y sugiere aislarse en un worktree. Informativo.

    -Mode edit-claim      PreToolUse(Edit|Write). Registra que esta sesion toca el
                          archivo y avisa si otra sesion VIVA lo toco antes.
                          Avisa, NO bloquea: un claim stale no debe trabar trabajo
                          legitimo, y el costo de un choque de edicion es un merge,
                          no una perdida.

    -Mode git-guard       PreToolUse(Bash|PowerShell). BLOQUEA git destructivo
                          (checkout --/restore/stash/reset --hard/clean/add -A)
                          cuando el tree tiene trabajo sin commitear. Este si
                          bloquea: es el unico caso irreversible - si se lleva
                          puesto el trabajo de otra sesion no hay undo. Un falso
                          positivo cuesta un rodeo (hacerlo por path); un falso
                          negativo cuesta horas ajenas.

  Contrato de hooks: el input llega por stdin como JSON; la salida es JSON por
  stdout. Exit 0 siempre (un hook que revienta no debe romper la sesion).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('session-start','edit-claim','git-guard')] [string]$Mode
)

# Un hook nunca debe tumbar la sesion: ante cualquier sorpresa, salir en silencio.
$ErrorActionPreference = 'Continue'

$root      = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$claimDir  = Join-Path $root '.buildlock\claims'
$staleMin  = 90     # un claim mas viejo que esto ya no representa a nadie

function Git-Run() {
    $ErrorActionPreference = 'Continue'
    $out = & git -C $root @args 2>&1
    return [pscustomobject]@{ rc = $LASTEXITCODE; out = ($out | Out-String).Trim() }
}

# Como Git-Run pero devuelve las lineas crudas, SIN Trim() global. Para
# --porcelain el Trim() es destructivo: el formato es 'XY <path>' y X puede ser un
# espacio (' M CMakeLists.txt'), asi que trimear el blob entero le come el espacio
# a la PRIMERA linea y despues el parser se lleva puesta la primera letra del path
# ('CMakeLists.txt' -> 'MakeLists.txt').
function Git-Lines() {
    $ErrorActionPreference = 'Continue'
    $out = & git -C $root @args 2>&1
    if ($LASTEXITCODE -ne 0) { return @() }
    return @($out | ForEach-Object { [string]$_ })
}

# Archivos con cambios sin commitear (tracked + untracked), como lista de paths.
function Get-DirtyPaths() {
    return @(Git-Lines status --porcelain | ForEach-Object {
        $line = $_.TrimEnd()
        if ($line -match '^(..)\s(.+)$') {
            $p = $Matches[2].Trim().Trim('"')
            # Renombres vienen como 'old -> new': nos interesa el destino.
            if ($p -match '\s->\s(.+)$') { $p = $Matches[1].Trim().Trim('"') }
            $p
        }
    } | Where-Object { $_ })
}

function Read-StdinJson() {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { return $null }
    try { return $raw | ConvertFrom-Json } catch { return $null }
}

# Los hooks se comunican por JSON en stdout. additionalContext = texto que entra
# al contexto del modelo; permissionDecision 'deny' aborta la tool call.
function Emit-Context([string]$text) {
    @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; additionalContext = $text } } |
        ConvertTo-Json -Depth 5 -Compress | Write-Output
}
function Emit-Deny([string]$reason) {
    @{ hookSpecificOutput = @{
           hookEventName            = 'PreToolUse'
           permissionDecision       = 'deny'
           permissionDecisionReason = $reason
       } } | ConvertTo-Json -Depth 5 -Compress | Write-Output
}

# =============================================================================
if ($Mode -eq 'session-start') {
    $dirty = Get-DirtyPaths
    if (-not $dirty) { exit 0 }

    $shown = $dirty | Select-Object -First 12
    $more  = $dirty.Count - $shown.Count
    $msg  = "[session-guard] El working tree ya tiene $($dirty.Count) archivo(s) sin commitear"
    $msg += " - puede ser trabajo de OTRA sesion en curso:`n"
    $msg += ($shown | ForEach-Object { "  $_" }) -join "`n"
    if ($more -gt 0) { $msg += "`n  ... y $more mas" }
    $msg += "`n`nSi vas a trabajar en algo distinto, aislate en tu propio worktree:"
    $msg += "`n  powershell -File worktree.ps1 -Action new -Name <tarea>"
    $msg += "`nSi compartis el tree igual: commitea SOLO tus paths (nunca 'git add -A'),"
    $msg += "`ny no uses 'git checkout --' / 'git stash' / 'git reset --hard' sobre el tree."
    @{ hookSpecificOutput = @{ hookEventName = 'SessionStart'; additionalContext = $msg } } |
        ConvertTo-Json -Depth 5 -Compress | Write-Output
    exit 0
}

# =============================================================================
if ($Mode -eq 'edit-claim') {
    $in = Read-StdinJson
    if (-not $in) { exit 0 }
    $sid  = [string]$in.session_id
    $file = [string]$in.tool_input.file_path
    if (-not $sid -or -not $file) { exit 0 }

    New-Item -ItemType Directory -Force -Path $claimDir | Out-Null

    # Los claims vencidos no los mira nadie pero el dir crece para siempre: podo
    # de paso. Barato (decenas de archivos) y evita tener que limpiar a mano.
    Get-ChildItem $claimDir -Filter '*.claim' -File -ErrorAction SilentlyContinue |
        Where-Object { ((Get-Date) - $_.LastWriteTime).TotalMinutes -ge ($staleMin * 2) } |
        Remove-Item -Force -ErrorAction SilentlyContinue

    # Un claim por (sesion, archivo). El nombre codifica ambos; el mtime es el
    # heartbeat (no hay PID confiable de la sesion, y no hace falta: lo unico que
    # importa es si alguien la toco recientemente).
    # Hash del path completo, no los ultimos 80 chars: truncar hace colisionar
    # archivos con el mismo final (a/x/CLAUDE.md vs b/y/CLAUDE.md), o sea avisos
    # de choques que no existen.
    $md5  = [Security.Cryptography.MD5]::Create()
    $key  = ([BitConverter]::ToString($md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($file.ToLower()))) -replace '-','').Substring(0,16)
    $mine = Join-Path $claimDir ("{0}__{1}.claim" -f $sid, $key)

    # ?Alguna otra sesion viva reclamo este mismo archivo?
    $others = @(Get-ChildItem $claimDir -Filter ("*__{0}.claim" -f $key) -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -notlike ("{0}__*" -f $sid) -and
                               ((Get-Date) - $_.LastWriteTime).TotalMinutes -lt $staleMin })

    Set-Content -Path $mine -Value $file -Encoding UTF8 -ErrorAction SilentlyContinue

    if ($others.Count -gt 0) {
        $ago = [int]((Get-Date) - ($others | Sort-Object LastWriteTime -Descending)[0].LastWriteTime).TotalMinutes
        $inRepo = $file.ToLower().StartsWith($root.ToLower())
        $rel = if ($inRepo) { $file.Substring($root.Length).TrimStart('\','/') } else { $file }

        # El consejo tiene que aplicar al archivo que tenes enfrente. Un choque en
        # la carpeta de memoria (o en cualquier cosa fuera del repo) es real y vale
        # avisarlo, pero hablarle de 'git checkout' o de worktrees es ruido - y un
        # guard que dice pavadas se ignora, o sea deja de proteger.
        $tail = if ($inRepo) {
            "Antes de escribir: releelo (puede haber cambiado en disco desde tu ultimo Read).`n" +
            "Al commitear, stagea solo TUS hunks; no revertas con 'git checkout -- $rel'`n" +
            "(te llevas lo suyo). Para trabajar tranquilo:`n" +
            "  powershell -File worktree.ps1 -Action new -Name <tarea>"
        } else {
            "Esta fuera del repo: no hay historial que te cubra si lo pisas. Releelo`n" +
            "antes de escribir y suma lo tuyo en vez de reescribir el archivo entero."
        }
        Emit-Context ("[session-guard] OJO: otra sesion edito '$rel' hace ~${ago} min y sigue activa.`n" +
                      "Vas a pisar o mezclar su trabajo. $tail")
    }
    exit 0
}

# =============================================================================
if ($Mode -eq 'git-guard') {
    $in = Read-StdinJson
    if (-not $in) { exit 0 }
    $cmd = [string]$in.tool_input.command
    if (-not $cmd) { exit 0 }

    # Solo comandos git que barren el working tree ENTERO. El criterio es "alcance
    # global", no "git peligroso": la forma por path (git checkout -- src/foo.cpp)
    # es justamente la salida que recomendamos, asi que NO puede caer aca.
    # '\.(?![\w/-])' = un '.' como argumento suelto (git checkout . / -- .), que es
    # el que se lleva puesto todo. --staged solo desestagea: no destruye nada.
    $dot = '(?<![\w./-])\.(?![\w/-])'
    $patterns = @(
        @{ rx = "\bgit\s+(checkout|restore)\b(?![^|;&]*--staged(?![^|;&]*--worktree))[^|;&]*$dot"
           what = 'git checkout/restore . (descarta el working tree entero)' },
        @{ rx = '\bgit\s+reset\s+[^|;&]*--hard';              what = 'git reset --hard (descarta TODO el working tree)' },
        @{ rx = '\bgit\s+clean\b[^|;&]*\s-[a-zA-Z]*[fdx]';    what = 'git clean -fd/-fx (borra archivos sin trackear)' },
        @{ rx = '\bgit\s+stash\b(?![^|;&]*\b(list|show)\b)';  what = 'git stash (se lleva los cambios de TODAS las sesiones)' },
        @{ rx = "\bgit\s+add\s+[^|;&]*(-A\b|--all\b|$dot)";   what = 'git add -A/. (stagea trabajo de otras sesiones)' }
    )
    # Matchear el TEXTO del comando bloquea cosas que solo NOMBRAN el comando sin
    # ejecutarlo: un echo, un grep, documentacion, un JSON con 'git stash' adentro.
    # Eso es exactamente lo que hace que un guard se termine desactivando. Asi que
    # antes de bloquear, exigimos que el 'git' este de verdad en posicion de
    # comando y fuera de comillas.

    # ?El indice cae dentro de un string entrecomillado?
    function Test-Quoted([string]$s, [int]$i) {
        $inS = $false; $inD = $false
        for ($k = 0; $k -lt $i -and $k -lt $s.Length; $k++) {
            $c = $s[$k]
            if     ($c -eq "'" -and -not $inD) { $inS = -not $inS }
            elseif ($c -eq '"' -and -not $inS) { $inD = -not $inD }
        }
        return ($inS -or $inD)
    }
    # ?Esta 'git' donde arranca un comando, y no como argumento de otro?
    # ('echo git stash' no ejecuta nada; 'foo && git stash' si.)
    function Test-CommandPos([string]$s, [int]$i) {
        $k = $i - 1
        while ($k -ge 0 -and [char]::IsWhiteSpace($s[$k])) { $k-- }
        if ($k -lt 0) { return $true }
        return ([string]$s[$k] -in @(';', '|', '&', '(', '{', '`', "`n"))
    }

    $hit = $null
    foreach ($p in $patterns) {
        foreach ($m in [regex]::Matches($cmd, $p.rx)) {
            if (-not (Test-Quoted $cmd $m.Index) -and (Test-CommandPos $cmd $m.Index)) {
                $hit = $p; break
            }
        }
        if ($hit) { break }
    }
    if (-not $hit) { exit 0 }

    # Sin trabajo ajeno en riesgo, no hay nada que proteger: dejalo pasar.
    $dirty = Get-DirtyPaths
    if ($dirty.Count -eq 0) { exit 0 }

    $shown = ($dirty | Select-Object -First 10 | ForEach-Object { "  $_" }) -join "`n"
    $more  = $dirty.Count - [Math]::Min(10, $dirty.Count)
    if ($more -gt 0) { $shown += "`n  ... y $more mas" }

    Emit-Deny ("BLOQUEADO: $($hit.what), con $($dirty.Count) archivo(s) sin commitear en el tree.`n`n" +
               "$shown`n`n" +
               "Este tree lo comparten varias sesiones: parte de eso puede ser trabajo ajeno EN CURSO,`n" +
               "y este comando no tiene undo. Alternativas:`n" +
               "  - Revertir SOLO lo tuyo, por path: git checkout -- <tu/archivo> (uno por uno, revisado)`n" +
               "  - Deshacer tus ediciones con la tool Edit (quirurgico, sin tocar lo ajeno)`n" +
               "  - Commitear solo tus paths: git add <path1> <path2> && git commit`n" +
               "  - Aislarte primero: powershell -File worktree.ps1 -Action new -Name <tarea>`n`n" +
               "Si de verdad queres el comando global, pediselo al usuario explicitamente.")
    exit 0
}
