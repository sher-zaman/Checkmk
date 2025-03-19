# ✅ Checkmk Plugin - DHCP Failover Monitoring

This Checkmk plugin monitors **DHCP Failover status** on a Windows server and reports critical or warning conditions for each failover scope.

## 🔍 Features
- Checks all failover scopes on DHCP Server.
- Detects `CommunicationInterrupted` and other abnormal states.
- Reports using standard Checkmk local check format.

## 📂 Plugin Location

Place the plugin in:
```
C:\ProgramData\checkmk\agent\plugins\check_dhcp_failover.ps1
```

## 📈 Output Format
```
<<<local>>>
0 DHCP_FAILOVER - OK - All DHCP failover scopes are normal
1 DHCP_FAILOVER - WARNING - Failover Issues: ScopeID: CommunicationInterrupted
2 DHCP_FAILOVER - CRITICAL - Failover Issues: ScopeID: PartnerDown
3 DHCP_FAILOVER - UNKNOWN - No failover configuration found
```

## ⚙️ Service States

| Status     | Exit Code | Description                            |
|------------|-----------|----------------------------------------|
| OK         | 0         | All failover scopes are healthy        |
| WARNING    | 1         | At least one scope in warning state    |
| CRITICAL   | 2         | At least one scope in critical state   |
| UNKNOWN    | 3         | No failover data found or not configured |

## 💡 Notes
- Requires **DHCP Server PowerShell module**.
- Tested on Windows Server with failover configuration.
- Ensure script execution policy allows the script to run.

## 📜 License
MIT License

## 🙌 Contributions
Pull requests and improvements welcome.