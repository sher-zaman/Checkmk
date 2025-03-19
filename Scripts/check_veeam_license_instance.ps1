<#
    Checkmk Local Check Plugin - Veeam License and Instance Usage Monitor
    Version: 1.0
    Description:
        Monitors Veeam license expiry days and instance usage percentage,
        and reports appropriate check state (OK/WARN/CRIT) based on thresholds.
#>

try {
    # -------------------------------
    # Configurable Thresholds
    # -------------------------------
    $License_Warn_Days = 30
    $License_Crit_Days = 5

    $Instance_Warn_Percent = 105
    $Instance_Crit_Percent = 110

    # -------------------------------
    # Import Veeam Module
    # -------------------------------
    Import-Module Veeam.Backup.PowerShell -ErrorAction Stop -WarningAction SilentlyContinue

    # -------------------------------
    # License Expiry Check
    # -------------------------------
    $license = Get-VBRInstalledLicense
    $expiryDate = $license.ExpirationDate
    $daysLeft = ($expiryDate - (Get-Date)).Days

    # Determine State
    $stateLicense = if ($daysLeft -lt $License_Crit_Days) {
        2  # CRIT
    } elseif ($daysLeft -lt $License_Warn_Days) {
        1  # WARN
    } else {
        0  # OK
    }

    # -------------------------------
    # Instance Usage Check
    # -------------------------------
    $instanceSummary = Get-VBRInstanceLicenseSummary -License $license
    $totalInstances = $instanceSummary.LicensedInstancesNumber
    $usedInstances = $instanceSummary.UsedInstancesNumber

    # Avoid divide-by-zero
    if ($totalInstances -eq 0) {
        $instanceUsagePercent = 0
    } else {
        $instanceUsagePercent = [math]::Round(($usedInstances / $totalInstances) * 100, 2)
    }

    # Determine State
    $stateInstance = if ($instanceUsagePercent -ge $Instance_Crit_Percent) {
        2  # CRIT
    } elseif ($instanceUsagePercent -ge $Instance_Warn_Percent) {
        1  # WARN
    } else {
        0  # OK
    }

    # -------------------------------
    # Output for Checkmk
    # -------------------------------
    Write-Output "$stateLicense Veeam_License_Expiry license_expiry_days=$daysLeft License expires in $daysLeft days (Thresholds: WARN < $License_Warn_Days, CRIT < $License_Crit_Days)"
    Write-Output "$stateInstance Veeam_Instance_Usage instance_usage_percent=$instanceUsagePercent Used $usedInstances of $totalInstances instances ($instanceUsagePercent%) (Thresholds: WARN ≥ $Instance_Warn_Percent%, CRIT ≥ $Instance_Crit_Percent%)"

} catch {
    # Error fallback
    Write-Output "3 Veeam_License_Expiry - UNKNOWN - Error retrieving license information: $_"
    Write-Output "3 Veeam_Instance_Usage - UNKNOWN - Error retrieving instance usage information: $_"
    exit 1
}

