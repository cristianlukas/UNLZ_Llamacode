$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$build = [IO.File]::ReadAllText((Join-Path $root 'build.bat'))
$tests = [IO.File]::ReadAllText((Join-Path $root 'tests.bat'))
$fails = 0

function Check([bool]$condition, [string]$message) {
    if ($condition) { Write-Host "  PASS $message" }
    else { Write-Host "  FAIL $message" -ForegroundColor Red; $script:fails++ }
}

Write-Host '== incremental build script policy =='
Check (-not $build.Contains('call "%~dp0bump-patch.bat"')) 'build does not mutate the version'
Check (-not $build.Contains('taskkill /F /IM MSBuild.exe')) 'build does not kill foreign MSBuild processes'
Check (-not $build.Contains('for /r "build" %%f in (*.tlog)')) 'build preserves MSBuild tracking logs'
Check ($build.Contains('if not exist CMakeCache.txt')) 'app configures only without a cache'
Check ($tests.Contains('if not exist build_tests\CMakeCache.txt')) 'tests configure only without a cache'
Check ($build.Contains('-DFETCHCONTENT_UPDATES_DISCONNECTED=ON')) 'dependency updates are disconnected after fetch'
Check ($tests.Contains('-DFETCHCONTENT_UPDATES_DISCONNECTED=ON')) 'test dependencies are disconnected after fetch'
Check ($build.Contains('Program Files (x86)\Microsoft Visual Studio\2022')) 'VS 2022 x86 install root is detected'
Check (-not $build.Contains('Generator changed from')) 'existing build trees are not forcibly migrated'
Check ($build.Contains('_deps\qtkeychain-subbuild\CMakeCache.txt')) 'interrupted configure reuses dependency generator'
Check ($build.Contains('if not exist CMakeFiles\VerifyGlobs.cmake set NEED_CONFIG=1')) 'partial configure is repaired'
Check ($build.Contains('Removing incompatible generated QtKeychain build metadata')) 'partial mixed-generator dependency is repaired'

if ($fails) { throw "$fails build-script regression(s) failed" }
Write-Host 'All build-script regressions passed.'
