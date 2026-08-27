# Benchmark de Qwen3.8-Flash-Next (arquitectura Qwen4: MoE + Ngram/PLE).
#
# Lo que mide, y por que: en esta arquitectura los tensores Ngram/PLE son una
# lookup table de acceso aleatorio, no compute. La pregunta de tuning no es
# "cuantas capas a GPU" sino "donde viven los Ngram": VRAM, RAM, o SSD via mmap.
# El sweep compara esas tres colocaciones con el mismo modelo y prompts.
#
# ASCII puro a proposito (ver CLAUDE.md: Windows PowerShell 5.1 lee .ps1 sin BOM
# como ANSI y un caracter UTF-8 dentro de un string puede cortarlo).
param(
    [string]$Server = "",
    [string]$Model  = "",
    [int]$Port      = 18097,
    [int]$Passes    = 2,
    [int]$CtxSize   = 32768,
    # Regex de tensores Ngram/PLE. Vacio = autodetectar desde el GGUF.
    [string]$NgramRegex = "",
    [ValidateSet("thinking","instruct","both")]
    [string]$Mode = "both",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"

if (-not $Server) {
    # Ninja es single-config: los binarios quedan en buildin, no en buildin\Release.
    $Server = Join-Path $env:APPDATA "LlamaCode\LlamaCode\tools\llama.cpp-qwen38-next\build\bin\llama-server.exe"
}
if (-not $Model) {
    $Model = "D:\Models\llamacpp\Qwen3.8-Flash-Next-UD-Q4_K_XL\UD-Q4_K_XL\Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf"
}
if (-not (Test-Path $Server)) { throw "No existe llama-server: $Server (compilar el PR 27742 primero)" }
if (-not (Test-Path $Model))  { throw "No existe el modelo: $Model" }

# Sampling oficial. Son DOS perfiles distintos, no uno con variantes.
$sampling = @{
    thinking = @{ temp="1.0"; topP="0.95"; topK="20"; minP="0.0"; presence="0.0" }
    instruct = @{ temp="0.7"; topP="0.80"; topK="20"; minP="0.0"; presence="1.5" }
}

$tasks = @(
    @{ id="modular";      expected='(?im)^FINAL:\s*1\s*$';       prompt="Compute 2^100 mod 125. Explain briefly and end with exactly FINAL: <integer>." },
    @{ id="mississippi";  expected='(?im)^FINAL:\s*34650\s*$';   prompt="How many distinct permutations does MISSISSIPPI have? Explain briefly and end with exactly FINAL: <integer>." },
    @{ id="telescoping";  expected='(?im)^FINAL:\s*100/101\s*$'; prompt="Compute sum from k=1 to 100 of 1/(k(k+1)). Explain briefly and end with exactly FINAL: <reduced fraction>." },
    @{ id="python-output";expected='(?im)^FINAL:\s*\[1,4,9\]\s*$';prompt="What does Python print for [x*x for x in range(1,4)]? Explain briefly and end with exactly FINAL: followed by compact JSON only." }
)

# Nombres reales de tensor de la arquitectura qwen4exp, tomados de llama-arch.cpp
# en el PR 27742. Solo las LOOKUP TABLES: blk.N.ple_key / ple_value y
# per_layer_token_embd. Deliberadamente NO incluye ple_norm_*, ple_conv1d ni
# per_layer_proj_norm: esos son compute, mandarlos a CPU es perdida neta.
$script:NgramTensorRegex = "(ple_key|ple_value|per_layer_token_embd)"

function Get-NgramRegex($modelPath) {
    # Confirma contra el GGUF que los tensores existen con ese nombre antes de
    # usarlos en -ot: un regex que no matchea nada falla silencioso (el modelo
    # carga igual, entero en VRAM, y el benchmark "anda" midiendo otra cosa).
    $dump = Join-Path (Split-Path $Server) "llama-gguf.exe"
    if (-not (Test-Path $dump)) { return "" }
    $names = & $dump $modelPath r n 2>$null
    $hits = ($names | Select-String -Pattern $script:NgramTensorRegex).Count
    if ($hits -lt 1) {
        Write-Warning "El GGUF no tiene tensores que matcheen $script:NgramTensorRegex."
        return ""
    }
    Write-Output ("Tensores Ngram/PLE encontrados: " + $hits)
    return $script:NgramTensorRegex
}

function Wait-Healthy([int]$targetPort, [int]$maxSeconds = 900) {
    # Este modelo tarda en cargar: 111 GB con mmap desde SSD no levanta en 60s.
    $deadline = (Get-Date).AddSeconds($maxSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $h = Invoke-RestMethod "http://127.0.0.1:$targetPort/health" -TimeoutSec 3
            if ($h.status -eq "ok") { return }
        } catch {}
        Start-Sleep -Seconds 3
    }
    throw "llama-server no quedo healthy en el puerto $targetPort tras $maxSeconds s"
}

