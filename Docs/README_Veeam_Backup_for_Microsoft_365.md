# Veeam_Backup_for_Microsoft_365.ps1

### 📂 Location: `Scripts/`
### 📎 Type: Checkmk Local Script

## 📝 Description

This script is designed to monitor **Veeam Backup for Microsoft 365** jobs via **Checkmk**. It retrieves the latest backup job session and reports its status in a Checkmk-compatible format. The script ensures accurate monitoring of backup success, failures, and running states.

## 📊 Why Use Task Scheduler?

Instead of running this script dynamically during each **Checkmk agent** query, we utilize **Windows Task Scheduler** to execute it at predefined intervals. This approach significantly reduces the load on the Checkmk agent and improves system performance.  

### Key benefits:
✔️ Prevents **Checkmk agent execution delays** caused by script processing time  
✔️ Ensures that the **latest backup status** is always available without on-demand execution  
✔️ Reduces **system resource usage** by running the script only when needed  

## 📊 Thresholds

- **OK** ✅: Backup job completed successfully.
- **WARNING** ⚠️: Job is still running beyond expected duration.
- **CRITICAL** ❌: Backup job failed or no recent job found.

## 🔢 Output Format (Checkmk Compatible)

The script outputs:

```
<<<local>>>
0 VEEAM_Job_<JobName> State: Stopped, Result: Success, Creation time: <Timestamp>, End time: <Timestamp>, Type: Backup
```

Or if the job is still running:

```
<<<local>>>
1 VEEAM_Job_<JobName> State: Running, Result: In Progress, Creation time: <Timestamp>, End time: Still Running, Type: Backup
```

## 📁 Placement

Place this script in:

```
C:\Scripts\Veeam_Backup_for_Microsoft_365.ps1
```

## 🛠️ Task Scheduler Setup

### ✅ Steps to Automate Execution:
1. **Open Task Scheduler** (`taskschd.msc`).
2. **Create a new task**:
   - **General:** Set a meaningful name (e.g., `Checkmk_Veeam365_Backup`).
   - **Triggers:** Run every **15 minutes** (or adjust as needed).
   - **Actions:**  
     - Start a program: `powershell.exe`  
     - Arguments:  
       ```
       -ExecutionPolicy Bypass -File C:\Scripts\Veeam_Backup_for_Microsoft_365.ps1
       ```
   - **Conditions:** Ensure it runs **regardless of user login status**.
3. **Save & Enable** the task.
4. **Manually run** the task to verify output.

## 📚 Requirements

- **Veeam PowerShell Module** (`Veeam.Archiver.PowerShell` must be installed and accessible).
- **Checkmk Agent** must be installed and configured to read spool files.
- **Windows Task Scheduler** must be running and executing the script periodically.

## 📎 Notes

- The script writes output to:
  ```
  C:\ProgramData\checkmk\agent\spool\VeeamBackup365.txt
  ```
- Ensure **PowerShell execution policy** allows script execution:  
  ```
  Set-ExecutionPolicy Bypass -Scope LocalMachine
  ```
- If **Checkmk does not discover the service**, force an inventory update:  
  ```
  cmk -II <hostname>
  ```

## 💼 License

This project is licensed under the **MIT License**. See the `LICENSE.md` file for more details.
