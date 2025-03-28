# Define the spool file path
$spoolFile = "C:\ProgramData\checkmk\agent\spool\VeeamBackup365.txt"

# Get the latest backup job session
$latestJob = Get-VBOJobSession | Sort-Object -Property EndTime -Descending | Select-Object -First 1

# Check if a job was found
if ($latestJob) {
    $jobName = $latestJob.JobName -replace '\s', '_'  # Replace spaces with underscores
    $creationTime = $latestJob.CreationTime
    $endTime = $latestJob.EndTime
    $status = $latestJob.Status
    $state = "Stopped"
    $jobType = "Backup"

    # Adjust state based on EndTime
    if ($endTime -eq $null -or $endTime -eq [datetime]"9999-12-31 18:59:59") {
        $endTime = "Still Running"
        $state = "Running"
    }

    # Determine CheckMK status (numeric values)
    if ($status -eq "Success" -or $status -eq "Running") {
        $checkmkStatus = 0  # ✅ OK
    } elseif ($status -match "Warning|In Progress") {
        $checkmkStatus = 1  # ⚠️ WARN
    } else {
        $checkmkStatus = 2  # ❌ CRITICAL
    }

    # Format output correctly for CheckMK
    $spoolData = @"
<<<local>>>
$checkmkStatus VEEAM_Job_$jobName - State: $state, Result: $status, Creation time: $(Get-Date $creationTime -Format "dd.MM.yyyy HH:mm:ss"), End time: $endTime, Type: $jobType
"@

    # Save without BOM
    [System.Text.Encoding]::UTF8.GetBytes($spoolData) | Set-Content -Path $spoolFile -Encoding Byte
}
else {
    # If no backup job is found, report an error
    $spoolData = @"
<<<local>>>
2 VEEAM_Job - No backup jobs found!
"@

    # Save without BOM
    [System.Text.Encoding]::UTF8.GetBytes($spoolData) | Set-Content -Path $spoolFile -Encoding Byte
}