function Get-VramMB {
    try {
        $q = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null
        if (-not $q) { return 0 }
        return (($q | ForEach-Object { [int]$_.Trim() }) | Measure-Object -Sum).Sum
    } catch { return 0 }
}

function Test-NgramLayout($modelPath) {
    # El punto que hace o rompe el offload: si los tensores Ngram/PLE estan
    # interleaved con el resto adentro de un shard, mmap los trae igual y no se
    # ahorra nada. Solo sirve si viven en shards propios.
    $dir = Split-Path $modelPath
    $shards = Get-ChildItem -Path $dir -Filter "*.gguf" | Sort-Object Name
    $dump = Join-Path (Split-Path $Server) "llama-gguf.exe"
    if (-not (Test-Path $dump)) {
        Write-Warning "Sin llama-gguf.exe no se puede verificar el layout del quant."
        return $null
    }
    $report = @()
    foreach ($sh in $shards) {
        $names = & $dump $sh.FullName r n 2>$null
        $ng = ($names | Select-String -Pattern $NgramRegex).Count
        $tot = ($names | Select-String -Pattern '^\s*tensor').Count
        $report += [pscustomobject]@{
            shard = $sh.Name; ngram_tensors = $ng; total_tensors = $tot
            pure_ngram = ($ng -gt 0 -and $tot -gt 0 -and $ng -eq $tot)
        }
    }
    $mixed = $report | Where-Object { $_.ngram_tensors -gt 0 -and -not $_.pure_ngram }
    if ($mixed) {
        Write-Warning ("Layout interleaved: " + $mixed.Count + " shard(s) mezclan Ngram con backbone.")
        Write-Warning "El offload a SSD no va a ahorrar memoria hasta repackear el GGUF."
    }
    return $report
}

