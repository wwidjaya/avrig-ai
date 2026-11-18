[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Target
)

$ErrorActionPreference = "Stop"

# Strict SemVer 2.0 regex
$SemVerRegex = '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'

$RootDir = Resolve-Path "$PSScriptRoot\.."
$CargoTomlPath = Join-Path $RootDir "Cargo.toml"
$WebPackageJsonPath = Join-Path $RootDir "apps\web\package.json"

if (-not (Test-Path $CargoTomlPath)) {
    Write-Error "Cargo.toml not found at $CargoTomlPath"
    exit 1
}

$cargoContent = Get-Content -Raw $CargoTomlPath
if ($cargoContent -match '\[workspace\.package\][\s\S]*?version\s*=\s*"([^"]+)"') {
    $currentVersion = $matches[1]
} else {
    Write-Error "Could not find [workspace.package] version in $CargoTomlPath"
    exit 1
}

Write-Host "Current workspace version: $currentVersion"

if ($currentVersion -notmatch $SemVerRegex) {
    Write-Error "Current version '$currentVersion' does not conform to SemVer 2.0"
    exit 1
}

$currentMajor = [int]$matches[1]
$currentMinor = [int]$matches[2]
$currentPatch = [int]$matches[3]

$newVersion = ""

switch ($Target.ToLowerInvariant()) {
    "patch" {
        $newVersion = "$currentMajor.$currentMinor.$($currentPatch + 1)"
    }
    "minor" {
        $newVersion = "$currentMajor.$($currentMinor + 1).0"
    }
    "major" {
        $newVersion = "$($currentMajor + 1).0.0"
    }
    default {
        if ($Target -notmatch $SemVerRegex) {
            Write-Error "Target version '$Target' is not a valid SemVer 2.0 string (or patch/minor/major command)"
            exit 1
        }
        $newVersion = $Target
    }
}

Write-Host "Updating workspace version to: $newVersion"

# 1. Update Cargo.toml [workspace.package] version
$updatedCargoContent = [regex]::Replace(
    $cargoContent,
    '(\[workspace\.package\][\s\S]*?version\s*=\s*)"[^"]+"',
    "`${1}`"$newVersion`""
)
Set-Content -Path $CargoTomlPath -Value $updatedCargoContent -NoNewline

# 2. Update apps/web/package.json version if it exists
if (Test-Path $WebPackageJsonPath) {
    $webPkg = Get-Content -Raw $WebPackageJsonPath | ConvertFrom-Json
    $webPkg.version = $newVersion
    $webJsonUpdated = ($webPkg | ConvertTo-Json -Depth 10) + "`n"
    Set-Content -Path $WebPackageJsonPath -Value $webJsonUpdated -NoNewline
    Write-Host "Updated $WebPackageJsonPath"
}

# 3. Synchronize Cargo.lock
Write-Host "Running 'cargo check --workspace' to sync Cargo.lock..."
Push-Location $RootDir
try {
    cargo check --workspace
} finally {
    Pop-Location
}

Write-Host "Successfully bumped version to $newVersion"
