# 📊 Checkmk Monitoring Scripts & Plugins

This repository contains PowerShell scripts and Checkmk plugins for advanced monitoring and automation tasks.

## 📁 Folder Structure

| Folder    | Description                                      |
|-----------|--------------------------------------------------|
| `Plugins/` | Contains all Checkmk agent plugins (go in `/plugins/`) |
| `Scripts/` | Contains all Checkmk local scripts (go in `/local/`)   |
| `Docs/`    | Documentation files for scripts and plugins      |
| `Tests/`   | Test scripts and helper tools for local testing  |
| `Configs/` | Configuration files and templates                |

## ⚙️ Components

### 🔌 Plugins (`/plugins/`)
- `check_dhcp_failover.ps1`: Checkmk Agent Plugin – DHCP Failover Monitoring

### 🖥️ Scripts (`/local/`)
- `check_dns_status.ps1`: Checkmk Local Script – DNS Server Monitoring
- `check_veeam_license_instance.ps1`: Checkmk Local Script – Veeam License & Instance Usage Monitoring

## 📝 License
This project is licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for more details.