# 📄 VEEAM_Tape_Job.ps1

## 🔍 Description
This PowerShell script is a Checkmk local check designed to monitor the status of Veeam Tape Jobs. It outputs job status along with the last successful run time in Checkmk-compatible format.

## 🖥️ Background & Purpose
This script was specifically developed for **Windows Server 2016**, as the built-in Veeam Tape Job monitoring feature in **Checkmk 2.3** does not function correctly on this OS version. The default Checkmk agent plugin only monitors **Backup** and **Replication Jobs**, and not **Tape Jobs**.

Although we attempted to extend the legacy plugin (located in the `/plugins` directory) to include Tape Job support, the Checkmk server was unable to correctly process Veeam Tape-specific data. As a result, a standalone local check was created to reliably handle this monitoring requirement.

## 📂 Script Location
Place the script in the following directory:
```
C:\ProgramData\checkmk\agent\local\
```

## 🛠️ What It Does
- Retrieves all Veeam Tape Jobs via PowerShell.
- Evaluates each job's `LastResult` (`Success`, `Warning`, `Failed`).
- Formats each job name for Checkmk compatibility.
- Outputs results using Checkmk local check format, including job status and last successful run time.

## ✅ Exit Code Mapping
| Exit Code | Status    |
|-----------|-----------|
| 0         | OK        |
| 1         | WARNING   |
| 2         | CRITICAL  |
| 3         | UNKNOWN   |

## 💡 Example Output
```
0 Veeam_Tape_Job_MonthlyBackup - Status: Success | LastSuccess: 2025-03-18 12:30:45
2 Veeam_Tape_Job_WeeklyArchive - Status: Failed | LastSuccess: N/A
```

## 📎 Notes
- This script requires the **Veeam PowerShell Module**.
- Ensure the script runs under a context with appropriate privileges to access Veeam job data.

## 🔖 Tags
Checkmk, PowerShell, Veeam, Tape Job Monitoring, Windows Server 2016, Local Check