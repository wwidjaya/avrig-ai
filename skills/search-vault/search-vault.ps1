param(
    [string]$Keywords,
    [string]$VaultPath = "D:\Cloud\OneDrive\AI\Personal\vault",
    [int]$TopN = 5
)

$kw = ($Keywords -split '\s+|,') | Where-Object { $_.Trim() -ne '' }
if ($kw.Count -lt 1) {
    Write-Error "At least one keyword required (-Keywords 'term1 term2')"
    exit 1
}

$pattern = $kw -join '|'
$useRg = $null -ne (Get-Command rg -ErrorAction SilentlyContinue)

$matches = if ($useRg) {
    rg -i -n --no-heading "$pattern" "$VaultPath" --include '*.md' 2>$null
} else {
    Get-ChildItem "$VaultPath" -Recurse -Filter '*.md' | Select-String -Pattern "$pattern" -CaseSensitive:$false
}

$scores = @{}
foreach ($m in $matches) {
    $file = if ($useRg) { ($m -split ':')[0] } else { $m.Path }
    $line = if ($useRg) { ($m -split ':', 3)[2] } else { $m.Line }
    
    $w = if ($line -match "^title:\s+.*$pattern" -or $line -match "^#\s+.*$pattern") { 10 }
         elseif ($line -match "^#{2,}\s+.*$pattern") { 5 }
         else { 1 }
         
    $scores[$file] = ($scores[$file] ?? 0) + $w
}

$scores.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First $TopN | ForEach-Object {
    "$($_.Key)|$($_.Value)"
}