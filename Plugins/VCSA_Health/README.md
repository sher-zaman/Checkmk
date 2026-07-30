# VMware vCenter Server Appliance (VCSA) Health Monitoring

Checkmk extension for monitoring the vCenter Server Appliance itself through its REST management API.

## Why this exists

Built-in vCenter monitoring covers the virtual infrastructure the appliance manages, not the appliance itself. This extension covers that gap.

## What it monitors

- **VCSA Service \<name\>**: state and health per vMon service. Automatic services not running or reporting degraded health are CRIT.
- **VCSA Health \<area\>**: appliance health colours mapped to states.
- **VCSA CPU utilization**: utilization and CPU steal, 80/90% and 5/10%.
- **VCSA Memory utilization**: utilization, used/total bytes, swap page rate, 80/90%.
- **VCSA Filesystem \<name\>**: per-filesystem usage, 80/90%. Archive excluded from levels by default.
- **VCSA Interface \<name\>**: link state, address mode, gateway, throughput, errors and drops. Link down is CRIT.
- **VCSA DNS Configuration**: name servers and appliance hostname. No servers is CRIT.
- **VCSA Time Synchronization**: mode, NTP reachability, measured clock drift. Drift 30/300 seconds.
- **VCSA Update**: status, version, and staleness of the last repository check, 14/30 days.
- **VCSA Root Password**: remaining validity, 14/7 days. Reported even if the account becomes unreadable.
- **VCSA Certificate**: machine TLS validity, 30/15 days, plus a hostname-to-certificate check.
- **VCSA Certificate \<name\>**: signing and trusted root certificates, 30/15 days.
- **VCSA Database Usage**: database usage by category with retention tiers, no default levels.
- **VCSA Access Settings**: SSH, DCUI, shell and console CLI state. OK by default.
- **VCSA Pending Shutdown**, **VCSA Proxy**, **VCSA Syslog Forwarding**, **VCSA VCHA Cluster**, **VCSA Replication**: each discovered only where configured.
- **Uptime**: via the built-in uptime check.

Where an endpoint fails, only that section is affected; the host-level services report the failure instead of disappearing. Every check ships with working defaults; no ruleset configuration is required.

## Example services

```
VCSA Service vpxd                 OK    Startup type: AUTOMATIC, State: STARTED, Health: HEALTHY
VCSA Health Storage               OK    Status: green
VCSA CPU utilization              OK    Utilization: 13.25%, Steal: 0.42%
VCSA Filesystem log               WARN  Used: 85.20% (warn/crit at 80.00%/90.00%)
VCSA Time Synchronization         OK    Mode: NTP, Clock drift: 0.35 s, All 2 NTP servers reachable
VCSA Root Password                OK    Root password expires in: 89 days 10 hours
```

## Graphing

CPU (utilization + steal), memory (utilization, and used vs total bytes), interfaces (throughput and packet rate as bidirectional graphs, errors/drops together), filesystems, database usage by category and by retention tier, clock drift, and perfometers on certificate validity, root password validity, backup age and update-check age. Services with no metrics: vMon services, health areas, access settings, proxy, pending shutdown, VCHA.

## Data source

One special agent, `agent_vcsa_health`, using the appliance REST API on port 443. Metrics are selected from the catalog the appliance advertises rather than fixed identifiers, since those differ between appliance versions.

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- VMware vCenter Server Appliance 7.x or 8.x

### Required permissions

The monitoring account must be a member of `SystemConfiguration.Administrators` (Administration > Single Sign On > Users and Groups > Groups). Plain read-only is not sufficient.

The certificate services additionally need a Certificate Management privilege the built-in Read-only role lacks: clone Read-only, add the "Administer" Certificate Management privilege, and assign it under Global Permissions with propagation to children. Optional: without it, only the certificate services are skipped.

## Installation

1. Install via **Setup > Extension packages > Upload package**.
2. Create a host with "Checkmk agent / API integrations" set to "Configured API integrations, no Checkmk agent".
3. Add a rule under **Setup > Agents > Other integrations > "VMware vCenter Server Appliance (VCSA) health"** with the username and password. The password is held in the password store and resolved inside the agent, so it never appears in the process table.
4. Run a service discovery.

## Conflicts and supersedes

This extension supersedes the legacy `vcsa7_health_status` package by Thomas Sielaff and Martin Hasin, which targets the pre-2.0 plugin APIs and is not compatible with Checkmk 2.3 and later.

## Configuration

Each check has a matching ruleset (Setup > Services > Service monitoring rules, under Virtualization): service and health-area state mapping, CPU/memory/steal/page-rate levels, filesystem levels with an archive opt-in, interface link and error/drop levels plus an expected address mode, drift and NTP-reachability states, update staleness, root password and certificate validity levels, backup age, database usage levels (none by default), access/proxy/syslog/shutdown state overrides, and HA/replication overrides. Uptime uses the built-in Uptime ruleset. No configuration is required; every check ships with working defaults.

## Tested against

Validated in multiple production Checkmk environments, covering vCenter Server Appliance 7.0 and 8.0.

## Version history

- **1.1.0**: adds access settings, proxy, syslog forwarding, pending shutdown, database usage, HA cluster and replication services; adds CPU steal, memory bytes, swap page rate, clock drift, interface address mode/gateway, and a certificate hostname check; filesystem percentages now taken from the appliance utilization metric with archive excluded by default; root password defaults changed to 14/7 days and reported even on account read failure; update staleness defaults changed to 14/30 days; credentials now resolved via the password store inside the agent
- **1.0.0**: initial release, vMon service states, appliance health areas, resource and filesystem usage, update status, backup status, certificates, root password expiry, time synchronization, network interfaces and DNS, with rulesets, graphing and checkman pages

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
