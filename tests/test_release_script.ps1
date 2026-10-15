$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root 'tools\release.ps1'
$fails = 0

function Check([bool]$condition, [string]$message) {
    if ($condition) { Write-Host "  PASS $message" }
    else { Write-Host "  FAIL $message" -ForegroundColor Red; $script:fails++ }
}

Write-Host '== release.ps1 =='

# 0) ASCII puro: Windows PowerShell 5.1 lee un .ps1 sin BOM como ANSI y un
#    caracter UTF-8 dentro de un string puede cerrarlo y romper el parseo.
$bytes = [IO.File]::ReadAllBytes($script)
$nonAscii = @($bytes | Where-Object { $_ -gt 127 })
Check ($nonAscii.Count -eq 0) "el script es ASCII puro (bytes >127: $($nonAscii.Count))"

# 1) Dry run por defecto: no taggea ni publica.
$tagsBefore = @(git -C $root tag --list)
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File $script 2>&1 | Out-String
$tagsAfter = @(git -C $root tag --list)
Check ($LASTEXITCODE -eq 0) 'dry run sale 0'
Check ($out -match '\[DRY RUN\]') 'dry run se anuncia como tal'
Check ($tagsBefore.Count -eq $tagsAfter.Count) 'dry run no crea tags'

# 2) Toma la version de CMakeLists.txt.
$cmake = (Get-Content (Join-Path $root 'CMakeLists.txt') -TotalCount 5) -join "`n"
$version = [regex]::Match($cmake, 'project\(LlamaCode VERSION ([0-9]+\.[0-9]+\.[0-9]+)').Groups[1].Value
Check ($out -match [regex]::Escape("release v$version")) "usa la version del proyecto (v$version)"

$debugOut = & powershell -NoProfile -ExecutionPolicy Bypass -File $script -Channel Debug 2>&1 | Out-String
Check ($LASTEXITCODE -eq 0) 'Debug dry run sale 0'
Check ($debugOut -match [regex]::Escape("release v$version-debug")) 'Debug usa un tag prerelease separado'

# 3) Rechaza versiones mal formadas antes de tocar git.
& powershell -NoProfile -ExecutionPolicy Bypass -File $script -Version '0.1' 2>&1 | Out-Null
Check ($LASTEXITCODE -eq 1) 'rechaza una version que no es x.y.z'

# 4) El tag tiene que parsear como version en el app: AppController saca la 'v'
#    inicial y pide QVersionNumber::fromString no nulo.
Check ($out -match 'release v[0-9]+\.[0-9]+\.[0-9]+ \(Prod\)') 'Prod usa el tag estable vX.Y.Z'
Check ($debugOut -match 'release v[0-9]+\.[0-9]+\.[0-9]+-debug \(Debug\)') 'Debug usa vX.Y.Z-debug'

# 5) Publicar es explicito: sin -Publish no hay llamada a gh.
$body = [IO.File]::ReadAllText($script)
Check ($body -match 'if \(-not \$Publish\)') 'publicar requiere -Publish'
Check ($body -match 'gh release create') 'publica con gh release create'
Check ($body -match '--prerelease') 'Debug se publica marcado como prerelease'

# 6) Binarios: el tag que pushea el release dispara release-binaries.yml, que
#    sube los assets que "Actualizar" baja (sin compilar en la PC del usuario).
$wf = [IO.File]::ReadAllText((Join-Path $root '.github\workflows\release-binaries.yml'))
# La subida vive en un workflow reutilizable (un publish por SO).
$wf += [IO.File]::ReadAllText((Join-Path $root '.github\workflows\release-binaries-upload.yml'))
Check ($wf.Contains('publish-linux:') -and $wf.Contains('needs: [meta, linux]')) 'Linux se publica sin esperar al build de Windows'
Check ($wf -match "tags: \['v\*\.\*\.\*'\]") 'el push del tag (Prod y -debug) dispara el build de binarios'
Check ($wf.Contains('gh release upload "$TAG" dist/* --clobber')) 'el CI sube los paquetes a la release del tag'
Check ($wf.Contains('gh release view "$TAG"') -and $wf.Contains('sleep 20')) 'el CI espera a que release.ps1 cree la release (tag primero, release despues)'
Check ($wf -match '-debug\$ \]\]; then config=Debug') 'un tag -debug compila Debug (mismo canal que el bootstrap)'
$tagIdx = $body.IndexOf('git push origin $tag')
$createIdx = $body.IndexOf("'release', 'create'")
Check ($tagIdx -gt 0 -and $createIdx -gt $tagIdx) 'release.ps1 pushea el tag antes de crear la release'

# CI (tests.yml) en cada push a main, exigido antes de publicar.
$testsWf = [IO.File]::ReadAllText((Join-Path $root '.github\workflows\tests.yml'))
Check ($testsWf -match 'branches: \[main\]' -and $testsWf.Contains('pull_request:')) 'tests.yml corre en cada push a main y en PRs'
Check ($testsWf.Contains('-DBUILD_TESTS=ON') -and $testsWf.Contains('ctest --test-dir build_tests')) 'tests.yml compila los tests y corre ctest'
Check ($testsWf.Contains('linux:') -and $testsWf.Contains('windows:')) 'tests.yml cubre Linux y Windows'
$ciIdx = $body.IndexOf('gh run list --workflow tests.yml')
Check ($ciIdx -gt 0 -and $ciIdx -lt $tagIdx) 'release.ps1 exige CI verde ANTES de pushear el tag'
Check ($body.Contains("conclusion -eq 'success'")) 'release.ps1 solo acepta una corrida exitosa'

if ($fails) { throw "$fails release-script regression(s) failed" }
Write-Host 'All release-script regressions passed.'
