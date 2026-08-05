# Checkmk Extensions

Checkmk monitoring extensions and scripts, built and maintained by Sher Zaman.

Each extension is packaged as an MKP and ships with its unpacked source, so the code can be reviewed directly here before installing. All extensions target Checkmk 2.3.0 or later, up to 2.5.

## Extensions

| Extension | What it monitors | Type | Version |
|---|---|---|---|
| [Synology_SMART](Plugins/Synology_SMART) | Per-disk SMART attributes on Synology NAS units | SNMP | 1.1.0 |
| [FortiSwitch_Device_Health](Plugins/FortiSwitch_Device_Health) | CPU, memory, temperature, PSU, fan and SFP optics on Fortinet FortiSwitch | SNMP | 1.2.0 |
| [Dell_PowerVault_ME5](Plugins/Dell_PowerVault_ME5) | Dell PowerVault ME5 arrays: controllers, pools, volumes, disks, sensors, host port I/O | Special agent | 1.2.2 |
| [VCSA_Health](Plugins/VCSA_Health) | VMware vCenter Server Appliance services, health areas, filesystems, backup and certificate | Special agent | 1.1.1 |
| [DHCP_Failover](Plugins/DHCP_Failover) | Windows DHCP failover relationship state | Agent, bakery | 1.0.1 |
| [System_Reboot_Required](Plugins/System_Reboot_Required) | Pending reboot detection across major Linux distributions | Agent, bakery | 1.1.0 |
| [DFS_State](Plugins/DFS_State) | DFS Replication state per replicated folder | Agent, bakery | 2.1.1 |
| [DFS_Backlog](Plugins/DFS_Backlog) | DFS Replication backlog per folder, partner and direction | Agent, bakery | 1.5.1 |
| [Infoblox_CSP](Plugins/Infoblox_CSP) | Infoblox Cloud Services Portal: DNS, DHCP, IPAM, security policy and service health | Special agent | 1.6.0 |

Every extension folder contains its own README covering what it monitors, requirements, installation and configuration.

## Installation

Download the `.mkp` from the extension's folder, then either upload it under **Setup > Extension Packages** in Checkmk, or install it from the command line as the site user:

```
mkp add <package>.mkp
mkp enable <package>
```

Extensions marked "Agent, bakery" also need their agent plugin deployed to the monitored host, either manually or through the Agent Bakery. See the individual README for details.

## Repository layout

```
Plugins/<Extension>/
├── <package>-<version>.mkp      all published versions, kept
├── README.md
├── lib/                          check plugin, rulesets, graphing, checkman, bakery
└── agents/                       agent plugin, where applicable
```

The unpacked source mirrors the latest version. Earlier `.mkp` files are retained so any published version can be downloaded.

`Scripts/` holds standalone PowerShell local checks that predate the packaged extensions, with their documentation under `Scripts/Docs/`. These are being phased out in favour of MKPs.

## License

Original extensions are GPL-2.0-only. See [LICENSE.md](LICENSE.md).

Extensions forked from other authors' work retain the upstream licence and attribution, documented in their own README and, where the licence differs, in a `LICENSE.md` inside the extension folder.

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
