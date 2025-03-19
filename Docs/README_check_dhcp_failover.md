# check_dhcp_failover.ps1

### 📂 Location: `Plugins/`
### 📎 Type: Checkmk Agent Plugin

## 📝 Description
This plugin script monitors the failover status of DHCP scopes on a Windows DHCP Server. It identifies normal, warning, and critical states for each scope.

## 📊 Thresholds
- **OK:** All scopes are in "Normal" state
- **WARNING:** Any scope is in "CommunicationInterrupted" state
- **CRITICAL:** Any scope is in other abnormal states (e.g., "PartnerDown")

## 🔢 Output Format (Checkmk Compatible)
The script outputs:
```
<<<local>>>
0 DHCP_FAILOVER - OK - All DHCP failover scopes are normal
```
or for issues:
```
<<<local>>>
1 DHCP_FAILOVER - WARNING - Failover Issues: <ScopeId>: CommunicationInterrupted
2 DHCP_FAILOVER - CRITICAL - Failover Issues: <ScopeId>: PartnerDown
```

## 📁 Placement
Place this script in:
```
C:\ProgramData\checkmk\agent\plugins\
```

## ⚙️ Requirements
- PowerShell environment on the target host
- DHCP PowerShell module available

## 📎 Notes
- The script is structured to exit with appropriate codes and provide detailed scope status in output.