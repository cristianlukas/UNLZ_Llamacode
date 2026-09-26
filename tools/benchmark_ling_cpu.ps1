[CmdletBinding()]
param(
    [string]$ServerPath,
    [string]$Q4ModelPath,
    [string]$Q6ModelPath,
    [string]$OutputPath,
    [ValidateRange(1, 128)]
    [int]$Threads = 16,
    [ValidateRange(32, 4096)]
    [int]$MaxTokens = 2048,
    [switch]$SelfTest,
    [string]$FinalizeExistingReport,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:SummaryCases = @(
    [ordered]@{
        id = 'harbor-relay'
        title = 'Informe de logística costera'
        early = 'El Proyecto Marea, también identificado como Harbor Relay, tiene como responsable a Mina Rao. La fecha objetivo de puesta en marcha es el 18 de octubre.'
        middle = 'La aprobación financiera fija un presupuesto de US$ 4,6 millones. El proveedor principal es Atlas Logistics.'
        late = 'Al cierre se confirma que Atlas Logistics retrasó la entrega: la fecha revisada es el 11 de octubre. El plan sigue dependiendo de ese envío.'
        expected = [ordered]@{
            project = 'Harbor Relay|Proyecto Marea'
            owner = 'Mina Rao'
            launch_date = '18 de octubre'
            budget = '(?:US\$\s*)?4[,.]6\s*millones'
            supplier = 'Atlas Logistics|Atlas'
            revised_delivery = '11 de octubre'
        }
    }
    [ordered]@{
        id = 'north-clinic'
        title = 'Informe de mantenimiento clínico'
        early = 'La revisión de la Clínica Norte, North Clinic en el registro bilingüe, está a cargo de Elena Park. La inspección es prioritaria para mantener abierto el sitio.'
        middle = 'El equipo técnico contó 27 válvulas con desgaste por encima del límite recomendado. La reparación debe completarse antes del 14 de junio.'
        late = 'La causa principal es el motor de la bomba. La cotización aprobada asciende a 82.000 libras; sin reemplazo, el suministro de agua queda expuesto a interrupciones.'
        expected = [ordered]@{
            site = 'Clínica Norte|North Clinic'
            owner = 'Elena Park'
            count = '27 válvulas'
            deadline = '14 de junio'
            amount = '82[.]000\s*libras|£\s*82[,.]?000'
            risk = 'motor de la bomba|bomba'
        }
    }
)

function New-FillerLine {
    param([Parameter(Mandatory)][int]$Index)

    $route = 'R-{0:D3}' -f (($Index % 127) + 1)
    $packages = 18 + (($Index * 37) % 283)
    $minutes = 12 + (($Index * 19) % 96)
    $zone = @('Este', 'Oeste', 'Norte', 'Sur', 'Centro')[($Index % 5)]
    $shift = @('mañana', 'tarde', 'noche')[($Index % 3)]
    return "Registro rutinario ${Index}: la ruta $route de la zona $zone trasladó $packages paquetes durante el turno de $shift; la ventana de operación duró $minutes minutos y no tuvo incidentes críticos."
}

function New-LingSummaryPrompt {
    param(
        [Parameter(Mandatory)]$Case,
        [Parameter(Mandatory)][int]$FillerRows
    )

    $firstHalf = [int][math]::Floor($FillerRows / 2)
    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add("$($Case.title). Extracto de un reporte extenso. Los registros rutinarios son contexto de bajo nivel.")
    $lines.Add($Case.early)
    for ($i = 1; $i -le $firstHalf; $i++) { $lines.Add((New-FillerLine -Index $i)) }
    $lines.Add($Case.middle)
    for ($i = $firstHalf + 1; $i -le $FillerRows; $i++) { $lines.Add((New-FillerLine -Index $i)) }
    $lines.Add($Case.late)

    $document = $lines -join "`n"
    return @"
Prepará un resumen ejecutivo en español de exactamente cuatro viñetas. Conservá el proyecto o sitio, responsable, fecha clave, monto o cantidad y riesgo/proveedor. Priorizá las decisiones y hechos importantes; omití el detalle operativo rutinario. No inventes datos ni combines fechas. Devolvé sólo las cuatro viñetas.

DOCUMENTO:
$document
"@
}

function Test-LingSummary {
    param(
        [Parameter(Mandatory)]$Case,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Answer
    )

    $matched = [System.Collections.Generic.List[string]]::new()
    $missing = [System.Collections.Generic.List[string]]::new()
    foreach ($fact in $Case.expected.GetEnumerator()) {
        if ([regex]::IsMatch($Answer, $fact.Value, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
            $matched.Add([string]$fact.Key)
        } else {
            $missing.Add([string]$fact.Key)
        }
    }
    $totalFacts = @($Case.expected.Keys).Count
    return [ordered]@{
        matched = @($matched)
        missing = @($missing)
        matchedFacts = $matched.Count
        totalFacts = $totalFacts
        recall = [math]::Round($matched.Count / [double]$totalFacts, 4)
    }
}

function Get-LingMatrix {
    $matrix = [System.Collections.Generic.List[object]]::new()
    foreach ($quant in @('Q4_K_M', 'Q6_K')) {
        foreach ($context in @(4096, 8192)) {
            foreach ($thinking in @($false, $true)) {
                $matrix.Add([ordered]@{
                    quant = $quant
                    context = $context
                    thinking = $thinking
                })
            }
        }
    }
    return @($matrix)
}

function Get-LingTrialSummaries {
    param([Parameter(Mandatory)][object[]]$Trials)

    $summaries = [System.Collections.Generic.List[object]]::new()
    foreach ($groupInfo in ($Trials | Group-Object { '{0}|{1}|{2}' -f $_.quant, $_.context, $_.thinking })) {
        $group = @($groupInfo.Group)
        $requests = @($group | ForEach-Object { $_.requests } | ForEach-Object { $_ })
        $rates = [System.Collections.Generic.List[double]]::new()
        $peak = 0L
        $facts = 0
        $total = 0
        foreach ($request in $requests) {
            if ($null -ne $request.decodeTokensPerSecond) { $rates.Add([double]$request.decodeTokensPerSecond) }
            if ([long]$request.peakWorkingSetBytes -gt $peak) { $peak = [long]$request.peakWorkingSetBytes }
            $facts += [int]$request.matchedFacts
            $total += [int]$request.totalFacts
        }
        $meanRate = $null
        if ($rates.Count -gt 0) {
            $rateSum = 0.0
            foreach ($rate in $rates) { $rateSum += $rate }
            $meanRate = [math]::Round($rateSum / $rates.Count, 3)
        }
        $summaries.Add([ordered]@{
            quant = $group[0].quant
            context = $group[0].context
            thinking = $group[0].thinking
            status = $group[0].status
            meanDecodeTokensPerSecond = $meanRate
            peakWorkingSetBytes = if ($requests.Count -gt 0) { $peak } else { $null }
            requiredFactsRecall = if ($total -gt 0) { [math]::Round($facts / [double]$total, 4) } else { $null }
            completedRequests = $requests.Count
        })
    }
    return @($summaries)
}

function Invoke-LingSelfTest {
    $case = $script:SummaryCases[0]
    $goodAnswer = 'Proyecto Marea (Harbor Relay), a cargo de Mina Rao, inicia el 18 de octubre. Presupuesto: US$ 4,6 millones. Atlas Logistics informó que la entrega revisada será el 11 de octubre.'
    $goodScore = Test-LingSummary -Case $case -Answer $goodAnswer
    if ($goodScore.matchedFacts -ne 6 -or $goodScore.totalFacts -ne 6) {
        throw 'El scorer no reconoce todos los hechos del ejemplo válido.'
    }
    $badScore = Test-LingSummary -Case $case -Answer 'El presupuesto operativo sigue en revisión.'
    if ($badScore.matchedFacts -ne 0 -or $badScore.missing.Count -ne 6) {
        throw 'El scorer no rechaza una respuesta sin los hechos requeridos.'
    }
    $emptyScore = Test-LingSummary -Case $case -Answer ''
    if ($emptyScore.matchedFacts -ne 0 -or $emptyScore.missing.Count -ne 6) {
        throw 'El scorer debe registrar una respuesta vacía como cero, no abortar la corrida.'
    }
    $caseBScore = Test-LingSummary -Case $script:SummaryCases[1] -Answer ''
    if ($caseBScore.matchedFacts -ne 0 -or $caseBScore.totalFacts -ne 6) {
        throw 'El scorer debe manejar una clave "count" sin confundirla con el total de la colección.'
    }
    $prompt = New-LingSummaryPrompt -Case $script:SummaryCases[1] -FillerRows 20
    if ($prompt -notmatch '27 válvulas' -or $prompt -notmatch 'motor de la bomba' -or $prompt -notmatch 'Registro rutinario') {
        throw 'El constructor del documento de prueba omitió hechos o relleno.'
    }
    $matrix = @(Get-LingMatrix)
    if ($matrix.Count -ne 8 -or @($matrix | Where-Object thinking).Count -ne 4) {
        throw 'La matriz no contiene las ocho variantes previstas.'
    }
    $summary = @(Get-LingTrialSummaries -Trials @(
        [ordered]@{ quant = 'Q4_K_M'; context = 4096; thinking = 'off'; status = 'completed'; requests = @([ordered]@{ decodeTokensPerSecond = 10.0; peakWorkingSetBytes = 100; matchedFacts = 4; totalFacts = 6 }) }
        [ordered]@{ quant = 'Q4_K_M'; context = 4096; thinking = 'off'; status = 'completed'; requests = @([ordered]@{ decodeTokensPerSecond = 20.0; peakWorkingSetBytes = 120; matchedFacts = 6; totalFacts = 6 }) }
    ))
    if ($summary.Count -ne 1 -or $summary[0].meanDecodeTokensPerSecond -ne 15 -or $summary[0].peakWorkingSetBytes -ne 120 -or $summary[0].requiredFactsRecall -ne 0.8333) {
        throw 'El agregador debe sumar métricas de OrderedDictionary sin perder recall ni máximos.'
    }
    Write-Output 'SELFTEST PASS: scorer, documentos sintéticos, agregación y matriz Q4/Q6 × 4k/8k × thinking on/off.'
}

function Get-TokenCount {
    param(
        [Parameter(Mandatory)][string]$BaseUrl,
        [Parameter(Mandatory)][string]$Text
    )

    $body = @{ content = $Text; add_special = $false; parse_special = $true } | ConvertTo-Json -Compress
    $reply = Invoke-RestMethod -Uri "$BaseUrl/tokenize" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 60
    if ($null -eq $reply.tokens) { throw 'El endpoint /tokenize no devolvió tokens.' }
    return @($reply.tokens).Count
}

function Get-OptionalField {
    param($InputObject, [Parameter(Mandatory)][string]$Name)

    if ($null -eq $InputObject) { return $null }
    if ($InputObject -is [System.Collections.IDictionary]) {
        if ($InputObject.Contains($Name)) { return $InputObject[$Name] }
        return $null
    }
    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -ne $property) { return $property.Value }
    return $null
}

function New-SizedPrompt {
    param(
        [Parameter(Mandatory)][string]$BaseUrl,
        [Parameter(Mandatory)]$Case,
        [Parameter(Mandatory)][int]$Context,
        [Parameter(Mandatory)][int]$MaxTokens
    )

    # Deja espacio para la plantilla, la respuesta y el razonamiento si está activo.
    $target = $Context - $MaxTokens - 320
    $low = 0
    $high = 64
    $highCount = Get-TokenCount -BaseUrl $BaseUrl -Text (New-LingSummaryPrompt -Case $Case -FillerRows $high)
    while ($highCount -lt $target) {
        $low = $high
        $high *= 2
        if ($high -gt 4096) { throw "No pude llenar el contexto de $Context tokens." }
        $highCount = Get-TokenCount -BaseUrl $BaseUrl -Text (New-LingSummaryPrompt -Case $Case -FillerRows $high)
    }

    $bestRows = $low
    $bestPrompt = New-LingSummaryPrompt -Case $Case -FillerRows $bestRows
    $bestTokens = Get-TokenCount -BaseUrl $BaseUrl -Text $bestPrompt
    while (($high - $low) -gt 1) {
        $mid = [int][math]::Floor(($low + $high) / 2)
        $candidate = New-LingSummaryPrompt -Case $Case -FillerRows $mid
        $count = Get-TokenCount -BaseUrl $BaseUrl -Text $candidate
        if ($count -le $target) {
            $low = $mid
            $bestRows = $mid
            $bestPrompt = $candidate
            $bestTokens = $count
        } else {
            $high = $mid
        }
    }
    if ($bestTokens -lt ($target - 64)) {
        throw "Prompt demasiado corto: $bestTokens tokens para contexto $Context."
    }
    return [ordered]@{ prompt = $bestPrompt; promptTokens = $bestTokens; fillerRows = $bestRows }
}

function Get-FreePort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try { return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port }
    finally { $listener.Stop() }
}

