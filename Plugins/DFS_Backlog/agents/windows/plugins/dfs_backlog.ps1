# =============================================================================
# dfs_backlog.ps1  -  Checkmk agent plugin (Windows)
# =============================================================================
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
# =============================================================================
# Reports the DFSR replication backlog (files queued but not yet replicated)
# for every enabled replicated-folder / connection pairing, from the
# perspective of THIS server. Consumed by the dfs_backlog check plugin
# (service "DFS Backlog: <folder> <from|to> <partner>").
#
# WHY THIS SCRIPT IS HARDENED:
#   * Relaunches under native 64-bit PowerShell (sysnative) because the
#     32-bit Checkmk agent cannot see the 64-bit root\MicrosoftDFS provider.
#   * Isolates every pairing in its own try/catch so one unreachable partner
#     does not blank the whole section. A pairing that cannot be evaluated is
#     emitted as ";NULL", which the check treats as "DFSR Disabled" (OK)
#     rather than a false CRIT.
#   * Emits sep(59) with the exact descr shape the check parser expects:
#         <Folder> ( from <Partner>);<count>
#         <Folder> ( to <Partner>);<count>
#
# OUTPUT FORMAT NOTE (matches installed check dfs_backlog 1.4.0):
#   The check derives the share name from the FIRST space-delimited token of
#   the folder name. Folder names containing spaces (e.g. "SYSVOL Share") will
#   therefore display truncated in the service item. This is a limitation of
#   the check, not of this collector; left as-is to stay compatible.
#
# REMOTE WMI DEPENDENCY:
#   Backlog math needs the partner's version vector, which requires WMI/DCOM
#   access to the partner server. Under LocalSystem the machine account is
#   used. Test on ONE server first and confirm counts appear before rolling
#   out to all DFSR members.
#
# MANUAL PLACEMENT:
#   C:\ProgramData\checkmk\agent\plugins\dfs_backlog.ps1
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

$ErrorActionPreference = 'Stop'
$NS       = 'root\MicrosoftDFS'
$local    = $env:COMPUTERNAME
$dcomOpt  = New-CimSessionOption -Protocol Dcom

Write-Output "<<<dfs_backlog:sep(59)>>>"

# Cache of CIM sessions to partner servers so we open each at most once.
$sessions = @{}
function Get-PartnerSession {
    param([string]$Computer)
    if ($Computer -ieq $local -or $Computer -ieq 'localhost') { return $null }  # local = no session
    if (-not $sessions.ContainsKey($Computer)) {
        $sessions[$Computer] = New-CimSession -ComputerName $Computer -SessionOption $dcomOpt
    }
    return $sessions[$Computer]
}

function Get-FolderInfo {
    param($Session, [string]$GroupGuid, [string]$FolderName)
    $filter = "ReplicationGroupGUID='$GroupGuid' AND ReplicatedFolderName='$FolderName'"
    if ($null -eq $Session) {
        Get-CimInstance -Namespace $NS -ClassName 'DfsrReplicatedFolderInfo' -Filter $filter
    } else {
        Get-CimInstance -CimSession $Session -Namespace $NS -ClassName 'DfsrReplicatedFolderInfo' -Filter $filter
    }
}

# Compute outbound backlog of $SenderInfo relative to $ReceiverInfo's vector.
function Get-BacklogCount {
    param($SenderSession, $SenderInfo, $ReceiverInfo)
    $vv = (Invoke-CimMethod -InputObject $ReceiverInfo -MethodName 'GetVersionVector').VersionVector
    $res = Invoke-CimMethod -InputObject $SenderInfo -MethodName 'GetOutboundBacklogFileCount' `
        -Arguments @{ VersionVector = $vv }
    return [int]$res.BacklogFileCount
}

try {
    $groups      = Get-CimInstance -Namespace $NS -ClassName 'DfsrReplicationGroupConfig'
    $folders     = Get-CimInstance -Namespace $NS -ClassName 'DfsrReplicatedFolderConfig'
    $connections = Get-CimInstance -Namespace $NS -ClassName 'DfsrConnectionConfig'

    foreach ($grp in $groups) {
        $guid = $grp.ReplicationGroupGUID

        foreach ($fld in ($folders | Where-Object { $_.ReplicationGroupGUID -eq $guid -and $_.Enabled })) {
            $folderName = $fld.ReplicatedFolderName

            foreach ($con in ($connections | Where-Object { $_.ReplicationGroupGUID -eq $guid -and $_.Enabled })) {
                $partner = $con.PartnerName.Trim()

                try {
                    $localInfo    = Get-FolderInfo -Session $null -GroupGuid $guid -FolderName $folderName
                    $partnerSess  = Get-PartnerSession -Computer $partner
                    $partnerInfo  = Get-FolderInfo -Session $partnerSess -GroupGuid $guid -FolderName $folderName

                    if ($null -eq $localInfo -or $null -eq $partnerInfo) {
                        "{0} ( from {1});NULL" -f $folderName, $partner
                        "{0} ( to {1});NULL"   -f $folderName, $partner
                        continue
                    }

                    # Inbound  = files the partner still owes us (partner is sender).
                    $inbound  = Get-BacklogCount -SenderSession $partnerSess -SenderInfo $partnerInfo -ReceiverInfo $localInfo
                    # Outbound = files we still owe the partner (we are sender).
                    $outbound = Get-BacklogCount -SenderSession $null -SenderInfo $localInfo -ReceiverInfo $partnerInfo

                    "{0} ( from {1});{2}" -f $folderName, $partner, $inbound
                    "{0} ( to {1});{2}"   -f $folderName, $partner, $outbound
                }
                catch {
                    # Pairing could not be evaluated (partner unreachable, etc.).
                    # Emit NULL so the check reports OK/Disabled instead of failing.
                    "{0} ( from {1});NULL" -f $folderName, $partner
                    "{0} ( to {1});NULL"   -f $folderName, $partner
                }
            }
        }
    }
}
catch {
    $msg = ($_.Exception.Message -replace '[\r\n;]', ' ')
    "COLLECTOR_ERROR ( from {0});NULL" -f ($msg)
}
finally {
    foreach ($s in $sessions.Values) { if ($s) { Remove-CimSession $s -ErrorAction SilentlyContinue } }
}
