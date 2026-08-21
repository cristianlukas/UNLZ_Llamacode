param(
    [int]$Port = 18766,
    [string]$Root = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$resolvedRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
$listener = [Net.HttpListener]::new()
$listener.Prefixes.Add("http://127.0.0.1:$Port/")

function Get-ContentType([string]$Path) {
    switch ([IO.Path]::GetExtension($Path).ToLowerInvariant()) {
        '.html' { 'text/html; charset=utf-8'; break }
        '.css' { 'text/css; charset=utf-8'; break }
        '.js' { 'text/javascript; charset=utf-8'; break }
        '.json' { 'application/json; charset=utf-8'; break }
        default { 'application/octet-stream' }
    }
}

$apiCache = @()
$apiCacheAt = [DateTime]::MinValue

function Get-ListeningLocalPorts {
    $ports = @()
    $llamaProcessIds = @(Get-Process -Name 'LlamaCode' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    try {
        $connections = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
            Where-Object { $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '::1', '::') })
        if ($llamaProcessIds.Count -gt 0) {
            $connections = @($connections | Where-Object { $llamaProcessIds -contains $_.OwningProcess })
        }
        $ports = @($connections |
            Select-Object -ExpandProperty LocalPort -Unique)
    } catch {
        # Get-NetTCPConnection may be unavailable on older Windows images.
        $ports = @(netstat -ano -p tcp 2>$null | ForEach-Object {
            if ($_ -match 'LISTENING\s+\d+$' -and $_ -match '(?:127\.0\.0\.1|0\.0\.0\.0|\[::\]|::):(?<port>\d+)') {
                [int]$Matches.port
            }
        } | Sort-Object -Unique)
    }
    # Keep the documented/default ports as a cheap fallback when the daemon
    # is hosted by a wrapper process instead of LlamaCode.exe.
    return @($ports + 8765 + 18774 | Where-Object { $_ -and $_ -ne $Port } | Sort-Object -Unique)
}

function Get-BenchmarkApiCandidates {
    $now = Get-Date
    if (($now - $apiCacheAt).TotalSeconds -lt 2) { return @($apiCache) }

    # La validación semántica (/health + /methods) la hace el navegador en
    # paralelo. Acá sólo enumeramos candidatos baratos; no bloqueamos el
    # servidor estático esperando servicios no relacionados.
    $found = @(Get-ListeningLocalPorts | ForEach-Object {
        [pscustomobject]@{ url = "http://127.0.0.1:$_"; port = [int]$_ }
    })
    $apiCache = @($found | Sort-Object port)
    $apiCacheAt = $now
    return @($apiCache)
}

try {
    $listener.Start()
    Write-Host "Benchmark dashboard: http://127.0.0.1:$Port/benchmark-dashboard.html"
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        try {
            $relative = [Uri]::UnescapeDataString($context.Request.Url.AbsolutePath.TrimStart('/'))
            if ([string]::IsNullOrWhiteSpace($relative)) { $relative = 'benchmark-dashboard.html' }
            if ($relative -eq 'favicon.ico') {
                $context.Response.StatusCode = 204
                $context.Response.Close()
                continue
            }
            if ($relative -eq 'benchmark-api.json') {
                $payload = [ordered]@{
                    ok = $true
                    generatedAt = (Get-Date).ToUniversalTime().ToString('o')
                    apis = @(Get-BenchmarkApiCandidates)
                }
                $bytes = [Text.Encoding]::UTF8.GetBytes(($payload | ConvertTo-Json -Depth 4 -Compress))
                $context.Response.ContentType = 'application/json; charset=utf-8'
                $context.Response.ContentLength64 = $bytes.Length
                $context.Response.Headers['Cache-Control'] = 'no-store'
                $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
                $context.Response.Close()
                continue
            }
            $candidate = [IO.Path]::GetFullPath((Join-Path $resolvedRoot $relative))
            if (-not $candidate.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
                $context.Response.StatusCode = 404
                $context.Response.Close()
                continue
            }
            $bytes = [IO.File]::ReadAllBytes($candidate)
            $context.Response.ContentType = Get-ContentType $candidate
            $context.Response.ContentLength64 = $bytes.Length
            $context.Response.Headers['Cache-Control'] = 'no-store'
            $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
            $context.Response.Close()
        } catch {
            try { $context.Response.StatusCode = 500; $context.Response.Close() } catch { }
        }
    }
} finally {
    if ($listener.IsListening) { $listener.Stop() }
    $listener.Close()
}
