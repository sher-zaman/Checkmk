# Checkmk

A personal collection of Checkmk monitoring plugins and scripts, built and maintained by Sher Zaman.

## Structure

```
Checkmk/
├── Plugins/     Checkmk extensions and agent plugins
├── Scripts/     Checkmk local checks (PowerShell, deployed to the agent's local/ directory)
└── Docs/        One README per script, matching the names in Scripts/
```

### Plugins/

Each subfolder is a self-contained Checkmk extension or agent plugin. Extensions packaged as MKPs include the packaged `.mkp` file(s) plus the unpacked source under `lib/python3/cmk_addons/plugins/<name>/` (and, where applicable, `agents/` and bakery trees), so the code can be browsed directly on GitHub. Each plugin folder has its own README with details on what it monitors and how to install it.

Current plugins:

- **Synology_SMART**: per-disk SMART attribute monitoring for Synology NAS units over SNMP
- **FortiSwitch_Device_Health**: CPU, memory, temperature, PSU, fan, and SFP optical monitoring for Fortinet FortiSwitch devices over SNMP
- **DHCP_Failover**: Windows DHCP failover relationship monitoring, agent-based with Agent Bakery support
- **System_Reboot_Required**: pending reboot detection for Linux hosts across major distributions. Maintenance fork of Luca-Leon Hausdoerfer's plugin, GPLv3
- **VCSA_Health**: VMware vCenter Server Appliance health monitoring via REST API, special agent, no Checkmk agent required

## Scripts/

Standalone PowerShell local checks, deployed to the Checkmk agent's `local/` directory. These run independently and produce their own check output. This folder is being phased out in favor of packaged extensions under `Plugins/`.

## Docs/

Documentation for the scripts in `Scripts/`, one file per script.

## License

GPL v2 for original FirmaTrust extensions. See [LICENSE.md](LICENSE.md).

Forked plugins carry their own license and attribution in their individual folders (see each plugin's README).
