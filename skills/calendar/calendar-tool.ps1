#!/usr/bin/env pwsh
# Calendar skill wrapper (Windows) — runs calendula against the skill-local config.
#
# Pass-through to `calendula` that pins account `calendar`, backend `gcal`, and
# the skill-local config. We cd into the config dir and pass a relative
# `config.toml` because calendula (like himalaya) splits `-c` paths on `:`
# (PATH-style list), which breaks Windows drive letters. Because the cwd
# changes, pass ABSOLUTE paths for any `<ICAL>` / `-k`/file arguments.
param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$CalendulaArgs
)

$ErrorActionPreference = "Stop"

$calDir = Join-Path $PSScriptRoot "calendula"
$cfgPath = Join-Path $calDir "config.toml"
if (-not (Test-Path -LiteralPath $cfgPath)) {
    Write-Error "Config not found: $cfgPath — copy calendula\config.toml.example to calendula\config.toml and fill it in first."
    exit 1
}

$calendula = Get-Command calendula -ErrorAction SilentlyContinue
if (-not $calendula) {
    Write-Error "calendula not found on PATH (installed at D:\rust\cargo\bin). See SKILL.md → Setup."
    exit 1
}

Push-Location -LiteralPath $calDir
try {
    & $calendula.Source -c "config.toml" -a calendar -b caldav @CalendulaArgs
    exit $LASTEXITCODE
}
finally { Pop-Location }