# check_dns_status.ps1

### 📂 Location: `Scripts/`
### 📎 Type: Checkmk Local Script

## 📝 Description
This script checks the status of the DNS Server service on a Windows host and outputs a result in Checkmk local check format.

## 📊 Thresholds
- **OK:** DNS Server service is running
- **CRITICAL:** DNS Server service is NOT running

## 🔢 Output Format (Checkmk Compatible)
The script outputs:
```
<<<local>>>
0 DNS_SERVER - OK - DNS Server is running
```
or
```
<<<local>>>
2 DNS_SERVER - CRITICAL - DNS Server is NOT running!
```

## 📁 Placement
Place this script in:
```
C:\ProgramData\checkmk\agent\local\
```

## ⚙️ Requirements
- PowerShell execution environment on the target host

## 📎 Notes
- The script uses `Get-Service` with error handling in case the service is not found.