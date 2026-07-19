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

Each subfolder is a self-contained Checkmk extension or agent plugin. Extensions packaged as MKPs include the packaged `.mkp` file(s) plus the unpacked source under `lib/python3/cmk_addons/plugins/<name>/`, so the code can be browsed directly on GitHub. Each plugin folder has its own README with details on what it monitors and how to install it.

Current plugins:

- **Synology_SMART**: per-disk SMART attribute monitoring for Synology NAS units over SNMP
- **FortiSwitch_Device_Health**: CPU, memory, temperature, PSU, fan, and SFP optical monitoring for Fortinet FortiSwitch devices over SNMP
- **check_dhcp_failover**: legacy PowerShell agent plugin for DHCP failover monitoring (to be migrated to a packaged extension)

### Scripts/

Standalone PowerShell local checks, deployed to the Checkmk agent's `local/` directory. These run independently and produce their own check output. This folder is being phased out in favor of packaged extensions under `Plugins/`.

### Docs/

Documentation for the scripts in `Scripts/`, one file per script.

## License

GPL v2. See [LICENSE.md](LICENSE.md).
