[CmdletBinding()]
param(
    # Optional so that -Range verification runs do not need a version argument.
    # Normal releases still refuse to run without it (checked further down).
    [Parameter(Position = 0)]
    [string]$Target = "",

    [string]$Message = "",

    [switch]$NoPush,

    [switch]$SkipBump,

    [switch]$Force,

    # Verification-only mode: rescan an already created tag's release commit
    # ("git log -p <tag>~1..<tag>") instead of staging anything.
    [switch]$Range,

    # Tag inspected by -Range. Supplying it on its own also implies -Range.
    [string]$RangeTag = ""
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

# ---------------------------------------------------------------------------
# Credential and artifact guards (shared by the staged scan and range mode).
# ---------------------------------------------------------------------------

# Content patterns that must never reach a release commit.
# The private-key entry is deliberately left open-ended so that a truncated
# paste (header without the closing dashes) still matches.
$secretPatterns = @(
    'sk-[A-Za-z0-9]{20,}',
    'AKIA[0-9A-Z]{16}',
    'ghp_[A-Za-z0-9]{30,}',
    '-----BEGIN [A-Z ]*PRIVATE KEY',
    'xox[baprs]-[A-Za-z0-9-]{10,}',
    'ATATT3x[A-Za-z0-9_-]{20,}',
    'GOCSPX-[A-Za-z0-9_-]{20,}',
    '1071006060591-[a-z0-9]{6,}'
)

# Hardcoded secret assignments in release helper shells. Requires a quoted
# literal of at least 12 characters; "$VAR" and "$(cmd)" references are
# excluded by the negated '$' so indirection does not trip the rule.
$secretAssignmentPattern = '(SECRET|TOKEN|PASSWORD)=["''][^"''$]{12,}'

# Staged paths that must not be committed.
# NOTE: only apps/web/dist is gitignored. packages/ui/dist,
# packages/api-client/dist, apps/mobile/dist and apps/desktop/dist are tracked
# build artifacts that the release legitimately commits, so a blanket
# 'apps/*/dist' rule would break the release. Block exactly apps/web/dist.
$blockedPathPatterns = @(
    @{ Pattern = '(^|/)\.env$'; Reason = 'environment file' },
    @{ Pattern = '(^|/)confluence\.env$'; Reason = 'Confluence credentials' },
    @{ Pattern = '\.pem$'; Reason = 'PEM key/certificate' },
    @{ Pattern = '\.p12$'; Reason = 'PKCS#12 keystore' },
    @{ Pattern = '(^|/)target/'; Reason = 'Rust build output' },
    @{ Pattern = '(^|/)node_modules/'; Reason = 'dependency tree' },
    @{ Pattern = '(^|/)apps/web/dist/'; Reason = 'gitignored web bundle (apps/web/dist)' }
)

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & git -C $RepoPath @GitArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) {
        throw ("git " + ($GitArgs -join " ") + " failed in $RepoPath (exit $code): " + (($output | Out-String).Trim()))
    }
    return $output
}

# Call git with an explicit argument array. Preferred over positional
# invocation because PowerShell prefix-matches parameter names: '-p' or '-r'
# after the repo path would bind to -RepoPath and be silently dropped, which
# makes 'git log -p' quietly run without a patch.
function Invoke-GitEx {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][string[]]$GitArgs
    )
    return Invoke-Git -RepoPath $RepoPath -GitArgs $GitArgs
}

function Get-SecretPatternHits {
    param([string]$Text)
    $hits = @()
    if (-not $Text) { return $hits }
    foreach ($pattern in $secretPatterns) {
        if ($Text -match $pattern) { $hits += $pattern }
    }
    return $hits
}

function Get-BlockedPathHits {
    param([string[]]$Paths)
    $hits = @()
    foreach ($candidate in $Paths) {
        if (-not $candidate) { continue }
        $normalized = $candidate -replace '\\', '/'
        foreach ($rule in $blockedPathPatterns) {
            if ($normalized -match $rule.Pattern) {
                $hits += ("{0} ({1})" -f $normalized, $rule.Reason)
            }
        }
    }
    return $hits
}

