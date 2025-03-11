# CheckMK local script format
Write-Output "<<<local>>>"

# Get DNS Server Service status
$service = Get-Service -Name "DNS" -ErrorAction SilentlyContinue

if ($service -and $service.Status -eq "Running") {
    Write-Output "0 DNS_SERVER - OK - DNS Server is running"
} else {
    Write-Output "2 DNS_SERVER - CRITICAL - DNS Server is NOT running!"
}