function Get-ModelMetadata {
    param([Parameter(Mandatory)][string]$Path)
    $file = Get-Item -LiteralPath $Path
    $hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
    return [ordered]@{ path = $file.FullName; sizeBytes = $file.Length; sha256 = $hash.Hash.ToLowerInvariant() }
}

function Write-Report {
    param([Parameter(Mandatory)]$Report, [Parameter(Mandatory)][string]$Path)
    $json = ConvertTo-Json -InputObject $Report -Depth 24
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

if ($SelfTest) {
    Invoke-LingSelfTest
    return
}

if (-not [string]::IsNullOrWhiteSpace($FinalizeExistingReport)) {
    $reportPath = [System.IO.Path]::GetFullPath($FinalizeExistingReport)
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) { throw "No existe el reporte: $reportPath" }
    $existingReport = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
    $existingReport.summaries = @(Get-LingTrialSummaries -Trials @($existingReport.trials))
    $freeRamBytes = [long](Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory).AvailableMBytes * 1MB
    $existingReport.hardware | Add-Member -NotePropertyName freeRamAfterBytes -NotePropertyValue $freeRamBytes -Force
    Write-Report -Report $existingReport -Path $reportPath
    Write-Output "Reporte finalizado: $reportPath"
    return
}

foreach ($required in @(@{ name = 'ServerPath'; value = $ServerPath }, @{ name = 'Q4ModelPath'; value = $Q4ModelPath }, @{ name = 'Q6ModelPath'; value = $Q6ModelPath })) {
    if ([string]::IsNullOrWhiteSpace($required.value)) { throw "Falta -$($required.name)." }
    if (-not (Test-Path -LiteralPath $required.value -PathType Leaf)) { throw "No existe $($required.name): $($required.value)" }
}

