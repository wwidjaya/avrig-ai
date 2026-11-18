param(
    [Parameter(Mandatory=$true)][string]$Query,
    [int]$TopK = 5,
    [string]$ServiceUrl = "http://172.26.0.50:18600",
    [switch]$LocalOnly
)

$TopK = [Math]::Min([Math]::Max($TopK, 1), 10)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uri = "$ServiceUrl/search?q=$([uri]::EscapeDataString($Query))&top_k=$TopK"

$usePrimary = -not $LocalOnly
$results = $null

if ($usePrimary) {
    try {
        $results = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 60
    } catch {
        Write-Warning "Primary semantic search unavailable — falling back to keyword search."
        $results = $null
    }
}

if (-not $results -or $results.Count -eq 0) {
    # Fallback: local vault keyword search via search-vault.ps1
    $kw = ($Query -split '\s+') | Where-Object { $_.Trim() -ne '' }
    $kwParams = @{
        Keywords = $kw -join ' '
        VaultPath = "D:\Cloud\OneDrive\AI\Personal\vault"
        TopN     = $TopK
    }
    & "$scriptDir\search-vault.ps1" @kwParams
    exit $LASTEXITCODE
}

$i = 0
foreach ($r in $results) {
    $i++
    $score = "{0:N3}" -f [double]$r.score
    Write-Output "[$i] [$($r.type)] score=$score | $($r.title)"
    Write-Output "    Path:    $($r.filepath)"
    $snip = ($r.snippet -replace '\s+', ' ').Trim()
    if ($snip.Length -gt 200) { $snip = $snip.Substring(0, 200) + "..." }
    Write-Output "    Snippet: $snip"
    Write-Output ""
}

Write-Output "Explanation: type 'vault' = local note (read the full file at Path for complete info, snippet truncated). type 'web' = external source. Scores = reranker relevance (higher = better)."