function Get-SecretAssignmentHits {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [string[]]$Paths
    )
    $hits = @()
    $targets = @($Paths | Where-Object { $_ -and (($_ -replace '\\', '/') -match '^scripts/.*\.sh$') })
    foreach ($relative in $targets) {
        $full = Join-Path $RepoPath $relative
        if (-not (Test-Path -LiteralPath $full)) { continue }
        $lineNumber = 0
        foreach ($line in Get-Content -LiteralPath $full) {
            $lineNumber++
            if ($line -match $secretAssignmentPattern) {
                $hits += ("{0}:{1}" -f $relative, $lineNumber)
            }
        }
    }
    return $hits
}

# ---------------------------------------------------------------------------
# Range mode: rescan an existing tag's release commit, staging nothing.
#   powershell -File scripts/release.ps1 -Range -RangeTag 0.3.0
# Supplying -RangeTag alone implies -Range.
# ---------------------------------------------------------------------------
if ($Range -or $RangeTag) {
    if (-not $RangeTag) {
        throw "-Range requires -RangeTag <tag> (for example -RangeTag 0.3.0)"
    }

    Write-Host "Range scan: git log -p $RangeTag~1..$RangeTag" -ForegroundColor Cyan
    $rangeFailures = 0

    foreach ($name in $RepoOrder) {
        $path = $Repos[$name]
        Write-Host ""
        Write-Host "=== $name ===" -ForegroundColor Cyan

        $hasCommit = $false
        try {
            $resolved = Invoke-GitEx -RepoPath $path -GitArgs @('rev-parse', '--verify', '--quiet', "$RangeTag^{commit}")
            $hasCommit = [bool]$resolved
        } catch {
            $hasCommit = $false
        }
        if (-not $hasCommit) {
            Write-Warning "Tag $RangeTag not found in $name, skipping"
            continue
        }

        $patchText = (Invoke-GitEx -RepoPath $path -GitArgs @('log', '--patch', '--no-color', "$($RangeTag)~1..$($RangeTag)")) -join "`n"
        $contentHits = Get-SecretPatternHits $patchText

        # Path rules are staging-independent, so re-check the commit's file list.
        # Deleted paths are excluded: removing a file cannot leak its contents.
        $changed = @(Invoke-GitEx -RepoPath $path -GitArgs @('show', '--name-only', '--pretty=format:', '--diff-filter=d', $RangeTag))
        $pathHits = Get-BlockedPathHits $changed

        # Added lines only: deletions are reported by the content patterns above.
        $addedLines = ($patchText -split "`n" | Where-Object { $_ -match '^\+' -and $_ -notmatch '^\+\+\+' }) -join "`n"
        $assignmentHits = @()
        foreach ($line in ($addedLines -split "`n")) {
            if ($line -match $secretAssignmentPattern) { $assignmentHits += $line.Trim() }
        }

        $hits = @($contentHits) + @($pathHits) + @($assignmentHits)
        if ($hits.Count -gt 0) {
            $rangeFailures++
            Write-Warning ("{0}: {1} finding(s)" -f $name, $hits.Count)
            foreach ($hit in $hits) { Write-Host ("  - {0}" -f $hit) -ForegroundColor Yellow }
        } else {
            Write-Host "Clean: no credential patterns or blocked paths in $RangeTag" -ForegroundColor Green
        }
    }

    Write-Host ""
    if ($rangeFailures -gt 0) {
        # Report only: range mode is a read-only re-check, so it never aborts.
        Write-Warning ("Range scan of {0} found findings in {1} repository/repositories. Review the lines above." -f $RangeTag, $rangeFailures)
    } else {
        Write-Host "Range scan of $RangeTag clean: no credential patterns or blocked paths." -ForegroundColor Green
    }
    Write-Host "Range scan completed, nothing was staged, committed, or pushed." -ForegroundColor Green
    return
}

if (-not $Target) {
    throw "Missing release target. Pass patch|minor|major or an explicit SemVer version (or use -Range -RangeTag <tag> to rescan an existing tag)."
}

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

$releaseMessage = if ($Message) { $Message } else { "chore(release): avrig $new" }

$results = @()

