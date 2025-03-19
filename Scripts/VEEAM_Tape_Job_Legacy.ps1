# Define exit codes
$OK = 0
$WARNING = 1
$CRITICAL = 2
$UNKNOWN = 3

# Get Veeam Tape Jobs
$jobs = Get-VBRTapeJob | Select-Object Name, LastResult, LastState, LastRun

if ($jobs.Count -eq 0) {
    Write-Output "$UNKNOWN Veeam_Tape_Job_Check - No jobs found!"
    exit 0
}

$output = @()

foreach ($job in $jobs) {
    $status = $job.LastResult
    $exitCode = $UNKNOWN  # Default unknown

    # Set exit codes
    if ($status -eq "Success") { $exitCode = $OK }
    elseif ($status -eq "Warning") { $exitCode = $WARNING }
    elseif ($status -eq "Failed") { $exitCode = $CRITICAL }

    # Clean job name for CheckMK
    $jobName = $job.Name -replace '[^a-zA-Z0-9]', '_'

    # Get Last Successful Run
    $lastSuccess = if ($status -eq "Success") { (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") } else { "N/A" }

    # Output with Last Successful Run Time
    $output += "$exitCode Veeam_Tape_Job_$jobName - Status: $status | LastSuccess: $lastSuccess"
}

# Print output for CheckMK
$output -join "`n"