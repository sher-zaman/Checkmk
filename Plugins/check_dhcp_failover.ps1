# CheckMK Plugin Script - DHCP Failover Monitoring
# Place this script in C:\ProgramData\checkmk\agent\plugins\

# Get DHCP failover status
$failoverStatus = Get-DhcpServerv4Failover | Select-Object ScopeId, State

# Initialize output variables
$exitCode = 0
$statusMsg = "OK - All DHCP failover scopes are normal"
$criticalIssues = @()
$warningIssues = @()

# Check if failover data exists
if ($failoverStatus) {
    foreach ($entry in $failoverStatus) {
        switch ($entry.State) {
            "Normal" { continue }
            "CommunicationInterrupted" { $warningIssues += "$($entry.ScopeId): $($entry.State)"; $exitCode = [math]::Max($exitCode, 1) }
            default { $criticalIssues += "$($entry.ScopeId): $($entry.State)"; $exitCode = 2 }
        }
    }

    if ($criticalIssues) {
        $statusMsg = "CRITICAL - Failover Issues: " + ($criticalIssues -join ", ")
    } elseif ($warningIssues) {
        $statusMsg = "WARNING - Failover Issues: " + ($warningIssues -join ", ")
    }
} else {
    $statusMsg = "UNKNOWN - No failover configuration found"
    $exitCode = 3
}

# Output for CheckMK format
Write-Output "<<<local>>>"
Write-Output "$exitCode DHCP_FAILOVER - $statusMsg"

# Ensure the correct exit code for monitoring
exit $exitCode
