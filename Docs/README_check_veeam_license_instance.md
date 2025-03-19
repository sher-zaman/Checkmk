# ✅ Checkmk Veeam Local Check Plugin

A lightweight and efficient PowerShell script for **Checkmk (Raw/Enterprise)** that monitors **Veeam Backup & Replication license expiry** and **instance usage**, reporting OK/WARN/CRIT states based on customizable thresholds.

## 🔍 Features
- 🎯 Monitors **Veeam license expiry (days remaining)**
- 📊 Tracks **Veeam instance usage (%)**
- 🟢 Compatible with **Checkmk local check format**
- ⚠️ Supports internal threshold logic (no need for WATO rules)
- 🚨 Graceful error handling — returns `UNKNOWN` if Veeam module or query fails

## 📂 File Structure

```
checkmk-veeam-local-checks/
├── check_veeam_license_instance.ps1
└── README.md
```

## ⚙️ Threshold Configuration

| Metric              | OK                    | Warning            | Critical            |
|---------------------|------------------------|---------------------|----------------------|
| License Expiry Days | > 30 days              | < 30 days           | < 5 days             |
| Instance Usage (%)  | ≤ 100% of licensed     | ≥ 105%              | ≥ 110%               |

## 🛠 Installation

1. Copy `check_veeam_license_instance.ps1` to your Checkmk agent’s local script directory:
   `C:\ProgramData\checkmk\agent\local\`

2. Ensure PowerShell execution is permitted:
   `Set-ExecutionPolicy RemoteSigned -Scope LocalMachine`

3. Unblock the script if needed via File Properties.

## 📈 Sample Output

```
OK - Veeam_License_Expiry license_expiry_days=45 License expires in 45 days
WARN - Veeam_License_Expiry license_expiry_days=12 License expires in 12 days (Thresholds: WARN < 30, CRIT < 5)
CRIT - Veeam_License_Expiry license_expiry_days=3 License expires in 3 days

OK - Veeam_Instance_Usage instance_usage_percent=97 Used 97 of 100 instances (97%)
WARN - Veeam_Instance_Usage instance_usage_percent=106.3 Used 106 of 100 instances (106.3%)
CRIT - Veeam_Instance_Usage instance_usage_percent=112.5 Used 113 of 100 instances (112.5%)
```

## 🚨 Error Handling
```
UNKNOWN - Error retrieving license information: <error>
UNKNOWN - Error retrieving instance usage information: <error>
```

## 📜 License
MIT License

## 🙌 Contributions
Pull requests and feedback are welcome.