$serverInfo = Get-Item -LiteralPath $ServerPath
$q4Info = Get-ModelMetadata -Path $Q4ModelPath
$q6Info = Get-ModelMetadata -Path $Q6ModelPath
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputPath = Join-Path (Join-Path $PSScriptRoot '..\artifacts') "ling-tiny-cpu-$stamp.json"
}
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$outputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
if ((Test-Path -LiteralPath $OutputPath) -and -not $Force) { throw "El reporte ya existe; usá otro -OutputPath o -Force: $OutputPath" }
$logDir = Join-Path $outputDir ([System.IO.Path]::GetFileNameWithoutExtension($OutputPath) + '-logs')
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$versionOutput = (& $ServerPath --version 2>&1 | Out-String).Trim()
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$computer = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$modelByQuant = @{ Q4_K_M = $q4Info; Q6_K = $q6Info }
$pathByQuant = @{ Q4_K_M = $Q4ModelPath; Q6_K = $Q6ModelPath }
$report = [ordered]@{
    schemaVersion = 1
    createdAt = (Get-Date).ToUniversalTime().ToString('o')
    benchmark = 'Ling 3.0 Tiny CPU summary retention smoke'
    hardware = [ordered]@{
        cpu = $cpu.Name
        physicalCores = $cpu.NumberOfCores
        logicalProcessors = $cpu.NumberOfLogicalProcessors
        totalRamBytes = $computer.TotalPhysicalMemory
        freeRamBeforeBytes = [long]$memory.AvailableMBytes * 1MB
        os = $os.Caption
        osVersion = $os.Version
    }
    runtime = [ordered]@{ path = $serverInfo.FullName; version = $versionOutput; gpuLayers = 0; threads = $Threads; batchThreads = $Threads }
    models = [ordered]@{ Q4_K_M = $q4Info; Q6_K = $q6Info }
    method = [ordered]@{
        contexts = @(4096, 8192)
        promptTarget = 'context minus maxTokens minus 320 tokens; actual prompt count measured with the server tokenizer'
        maxTokens = $MaxTokens
        sampling = [ordered]@{ temperature = 1.0; topP = 0.95; topK = 20; minP = 0.0; repeatPenalty = 1.0 }
        thinkingModes = @('off', 'on')
        scoring = 'Required-fact recall from final answer; this is a smoke score, not a semantic grader.'
        documents = @($script:SummaryCases | ForEach-Object { [ordered]@{ id = $_.id; requiredFacts = $_.expected.Count } })
    }
    trials = [System.Collections.Generic.List[object]]::new()
    summaries = @()
}
Write-Report -Report $report -Path $OutputPath

