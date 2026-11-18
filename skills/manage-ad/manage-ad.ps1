param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$WslDist = "ad"
$BaseDn = "DC=wirianto,DC=ai"
$SamLdb = "/var/lib/samba/private/sam.ldb"

if ($ArgsList.Count -lt 1) {
    Write-Error "Usage: manage-ad.ps1 <samba-tool command...> | search <filter> [attrs...]"
    exit 1
}

$quote = { "'" + ($_ -replace "'", "'\''") + "'" }

if ($ArgsList[0] -eq "search") {
    if ($ArgsList.Count -lt 2) {
        Write-Error "search requires an LDAP filter, e.g. '(objectClass=user)'"
        exit 1
    }
    $filter = $ArgsList[1]
    $attrs = @($ArgsList[2..($ArgsList.Count - 1)] | ForEach-Object $quote) -join ' '
    $cmd = "ldbsearch -H $SamLdb -b '$BaseDn' '$filter' $attrs 2>&1 | grep -vE 'WARNING|setproctitle'"
} else {
    $rest = @($ArgsList | ForEach-Object $quote) -join ' '
    $cmd = "samba-tool $rest 2>&1 | grep -vE 'WARNING|setproctitle'"
}

wsl -u root -d $WslDist -- bash -lc $cmd