foreach ($name in $RepoOrder) {
    $path = $Repos[$name]
    Write-Host ""
    Write-Host "=== $name ===" -ForegroundColor Cyan

    # Working-tree warning: 'git add -A' sweeps everything, not just the bump.
    $dirty = @(Invoke-GitEx -RepoPath $path -GitArgs @('status', '--porcelain'))
    if ($dirty.Count -gt 0 -and -not $Force) {
        Write-Warning ("{0} has {1} uncommitted path(s). 'git add -A' will sweep EVERY change in this repository into the release commit '{2}', not just the version bump:" -f $name, $dirty.Count, $releaseMessage)
        foreach ($entry in ($dirty | Select-Object -First 10)) {
            Write-Warning ("  {0}" -f $entry)
        }
        if ($dirty.Count -gt 10) {
            Write-Warning ("  ... and {0} more" -f ($dirty.Count - 10))
        }
        Write-Warning "Re-run with -Force to silence this warning. Continuing regardless."
    }

    Invoke-GitEx -RepoPath $path -GitArgs @('add', '-A') | Out-Null
    $staged = Invoke-GitEx -RepoPath $path -GitArgs @('diff', '--cached', '--name-only')

    if ($staged) {
        $patchText = (Invoke-GitEx -RepoPath $path -GitArgs @('diff', '--cached')) -join "`n"

        $contentHits = Get-SecretPatternHits $patchText
        if ($contentHits.Count -gt 0 -and -not $Force) {
            throw "Aborting release: staged content in $name matches credential patterns ($($contentHits -join ', ')). Review the staged diff, add the files to .gitignore, or re-run with -Force."
        }

        # Path assertions: run before committing so bad artifacts never land.
        $pathHits = Get-BlockedPathHits $staged
        if ($pathHits.Count -gt 0 -and -not $Force) {
            throw ("Aborting release: {0} staged path(s) must not be committed: {1}. Unstage them (`git reset HEAD <path>`) or re-run with -Force." -f $name, ($pathHits -join ', '))
        }

        # Hardcoded credentials in staged release helper scripts.
        $assignmentHits = Get-SecretAssignmentHits -RepoPath $path -Paths $staged
        if ($assignmentHits.Count -gt 0 -and -not $Force) {
            throw ("Aborting release: {0} staged script(s) hardcode credential assignments: {1}. Replace the literals with environment variable references." -f $name, ($assignmentHits -join ', '))
        }

        Invoke-GitEx -RepoPath $path -GitArgs @('commit', '-m', $releaseMessage) | Out-Null
        Write-Host "Committed $(($staged | Measure-Object).Count) files"
    } else {
        Write-Host "No pending changes, tagging current HEAD"
    }

    $existing = Invoke-GitEx -RepoPath $path -GitArgs @('tag', '--list', $new)
    if ($existing) {
        Write-Host "Tag $new already exists locally, reusing"
    } else {
        Invoke-GitEx -RepoPath $path -GitArgs @('tag', '-a', $new, '-m', "avrig $new") | Out-Null
        Write-Host "Created annotated tag $new"
    }

    if ($NoPush) {
        Write-Host "Skipping push (-NoPush)"
    } else {
        $branch = Invoke-GitEx -RepoPath $path -GitArgs @('rev-parse', '--abbrev-ref', 'HEAD')
        Invoke-GitEx -RepoPath $path -GitArgs @('push', 'origin', $branch) | Out-Null
        Invoke-GitEx -RepoPath $path -GitArgs @('push', 'origin', $new) | Out-Null
        Write-Host "Pushed $branch and tag $new"
    }

    $sha = Invoke-GitEx -RepoPath $path -GitArgs @('rev-parse', '--short', 'HEAD')
    $branchName = Invoke-GitEx -RepoPath $path -GitArgs @('rev-parse', '--abbrev-ref', 'HEAD')
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
        $remoteTags = Invoke-GitEx -RepoPath $Repos[$name] -GitArgs @('ls-remote', '--tags', 'origin', $new)
        if ($remoteTags) {
            Write-Host ("  {0}: tag {1} present on origin" -f $name, $new)
        } else {
            Write-Warning ("  {0}: tag {1} NOT found on origin" -f $name, $new)
        }
    }
}

Write-Host "Release $new completed."