$matrix = @(Get-LingMatrix)
foreach ($config in $matrix) {
    $port = Get-FreePort
    $baseUrl = "http://127.0.0.1:$port"
    $modelPath = $pathByQuant[$config.quant]
    $trial = [ordered]@{
        quant = $config.quant
        modelSha256 = $modelByQuant[$config.quant].sha256
        context = $config.context
        thinking = if ($config.thinking) { 'on' } else { 'off' }
        threads = $Threads
        status = 'starting'
        serverLog = $null
        requests = [System.Collections.Generic.List[object]]::new()
        error = $null
    }
    $slug = '{0}-{1}k-thinking-{2}' -f $config.quant, [int]($config.context / 1024), $trial.thinking
    $stdoutPath = Join-Path $logDir "$slug.stdout.log"
    $stderrPath = Join-Path $logDir "$slug.stderr.log"
    $trial.serverLog = $stderrPath
    $report.trials.Add($trial)
    Write-Report -Report $report -Path $OutputPath
    $serverProcess = $null
    Write-Host "Starting $slug (CPU-only, $Threads threads)"
    try {
        $serverArgs = @(
            '-m', ('"{0}"' -f ([System.IO.Path]::GetFullPath($modelPath))),
            '--host', '127.0.0.1', '--port', "$port",
            '--ctx-size', "$($config.context)",
            '--threads', "$Threads", '--threads-batch', "$Threads",
            '--batch-size', '512', '--ubatch-size', '128', '--parallel', '1',
            '--n-gpu-layers', '0', '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
            '--jinja', '--metrics', '--no-warmup',
            '--temp', '1.0', '--top-p', '0.95', '--top-k', '20', '--min-p', '0.0'
        )
        $serverProcess = Start-Process -FilePath $ServerPath -ArgumentList $serverArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $healthy = $false
        for ($attempt = 0; $attempt -lt 120; $attempt++) {
            $serverProcess.Refresh()
            if ($serverProcess.HasExited) { throw "llama-server terminó durante el arranque (exit $($serverProcess.ExitCode))." }
            try {
                $health = Invoke-RestMethod -Uri "$baseUrl/health" -TimeoutSec 2
                if ($health.status -eq 'ok') { $healthy = $true; break }
            } catch { }
            Start-Sleep -Seconds 1
        }
        if (-not $healthy) { throw 'llama-server no quedó healthy en 120 segundos.' }
        $trial.status = 'running'

        foreach ($case in $script:SummaryCases) {
            $sized = New-SizedPrompt -BaseUrl $baseUrl -Case $case -Context $config.context -MaxTokens $MaxTokens
            $requestBody = [ordered]@{
                model = 'ling-3.0-tiny'
                messages = @(@{ role = 'user'; content = $sized.prompt })
                stream = $false
                max_tokens = $MaxTokens
                temperature = 1.0
                top_p = 0.95
                top_k = 20
                min_p = 0.0
                repeat_penalty = 1.0
                chat_template_kwargs = [ordered]@{ enable_thinking = [bool]$config.thinking; preserve_thinking = $true }
            } | ConvertTo-Json -Depth 12 -Compress
            $watch = [System.Diagnostics.Stopwatch]::StartNew()
            $response = Invoke-RestMethod -Uri "$baseUrl/v1/chat/completions" -Method Post -ContentType 'application/json' -Body $requestBody -TimeoutSec 900
            $watch.Stop()
            $message = $response.choices[0].message
            $answer = [string]$message.content
            $score = Test-LingSummary -Case $case -Answer $answer
            $serverProcess.Refresh()
            $timings = Get-OptionalField -InputObject $response -Name 'timings'
            $request = [ordered]@{
                caseId = $case.id
                inputTokens = $sized.promptTokens
                fillerRows = $sized.fillerRows
                wallSeconds = [math]::Round($watch.Elapsed.TotalSeconds, 3)
                promptTokens = Get-OptionalField -InputObject $timings -Name 'prompt_n'
                promptSeconds = if ($null -ne (Get-OptionalField -InputObject $timings -Name 'prompt_ms')) { [math]::Round(([double](Get-OptionalField -InputObject $timings -Name 'prompt_ms')) / 1000, 3) } else { $null }
                prefillTokensPerSecond = Get-OptionalField -InputObject $timings -Name 'prompt_per_second'
                outputTokens = Get-OptionalField -InputObject $timings -Name 'predicted_n'
                outputSeconds = if ($null -ne (Get-OptionalField -InputObject $timings -Name 'predicted_ms')) { [math]::Round(([double](Get-OptionalField -InputObject $timings -Name 'predicted_ms')) / 1000, 3) } else { $null }
                decodeTokensPerSecond = Get-OptionalField -InputObject $timings -Name 'predicted_per_second'
                peakWorkingSetBytes = [long]$serverProcess.PeakWorkingSet64
                matchedFacts = $score.matchedFacts
                totalFacts = $score.totalFacts
                factRecall = $score.recall
                matched = $score.matched
                missing = $score.missing
                answer = $answer
                answerCharacters = $answer.Length
                finishReason = $response.choices[0].finish_reason
            }
            $trial.requests.Add($request)
            Write-Host ("  {0}: {1}/{2} facts, {3:N1} decode tok/s, {4:N1}s, prompt {5} tokens, peak {6:N2} GiB" -f $case.id, $score.matchedFacts, $score.totalFacts, [double]$request.decodeTokensPerSecond, $watch.Elapsed.TotalSeconds, $sized.promptTokens, ($request.peakWorkingSetBytes / 1GB))
            Write-Report -Report $report -Path $OutputPath
        }
        $trial.status = 'completed'
    } catch {
        $trial.status = 'failed'
        $trial.error = $_.Exception.Message
        Write-Warning "$slug failed: $($trial.error)"
        if (Test-Path -LiteralPath $stderrPath) {
            $trial.errorLogTail = @(Get-Content -LiteralPath $stderrPath -Tail 30 -ErrorAction SilentlyContinue)
        }
    } finally {
        if ($null -ne $serverProcess) {
            $serverProcess.Refresh()
            if (-not $serverProcess.HasExited) {
                Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
                $serverProcess.WaitForExit()
            }
            $serverProcess.Dispose()
        }
    }
    Write-Report -Report $report -Path $OutputPath
}

$report.summaries = @(Get-LingTrialSummaries -Trials @($report.trials))
$report.hardware.freeRamAfterBytes = [long](Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory).AvailableMBytes * 1MB
Write-Report -Report $report -Path $OutputPath
Write-Host "Report: $OutputPath"
Write-Host "Logs:   $logDir"
