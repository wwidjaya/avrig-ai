[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Target,

    [string]$Message = "",

    [switch]$NoPush,

    [switch]$SkipBump,

    [switch]$Force
)

$ErrorActionPreference = "Stop"

$SemVerRegex = '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'

# Repository roots. avrig-ai holds the canonical SemVer source of truth.
$AgenticRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RepoOrder = @("avrig-ai", "avrig-api", "avrig-lib", "avrig-ui")
$Repos = [ordered]@{}
foreach ($name in $RepoOrder) {
    $path = Join-Path $AgenticRoot $name
    if (-not (Test-Path (Join-Path $path ".git"))) {
        throw "Missing git repository: $path"
    }
    $Repos[$name] = $path
}

$CanonicalCargo = Join-Path $Repos["avrig-ai"] "Cargo.toml"
$WebPackage = Join-Path $Repos["avrig-ai"] "apps\web\package.json"
$ApiCargo = Join-Path $Repos["avrig-api"] "Cargo.toml"

function Get-CanonicalVersion {
    $content = Get-Content -Raw $CanonicalCargo
    if ($content -match '(?m)\[workspace\.package\][\s\S]*?^version\s*=\s*"([^"]+)"') {
        return $matches[1]
    }
    throw "Could not find [workspace.package] version in $CanonicalCargo"
}

$current = Get-CanonicalVersion
if ($current -notmatch $SemVerRegex) {
    throw "Current version '$current' does not conform to SemVer 2.0"
}
$major = [int]$matches[1]
$minor = [int]$matches[2]
$patch = [int]$matches[3]

if ($SkipBump) {
    $new = $Target
    if ($new -notmatch $SemVerRegex) {
        throw "Target '$Target' must be a full SemVer 2.0 version when -SkipBump is used"
    }
    Write-Host "Skipping bump, releasing current manifests as $new"
} else {
    switch ($Target.ToLowerInvariant()) {
        "patch" { $new = "$major.$minor.$($patch + 1)" }
        "minor" { $new = "$major.$($minor + 1).0" }
        "major" { $new = "$($major + 1).0.0" }
        default {
            if ($Target -notmatch $SemVerRegex) {
                throw "Target '$Target' is not a valid SemVer 2.0 version or one of patch|minor|major"
            }
            $new = $Target
        }
    }
}

if ($new -eq $current -and -not $SkipBump) {
    throw "Version is already $current, nothing to release"
}

Write-Host "Releasing avrig $current -> $new"

# 1. Synchronize manifest versions.
if (-not $SkipBump) {
$cargoContent = Get-Content -Raw $CanonicalCargo
$workspaceRegex = [regex]'(?m)(\[workspace\.package\][\s\S]*?^version\s*=\s*)"[^"]+"'
$cargoContent = $workspaceRegex.Replace($cargoContent, ('${1}"' + $new + '"'), 1)
Set-Content -Path $CanonicalCargo -Value $cargoContent -NoNewline
Write-Host "Updated $CanonicalCargo"

$webPkg = Get-Content -Raw $WebPackage | ConvertFrom-Json
$webPkg.version = $new
Set-Content -Path $WebPackage -Value (($webPkg | ConvertTo-Json -Depth 10) + "`n") -NoNewline
Write-Host "Updated $WebPackage"

$apiContent = Get-Content -Raw $ApiCargo
$apiContent = [regex]::Replace($apiContent, '(?m)^version\s*=\s*"[^"]+"', "version = `"$new`"")
Set-Content -Path $ApiCargo -Value $apiContent -NoNewline
Write-Host "Updated $ApiCargo"

# 2. Refresh lockfiles so the released version is recorded.
Push-Location $Repos["avrig-ai"]
try {
    cargo metadata --format-version 1 --no-deps | Out-Null
} finally { Pop-Location }
Push-Location $Repos["avrig-api"]
try {
    cargo metadata --format-version 1 --no-deps | Out-Null
} finally { Pop-Location }
Write-Host "Refreshed Cargo.lock in avrig-ai and avrig-api"
}

# 3. Guard against staging credentials.
$secretPatterns = @(
    'sk-[A-Za-z0-9]{20,}',
    'AKIA[0-9A-Z]{16}',
    'ghp_[A-Za-z0-9]{30,}',
    '-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'xox[baprs]-[A-Za-z0-9-]{10,}'
)

$releaseMessage = if ($Message) { $Message } else { "chore(release): avrig $new" }

$results = @()

foreach ($name in $RepoOrder) {
    $path = $Repos[$name]
    Write-Host ""
    Write-Host "=== $name ===" -ForegroundColor Cyan

    git -C $path add -A | Out-Null
    $staged = git -C $path diff --cached --name-only

    if ($staged) {
        $patchText = git -C $path diff --cached
        $hits = @()
        foreach ($pattern in $secretPatterns) {
            if ($patchText -match $pattern) { $hits += $pattern }
        }
        if ($hits.Count -gt 0 -and -not $Force) {
            throw "Aborting release: staged content in $name matches credential patterns ($($hits -join ', ')). Review the staged diff, add the files to .gitignore, or re-run with -Force."
        }

        git -C $path commit -m $releaseMessage | Out-Null
        Write-Host "Committed $(($staged | Measure-Object).Count) files"
    } else {
        Write-Host "No pending changes, tagging current HEAD"
    }

    $existing = git -C $path tag --list $new
    if ($existing) {
        Write-Host "Tag $new already exists locally, reusing"
    } else {
        git -C $path tag -a $new -m "avrig $new" | Out-Null
        Write-Host "Created annotated tag $new"
    }

    if ($NoPush) {
        Write-Host "Skipping push (-NoPush)"
    } else {
        $branch = git -C $path rev-parse --abbrev-ref HEAD
        git -C $path push origin $branch 2>&1 | Out-Null
        git -C $path push origin $new 2>&1 | Out-Null
        Write-Host "Pushed $branch and tag $new"
    }

    $sha = git -C $path rev-parse --short HEAD
    $branchName = git -C $path rev-parse --abbrev-ref HEAD
    $results += [pscustomobject]@{
        Repo   = $name
        Branch = $branchName
        Commit = $sha
        Tag    = $new
    }
}

Write-Host ""
Write-Host "=== Release $new ===" -ForegroundColor Green
$results | Format-Table -AutoSize

if (-not $NoPush) {
    Write-Host "Verifying tags on remotes..."
    foreach ($name in $RepoOrder) {
        $remoteTags = git -C $Repos[$name] ls-remote --tags origin $new
        if ($remoteTags) {
            Write-Host ("  {0}: tag {1} present on origin" -f $name, $new)
        } else {
            Write-Warning ("  {0}: tag {1} NOT found on origin" -f $name, $new)
        }
    }
}

Write-Host "Release $new completed."
