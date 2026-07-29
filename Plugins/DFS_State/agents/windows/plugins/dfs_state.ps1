# =============================================================================
# dfs_state.ps1  -  Checkmk agent plugin (Windows)
# =============================================================================
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
# =============================================================================
# Reports the operational state of every DFSR replicated folder from the
# root\MicrosoftDFS WMI provider. Consumed by the dfs_state check plugin
# (service "DFS Share <folder>").
#
# WHY THIS SCRIPT IS HARDENED:
#   * The Checkmk agent runs as a 32-bit process. The root\MicrosoftDFS WMI
#     provider is 64-bit only, so a 32-bit query returns an empty namespace
#     and NO <<<dfs_state>>> section is produced. This script relaunches
#     itself under native 64-bit PowerShell (via the sysnative alias) before
#     querying.
#   * Uses Get-CimInstance instead of the deprecated System.Management calls.
#   * Emits sep(9) so folder / group names that contain spaces
#     (e.g. "SYSVOL Share", "Domain System Volume") parse as single fields
#     instead of being split and silently dropped by the check.
#   * Surfaces failures as a visible line in the raw agent output so that
#     "cmk -d <host>" shows the real error instead of an empty section.
#
# MANUAL PLACEMENT:
#   C:\ProgramData\checkmk\agent\plugins\dfs_state.ps1
# =============================================================================

# --- Relaunch under 64-bit PowerShell when running 32-bit on a 64-bit OS -----
if ($env:PROCESSOR_ARCHITECTURE -eq 'x86' -and $env:PROCESSOR_ARCHITEW6432) {
    $scriptPath = $PSCommandPath
    if ([string]::IsNullOrEmpty($scriptPath)) { $scriptPath = $MyInvocation.MyCommand.Path }
    $native = Join-Path $env:WINDIR 'sysnative\WindowsPowerShell\v1.0\powershell.exe'
    if (Test-Path $native) {
        & $native -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $scriptPath
        exit $LASTEXITCODE
    }
}

Write-Output "<<<dfs_state:sep(9)>>>"

try {
    $folders = Get-CimInstance -Namespace 'root\MicrosoftDFS' `
        -ClassName 'DfsrReplicatedFolderInfo' -ErrorAction Stop

    foreach ($f in $folders) {
        # State is an integer 0..5 (0=NotInit,1=Init,2=InitialSync,
        # 3=AutoRecovery,4=Normal,5=Error). Passed through unchanged; the
        # check maps it to OK/WARN/CRIT/UNKNOWN.
        $name  = ($f.ReplicatedFolderName -replace "[\r\n\t]", ' ')
        $group = ($f.ReplicationGroupName  -replace "[\r\n\t]", ' ')
        "{0}`t{1}`t{2}" -f $name, $group, [int]$f.State
    }
}
catch {
    # 3 tab-separated fields keep the check parser safe (it indexes [0..2]).
    # State field "99" is out of the valid 0-5 range, so the check ignores
    # this row rather than crashing, but it remains visible in "cmk -d".
    $msg = ($_.Exception.Message -replace "[\r\n\t]", ' ')
    "ERROR`t{0}`t99" -f $msg
}
