#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Server,

    [Parameter(Mandatory = $true)]
    [string]$Model,

    [int]$Port = 8097,
    [string]$ArtifactDir = "./artifacts/qwen38-flash-next-campaign",
    [string]$Output = "",
    [int]$Passes = 1,
    [int[]]$Contexts = @(8192, 32768),
    [int]$NCpuMoe = 40,
    [switch]$IncludeExperimental
)

$ErrorActionPreference = "Stop"
$campaignRoot = [System.IO.Path]::GetFullPath($ArtifactDir)
New-Item -ItemType Directory -Force -Path $campaignRoot | Out-Null
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $campaignRoot "summary.json"
}
$Output = [System.IO.Path]::GetFullPath($Output)

function Write-JsonFile([string]$Path, $Value) {
    $Value | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 -Path $Path
}

function Get-GpuSnapshot {
    $rows = @()
    try {
        $raw = & nvidia-smi --query-gpu=index,name,memory.used,memory.total,temperature.gpu,utilization.gpu --format=csv,noheader,nounits 2>$null
        foreach ($line in $raw) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $parts = $line -split "\s*,\s*"
            if ($parts.Count -ge 6) {
                $rows += [ordered]@{
                    index = [int]$parts[0]
                    name = $parts[1]
                    memory_used_mib = [int]$parts[2]
                    memory_total_mib = [int]$parts[3]
                    temperature_c = [int]$parts[4]
                    utilization_pct = [int]($parts[5] -replace "%", "")
                }
            }
        }
    } catch {
        # nvidia-smi is optional for portability; the case remains valid without it.
    }
    return @($rows)
}

function Wait-Healthy([string]$BaseUrl, [int]$TimeoutSeconds = 180) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -TimeoutSec 5
            if ($health.status -eq "ok") { return $true }
        } catch {}
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Invoke-Probe([string]$BaseUrl, [int]$Context) {
    $probes = @(
        [ordered]@{
            id = "arithmetic"
            prompt = "Reply with exactly: FINAL: 4"
            expected = "FINAL:\s*4"
        },
        [ordered]@{
            id = "sequence"
            prompt = "Reply with exactly: NUMBERS: 55 56 57 58 59"
            expected = "NUMBERS:\s*55\s+56\s+57\s+58\s+59"
        },
        [ordered]@{
            id = "json"
            prompt = 'Reply with exactly one JSON object and no markdown: {"ok":true}'
            expected = '\{\s*\x22ok\x22\s*:\s*true\s*\}'
        }
    )

    $results = @()
    foreach ($probe in $probes) {
        foreach ($cachePrompt in @($false, $true)) {
            $body = [ordered]@{
                prompt = $probe.prompt
                n_predict = 32
                temperature = 0.0
                top_p = 1.0
                top_k = 1
                min_p = 0.0
                repeat_penalty = 1.0
                cache_prompt = $cachePrompt
                stream = $false
            }
            $started = Get-Date
            try {
                $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/completion" -ContentType "application/json" -Body ($body | ConvertTo-Json) -TimeoutSec 120
                $content = [string]$response.content
                $matched = $content -match $probe.expected
                $results += [ordered]@{
                    probe = $probe.id
                    cache_prompt = $cachePrompt
                    ok = [bool]$matched
                    content = $content.Trim()
                    elapsed_ms = [int]((Get-Date) - $started).TotalMilliseconds
                }
            } catch {
                $results += [ordered]@{
                    probe = $probe.id
                    cache_prompt = $cachePrompt
                    ok = $false
                    content = ""
                    error = $_.Exception.Message
                    elapsed_ms = [int]((Get-Date) - $started).TotalMilliseconds
                }
            }
        }
    }
    return @($results)
}

