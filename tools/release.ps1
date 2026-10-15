# release.ps1 - publica un release Prod estable o Debug prerelease.
#
# Uso:
#   powershell -File tools\release.ps1                 # dry run: muestra el plan
#   powershell -File tools\release.ps1 -Publish        # taggea, pushea y publica
#   powershell -File tools\release.ps1 -Channel Debug -Publish
#   powershell -File tools\release.ps1 -Version 0.2.0 -Publish
#
# ASCII puro a proposito (ver "los scripts de infra PS son ASCII puro" en CLAUDE.md).
param(
    [string]$Version = "",
    [ValidateSet('Prod', 'Debug')][string]$Channel = 'Prod',
    [switch]$Publish,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Fail([string]$msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
    exit 1
}

# ---- Version: la del proyecto salvo que se pida otra ------------------------
if (-not $Version) {
    $cmake = Get-Content (Join-Path $root 'CMakeLists.txt') -TotalCount 5
    $m = [regex]::Match(($cmake -join "`n"), 'project\(LlamaCode VERSION ([0-9]+\.[0-9]+\.[0-9]+)')
    if (-not $m.Success) { Fail 'No pude leer la version de CMakeLists.txt' }
    $Version = $m.Groups[1].Value
}
if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') {
    Fail "Version invalida: '$Version' (se espera x.y.z)"
}
$tag = if ($Channel -eq 'Debug') { "v$Version-debug" } else { "v$Version" }

# ---- Estado del repo --------------------------------------------------------
Push-Location $root
try {
    $dirty = @(git status --porcelain | Where-Object { $_ })
    $existing = @(git tag --list $tag)
    $tagPattern = if ($Channel -eq 'Debug') { '^v[0-9]+\.[0-9]+\.[0-9]+-debug$' } else { '^v[0-9]+\.[0-9]+\.[0-9]+$' }
    $prevTag = git tag --list 'v*' --sort=-v:refname | Where-Object { $_ -match $tagPattern } | Select-Object -First 1

    if ($existing -and -not $Force) {
        Fail "El tag $tag ya existe. Bumpear la version o usar -Force."
    }

    # Notas: commits desde el tag anterior (o todo el historial en el primero).
    $range = if ($prevTag) { "$prevTag..HEAD" } else { 'HEAD' }
    $log = @(git log --no-merges --pretty=format:'- %s' $range | Where-Object { $_ })
    if ($log.Count -gt 40) { $log = $log[0..39] + '- ...' }
    if (-not $log) { $log = @('- Sin cambios registrados.') }

    $notesPath = Join-Path ([IO.Path]::GetTempPath()) "llamacode-release-$Channel-$Version.md"
    ($log -join "`n") | Set-Content -Path $notesPath -Encoding UTF8

    Write-Host "== release $tag ($Channel) =="
    Write-Host "  repo    : $root"
    Write-Host "  desde   : $(if ($prevTag) { $prevTag } else { '(primer release)' })"
    Write-Host "  commits : $($log.Count)"
    if ($dirty) { Write-Host "  [WARN] hay $($dirty.Count) archivo(s) sin commitear; el release taggea HEAD" }
    Write-Host ''
    $log | ForEach-Object { Write-Host "  $_" }
    Write-Host ''

    if (-not $Publish) {
        Write-Host '[DRY RUN] Nada publicado. Repetir con -Publish para taggear y publicar.'
        exit 0
    }

    if ($dirty -and -not $Force) {
        Fail 'Working tree sucio: commitear (o usar -Force) antes de publicar.'
    }
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Fail 'gh CLI no encontrado; instalalo o publica el release a mano.'
    }

    # CI verde (tests.yml) para el commit que se taggea. El gate local corre en la
    # maquina de quien publica y no ve los merges de otros. El commit "Release
    # vX.Y.Z" solo cambia la version: vale el CI del commit anterior.
    if (-not $Force) {
        $head = (git rev-parse HEAD).Trim()
        $candidates = @($head)
        $changed = @(git diff --name-only HEAD~1 HEAD 2>$null)
        $versionOnly = ($changed.Count -eq 1 -and $changed[0] -eq 'CMakeLists.txt' -and
            (@(git diff -U0 HEAD~1 HEAD -- CMakeLists.txt | Where-Object { $_ -match '^[+-][^+-]' -and $_ -notmatch 'project\(LlamaCode VERSION' }).Count -eq 0))
        if ($versionOnly) { $candidates += (git rev-parse HEAD~1).Trim() }
        $green = $null
        $lastState = 'sin corridas'
        foreach ($sha in $candidates) {
            $json = gh run list --workflow tests.yml --commit $sha --json status,conclusion --limit 1 2>$null
            $run = $null
            try { $run = @($json | ConvertFrom-Json) | Select-Object -First 1 } catch {}
            if ($run) {
                $lastState = "$($run.status)/$($run.conclusion)"
                if ($run.status -eq 'completed' -and $run.conclusion -eq 'success') { $green = $sha; break }
            }
        }
        if (-not $green) {
            Fail "El CI (tests.yml) no esta verde para $head ($lastState). Pushea main, espera el gate de CI y reintenta (o -Force)."
        }
        Write-Host "[OK] CI verde para $green"
    }

    if (-not $existing) {
        git tag -a $tag -m "LlamaCode $Version $Channel"
        if ($LASTEXITCODE -ne 0) { Fail 'git tag fallo' }
    }
    git push origin $tag
    if ($LASTEXITCODE -ne 0) { Fail 'git push del tag fallo' }

    $releaseArgs = @('release', 'create', $tag, '--title', "LlamaCode $Version $Channel", '--notes-file', $notesPath)
    if ($Channel -eq 'Debug') { $releaseArgs += '--prerelease' }
    gh @releaseArgs
    if ($LASTEXITCODE -ne 0) { Fail 'gh release create fallo' }

    Write-Host "[OK] Release $tag ($Channel) publicado."
    Write-Host '[INFO] The app filters releases by the configured update channel.'
    Write-Host '[INFO] CI (release-binaries.yml) now builds the Windows/Linux binaries and attaches them'
    Write-Host '       to this release (~30 min); until then "Actualizar" falls back to building from source.'
}
finally {
    Pop-Location
}
