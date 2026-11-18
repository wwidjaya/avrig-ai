#!/usr/bin/env pwsh
# Gmail skill wrapper (Windows) — runs himalaya against the skill-local config.
#
# Pass-through to `himalaya` that pins account `gmail` and the skill-local
# config. himalaya splits `-c` paths on `:` (PATH-style list), so we cd into
# the config directory and pass a relative `config.toml` — that works on
# Windows drive letters. Because the cwd changes, pass ABSOLUTE paths for any
# --body-file / --attach / -d arguments.
[CmdletBinding(PositionalBinding = $false)]
param(
    # himalaya account to run against (gmail | composync). Defaults to gmail.
    [Parameter()][string]$Account = "gmail",
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$HimalayaArgs
)

$ErrorActionPreference = "Stop"

$himalayaDir = Join-Path $PSScriptRoot "himalaya"
$cfgPath = Join-Path $himalayaDir "config.toml"
if (-not (Test-Path -LiteralPath $cfgPath)) {
    Write-Error "Config not found: $cfgPath. Copy himalaya\config.toml.example to himalaya\config.toml and fill it in first."
    exit 1
}

$himalaya = Get-Command himalaya -ErrorAction SilentlyContinue
if (-not $himalaya) {
    Write-Error "himalaya not found on PATH (installed at D:\rust\cargo\bin). See SKILL.md Setup section."
    exit 1
}

Push-Location -LiteralPath $himalayaDir
try {
    & $himalaya.Source -c "config.toml" -a $Account @HimalayaArgs
    exit $LASTEXITCODE
}
finally { Pop-Location }
