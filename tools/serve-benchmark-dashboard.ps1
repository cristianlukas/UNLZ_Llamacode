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
        default { 'application/octet-stream' }
    }
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
