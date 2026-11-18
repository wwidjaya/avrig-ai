#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Confluence Cloud connector wrapper (Windows).

.DESCRIPTION
    Runs the Python Confluence connector. Credentials come from confluence.env
    next to this script.

    Subcommands:
        space resolve [--key KEY]
        search       -q "text" [--limit N] [--space KEY]
        get          -page-id N [--body json|none]
        create       [-title T] [-parent-id N] [-space-id S] [-no-full-width] -doc FILE.json
        update       -page-id N [-title T] [-version N] -doc FILE.json
        append       -page-id N -doc FILE.json
        full-width   -page-id N

    Bodies use Confluence storage format (table widths in px, default 1800px).
    New pages are created at maximum (full) width by default — the connector
    sets the content-appearance-* properties to full-width. Pass --no-full-width
    to create at the default fixed width instead.
    Title falls back to the model `title` (from note frontmatter), then the
    existing page title (update).

.EXAMPLE
    pwsh confluence-tool.ps1 space resolve
    pwsh confluence-tool.ps1 search -q "User Roles"
    pwsh confluence-tool.ps1 get -page-id 12345
    pwsh confluence-tool.ps1 create -title "New Page" -parent-id 12345 -doc doc.json
    pwsh confluence-tool.ps1 create -parent-id 12345 -doc doc.json
    pwsh confluence-tool.ps1 update -page-id 12345 -version 3 -doc doc.json
    pwsh confluence-tool.ps1 append -page-id 12345 -doc section.json
    pwsh confluence-tool.ps1 full-width -page-id 12345
#>
param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$scriptDir = $PSScriptRoot
$py = Join-Path $scriptDir "confluence_tool.py"

if ($Args.Count -lt 1) {
    Write-Error "Usage: confluence-tool.ps1 <space|search|get|create|update|append|full-width> [args...]"
    exit 1
}

python "$py" @Args
exit $LASTEXITCODE