function Invoke-Bench($label, $placement, $modeName) {
    $s = $sampling[$modeName]
    $serverArgs = @(
        "-m", $Model, "--host", "127.0.0.1", "--port", "$Port",
        "--ctx-size", "$CtxSize", "--parallel", "1",
        "--n-gpu-layers", "999", "--split-mode", "layer", "--tensor-split", "1,1",
        "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
        "--flash-attn", "on", "--jinja", "--metrics", "--no-warmup",
        "--temp", $s.temp, "--top-p", $s.topP, "--top-k", $s.topK,
        "--min-p", $s.minP, "--presence-penalty", $s.presence
    )
    # OJO: --mmap es el DEFAULT en llama.cpp actual (incluido el PR 27742). No hay
    # que pasarlo; lo que rompe el offload es pasar --no-mmap o --mlock. Por eso
    # el brazo "ram" es el que agrega --no-mmap, no al reves.
    switch ($placement) {
        "gpu" {
            # Ngram/PLE a VRAM junto con el resto. Baseline.
        }
        "ram" {
            # Residencia real en RAM: sin mmap el loader copia los tensores.
            $serverArgs += @("-ot", ($NgramRegex + "=CPU"), "--no-mmap")
        }
        "ssd" {
            # -ot manda los Ngram al backend CPU y mmap (default) deja que el SO
            # los pagine desde el SSD bajo demanda, sin copiarlos a RAM.
            $serverArgs += @("-ot", ($NgramRegex + "=CPU"))
        }
    }

    $log = Join-Path ([IO.Path]::GetTempPath()) ("llamacode-q38fn-" + $label + ".log")
    $proc = Start-Process -FilePath $Server -ArgumentList $serverArgs -PassThru `
                          -RedirectStandardError $log -RedirectStandardOutput ($log + ".out") -WindowStyle Hidden
    $rows = @()
    try {
        Wait-Healthy $Port
        # Foto de memoria despues de cargar y antes de generar: aca se ve si los
        # Ngram quedaron residentes o si el SO los esta paginando desde el SSD.
        Start-Sleep -Seconds 5
        $proc.Refresh()
        $wsMB   = [math]::Round($proc.WorkingSet64 / 1MB, 0)
        $vramMB = Get-VramMB
        Write-Output ("  memoria: working set " + $wsMB + " MB, VRAM " + $vramMB + " MB")
        foreach ($t in $tasks) {
            for ($p = 1; $p -le $Passes; $p++) {
                $body = @{
                    messages = @(@{ role="user"; content=$t.prompt })
                    max_tokens = 2048
                    stream = $false
                } | ConvertTo-Json -Depth 6
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $r = Invoke-RestMethod "http://127.0.0.1:$Port/v1/chat/completions" -Method Post `
                        -ContentType "application/json" -Body $body -TimeoutSec 1800
                $sw.Stop()
                $text = $r.choices[0].message.content
                $genTok = $r.usage.completion_tokens
                $rows += [pscustomobject]@{
                    placement  = $placement
                    mode       = $modeName
                    task       = $t.id
                    pass       = $p
                    seconds    = [math]::Round($sw.Elapsed.TotalSeconds, 2)
                    gen_tokens = $genTok
                    tok_s      = if ($sw.Elapsed.TotalSeconds -gt 0) { [math]::Round($genTok / $sw.Elapsed.TotalSeconds, 2) } else { 0 }
                    correct    = [bool]([regex]::IsMatch($text, $t.expected))
                    ws_mb      = $wsMB
                    vram_mb    = $vramMB
                }
            }
        }
    } finally {
        if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
    }
    return $rows
}

if (-not $NgramRegex) {
    $NgramRegex = Get-NgramRegex $Model
    if (-not $NgramRegex) {
        Write-Warning "No se pudo verificar contra el GGUF; usando los nombres de llama-arch.cpp."
        $NgramRegex = $script:NgramTensorRegex
    }
}
Write-Output ("Ngram/PLE regex: " + $NgramRegex)
$layout = Test-NgramLayout $Model
if ($layout) { $layout | Format-Table -AutoSize }

$modes = if ($Mode -eq "both") { @("thinking","instruct") } else { @($Mode) }
$all = @()
foreach ($m in $modes) {
    foreach ($placement in @("gpu","ram","ssd")) {
        Write-Output ("== " + $m + " / ngram=" + $placement + " ==")
        $all += Invoke-Bench ($m + "-" + $placement) $placement $m
    }
}

$all | Format-Table -AutoSize
Write-Output ""
Write-Output "== Resumen =="
$all | Group-Object placement, mode | ForEach-Object {
    $g = $_.Group
    [pscustomobject]@{
        placement = $g[0].placement
        mode      = $g[0].mode
        avg_tok_s = [math]::Round(($g | Measure-Object tok_s -Average).Average, 2)
        accuracy  = [math]::Round((($g | Where-Object correct).Count / $g.Count) * 100, 1)
        ws_mb     = $g[0].ws_mb
        vram_mb   = $g[0].vram_mb
    }
} | Format-Table -AutoSize

if ($Output) {
    $all | ConvertTo-Json -Depth 5 | Set-Content -Path $Output -Encoding UTF8
    Write-Output ("Resultados en " + $Output)
}
