# check_veeam_license_instance.ps1

### 📂 Location: `Scripts/`
### 📎 Type: Checkmk Local Script

## 📝 Description
This script is designed to be used with the Checkmk agent's `local` directory. It performs two monitoring checks related to Veeam Backup & Replication:
- License expiry countdown
- Instance usage percentage

## 📊 Thresholds
1. **License Expiry:**
   - OK: More than 30 days remaining
   - WARN: Less than 30 days
   - CRIT: Less than 5 days

2. **Instance Usage:**
   - OK: Up to 100%
   - WARN: Above 105%
   - CRIT: Above 110%

## 🔢 Output Format (Checkmk Compatible)
The script outputs:
```
0 Veeam_License_Expiry license_expiry_days=X
0 Veeam_Instance_Usage instance_usage_percent=Y
```

## 📁 Placement
Place this script in:
```
C:\ProgramData\checkmk\agent\local\
```

## ⚙️ Requirements
- Veeam PowerShell Module (`Veeam.Backup.PowerShell`)

## 📎 Notes
- This script assumes PowerShell execution policy allows running unsigned scripts.