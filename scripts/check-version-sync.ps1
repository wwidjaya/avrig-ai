$cargoVersion = (Get-Content -Raw Cargo.toml | Select-String '\[workspace\.package\][\s\S]*?version\s*=\s*"([^"]+)"').Matches.Groups[1].Value
$webVersion = (Get-Content -Raw apps/web/package.json | ConvertFrom-Json).version
Write-Host "Cargo version:   $cargoVersion"
Write-Host "Web app version: $webVersion"
if ($cargoVersion -ne $webVersion) {
    Write-Error "Version mismatch: Cargo.toml ($cargoVersion) != apps/web/package.json ($webVersion)"
    exit 1
} else {
    Write-Host "Version check passed: all manifests synchronized."
}