function Invoke-Case([string]$CaseName, [int]$Context, [string]$SplitMode, [bool]$ExpertCache) {
    $caseDir = Join-Path $campaignRoot $CaseName
    New-Item -ItemType Directory -Force -Path $caseDir | Out-Null
    $stdoutPath = Join-Path $caseDir "server.stdout.log"
    $stderrPath = Join-Path $caseDir "server.stderr.log"
    $baseUrl = "http://127.0.0.1:$Port"
    $args = @(
        "--model", $Model,
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--ctx-size", "$Context",
        "--n-gpu-layers", "999",
        "--split-mode", $SplitMode,
        "--fit", "off",
        "--n-cpu-moe", "$NCpuMoe",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--batch-size", "512",
        "--ubatch-size", "512",
        "--threads", "16",
        "--threads-batch", "16",
        "--flash-attn", "on",
        "--temp", "0.6",
        "--top-p", "0.95",
        "--top-k", "20",
        "--min-p", "0.0",
        "--repeat-penalty", "1.0",
        "--presence-penalty", "0.0",
        "--reasoning", "off",
        "--metrics"
    )
    if ($ExpertCache) {
        $args += @("--moe-expert-cache", "188")
    }

    $startedAt = Get-Date
    $before = Get-GpuSnapshot
    $process = $null
    try {
        $process = Start-Process -FilePath $Server -ArgumentList $args -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
        $healthy = Wait-Healthy -BaseUrl $baseUrl
        if (-not $healthy) {
            return [ordered]@{
                case = $CaseName
                context = $Context
                split_mode = $SplitMode
                expert_cache = $ExpertCache
                status = "failed"
                failure_kind = "health_timeout"
                gpu_before = $before
                gpu_after = Get-GpuSnapshot
                log_stdout = $stdoutPath
                log_stderr = $stderrPath
                elapsed_s = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 2)
            }
        }

        $afterLoad = Get-GpuSnapshot
        $probes = Invoke-Probe -BaseUrl $baseUrl -Context $Context
        $qualityOk = @($probes | Where-Object { -not $_.ok }).Count -eq 0
        $status = if ($qualityOk) { "ok" } else { "quality_fail" }
        return [ordered]@{
            case = $CaseName
            context = $Context
            split_mode = $SplitMode
            expert_cache = $ExpertCache
            status = $status
            failure_kind = if ($qualityOk) { "" } else { "deterministic_probe" }
            probes = $probes
            gpu_before = $before
            gpu_after_load = $afterLoad
            log_stdout = $stdoutPath
            log_stderr = $stderrPath
            elapsed_s = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 2)
        }
    } catch {
        return [ordered]@{
            case = $CaseName
            context = $Context
            split_mode = $SplitMode
            expert_cache = $ExpertCache
            status = "failed"
            failure_kind = "process_or_request"
            error = $_.Exception.Message
            gpu_before = $before
            gpu_after = Get-GpuSnapshot
            log_stdout = $stdoutPath
            log_stderr = $stderrPath
            elapsed_s = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 2)
        }
    } finally {
        if ($null -ne $process) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                $process.WaitForExit()
                $process.Dispose()
            } catch {}
        }
        Start-Sleep -Seconds 2
    }
}

$cases = @()
for ($pass = 1; $pass -le $Passes; $pass++) {
    foreach ($context in $Contexts) {
        $cases += Invoke-Case -CaseName ("pass{0}-layer-ctx{1}-base" -f $pass, $context) -Context $context -SplitMode "layer" -ExpertCache $false
        $cases += Invoke-Case -CaseName ("pass{0}-layer-ctx{1}-cache188" -f $pass, $context) -Context $context -SplitMode "layer" -ExpertCache $true
        if ($IncludeExperimental) {
            $cases += Invoke-Case -CaseName ("pass{0}-row-ctx{1}-diagnostic" -f $pass, $context) -Context $context -SplitMode "row" -ExpertCache $false
        }
    }
}

$manifest = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    server = [System.IO.Path]::GetFullPath($Server)
    model = [System.IO.Path]::GetFullPath($Model)
    port = $Port
    passes = $Passes
    contexts = $Contexts
    n_cpu_moe = $NCpuMoe
    include_experimental = [bool]$IncludeExperimental
    cases = $cases
}
Write-JsonFile -Path $Output -Value $manifest

$summary = $cases | Select-Object case, context, split_mode, expert_cache, status, failure_kind, elapsed_s
$summary | Format-Table -AutoSize | Out-String | Set-Content -Encoding utf8 -Path (Join-Path $campaignRoot "summary.txt")
Write-Host "Campaign complete: $Output"

