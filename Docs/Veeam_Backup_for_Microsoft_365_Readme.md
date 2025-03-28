# Veeam_Backup_for_Microsoft_365.ps1
📂 **Location:** `Scripts/`
📎 **Type:** Checkmk Local Script

## 📝 Description
This script is designed for Checkmk monitoring of **Veeam Backup for Microsoft 365**. It retrieves details about the latest backup jobs and reports their status in a format compatible with Checkmk local checks.

## 📊 Monitoring Metrics
- **Latest Backup Job Status:** Reports job name, state, result, start time, end time, and type.
- **Health Status:**
  - ✅ **OK** → Job completed successfully
  - ⚠️ **WARN** → Job is still running beyond expected duration
  - ❌ **CRIT** → No recent backups found or job failed

## 🔢 Output Format (Checkmk Compatible)
The script outputs:
```
<<<local>>>
OK
VEEAM Job <Job Name>  State: <Running/Stopped>, Result: <Success/Failed>, Creation time: <Date>, End time: <Date>, Type: Backup
```
Example:
```
<<<local>>>
OK
VEEAM Job Sharepoint & OneDrive  State: Stopped, Result: Success, Creation time: 27.03.2025 20:00:00, End time: 27.03.2025 20:22:21, Type: Backup
```

## 📁 Placement
Place this script in:
```
C:\ProgramData\checkmk\agent\local\
```

---

## ⚙️ Requirements
- **Veeam PowerShell Module** (`Veeam.Archiver.PowerShell`)
- **Checkmk Agent installed on the Veeam backup server**
- **PowerShell Execution Policy** allowing script execution

---

## 🛠 Installation & Configuration Steps

### 1️⃣ Save the Script
1. Copy `Veeam_Backup_for_Microsoft_365.ps1` to:
   ```
   C:\ProgramData\checkmk\agent\local\
   ```
2. Ensure the script is saved **in UTF-8 without BOM** encoding.

### 2️⃣ Schedule Execution via Task Scheduler
Since Checkmk does not execute local scripts on a fixed interval, use Windows Task Scheduler to refresh the output every **15 minutes**.

#### Create a Task:
1. **Open Task Scheduler** (`taskschd.msc`)
2. **Create a New Task** (Right-click **Task Scheduler Library** → **Create Task**)
3. **General Tab:**
   - Name: `Checkmk_Veeam_365_Backup`
   - Run whether user is logged in or not
   - Run with highest privileges
   - Configure for: `Windows Server 2016`
4. **Triggers Tab:**
   - **New** → Begin the task: **On a schedule**
   - Repeat every: **15 minutes**
   - Enabled ✅
5. **Actions Tab:**
   - **New → Start a program**
   - Program/script: `powershell.exe`
   - Arguments:
     ```
     -ExecutionPolicy Bypass -File "C:\ProgramData\checkmk\agent\local\Veeam_Backup_for_Microsoft_365.ps1"
     ```
6. **Conditions & Settings:**
   - Uncheck "Stop the task if it runs longer than..."
   - Check "Allow task to be run on demand"

---

## ✅ Verification & Troubleshooting

### 1️⃣ Check Script Output
Manually run:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\ProgramData\checkmk\agent\local\Veeam_Backup_for_Microsoft_365.ps1"
```
Then, check output in:
```powershell
Get-Content "C:\ProgramData\checkmk\agent\spool\VeeamBackup365.txt"
```

### 2️⃣ Test Checkmk Agent Output
Run:
```powershell
C:\Program Files (x86)\checkmk\service\check_mk_agent.exe test | Select-String "VEEAM"
```

### 3️⃣ Check From Checkmk Server
On the Checkmk monitoring server, run:
```bash
cmk -d <hostname> | grep "VEEAM"
```
If the output includes backup details, Checkmk is reading the data correctly.

### 4️⃣ Troubleshooting
- **If data is missing in Checkmk UI:**
  - Ensure the script outputs `<<<local>>>` as the first line.
  - Run the script manually to confirm output format.
  - Restart the Checkmk Agent service:
    ```powershell
    Restart-Service check_mk_agent
    ```
  - Check Task Scheduler logs (`taskschd.msc` → **Task History**)

---

## 📎 Notes
- Uses **UTF-8 without BOM** to prevent encoding issues.
- Supports Veeam **Backup for Microsoft 365** only.
- The script runs every **15 minutes** via Task Scheduler for real-time monitoring.

---

## 📝 License
This project is licensed under the **MIT License**. See `LICENSE.md` for details.
