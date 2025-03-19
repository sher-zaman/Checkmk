# ✅ Checkmk Local Script - DNS Server Status

A simple yet effective Checkmk local script that monitors the **status of the DNS Server service** on a Windows host.

## 🔍 Features
- 🔎 Checks the current status of the `DNS` Windows service.
- 🔔 Reports OK or CRITICAL based on service state.
- 🟢 Compatible with Checkmk local check output format.
- 🛡 Very lightweight with almost no performance overhead.

## 📂 Script Location

Place the script here:
```
C:\ProgramData\checkmk\agent\local\check_dns_status.ps1
```

## 📈 Output Format

The script returns a standard local check output:
```
0 DNS_SERVER - OK - DNS Server is running
2 DNS_SERVER - CRITICAL - DNS Server is NOT running!
```

## ⚙️ Service States

| Status     | Exit Code | Description                     |
|------------|-----------|----------------------------------|
| OK         | 0         | DNS service is running          |
| CRITICAL   | 2         | DNS service is not running      |

## 💡 Notes
- Ensure the script is executable (`Unblock-File` or adjust execution policy if needed).
- The script uses `Get-Service -Name "DNS"` — ensure the service is named `"DNS"` on your system.

## 📜 License
MIT License

## 🙌 Contributions
Pull requests are welcome. Suggestions and improvements encouraged.