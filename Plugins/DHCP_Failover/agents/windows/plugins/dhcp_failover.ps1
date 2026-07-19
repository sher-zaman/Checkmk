# Checkmk agent plugin: DHCP failover relationship monitoring (Windows)
#
# Author: Sher Zaman (FirmaTrust)
# License: GPLv2
#
# Emits one line per DHCPv4 failover relationship configured on this server.
# All state evaluation is done server-side by the dhcp_failover check plugin.
#
# Section format (pipe separated):
#   name|state|mode|partner_server|server_role|scope_count|scope1,scope2,...
#
# Deployment: via Agent Bakery rule "DHCP failover monitoring (Windows)"
# or manually to C:\ProgramData\checkmk\agent\plugins\dhcp_failover.ps1

# Exit silently if the DHCP Server role / PowerShell module is not present,
# so no section is emitted and no service is discovered on non-DHCP hosts.
if (-not (Get-Command Get-DhcpServerv4Failover -ErrorAction SilentlyContinue)) {
    exit 0
}

function Sanitize([string]$value) {
    if ($null -eq $value) { return "" }
    # Field separator is the pipe character; strip it from values just in case.
    return ($value -replace '\|', '/').Trim()
}

Write-Output "<<<dhcp_failover:sep(124)>>>"

try {
    $relationships = Get-DhcpServerv4Failover -ErrorAction Stop
} catch {
    Write-Output ("__query_error__|" + (Sanitize $_.Exception.Message))
    exit 0
}

foreach ($rel in @($relationships)) {
    $name    = Sanitize $rel.Name
    $state   = Sanitize $rel.State
    $mode    = Sanitize $rel.Mode
    $partner = Sanitize $rel.PartnerServer
    $role    = Sanitize $rel.ServerRole   # Empty for LoadBalance mode

    $scopes = @($rel.ScopeId | ForEach-Object { $_.ToString() })
    $scopeCount = $scopes.Count
    $scopeList = Sanitize ($scopes -join ",")

    Write-Output "$name|$state|$mode|$partner|$role|$scopeCount|$scopeList"
}

exit 0
