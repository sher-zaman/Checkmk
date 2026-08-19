# VMware vCenter Server Appliance (VCSA) Health Monitoring

Checkmk extension for monitoring the vCenter Server Appliance itself through its REST management API.

## Why this exists

Built-in vCenter monitoring covers the virtual infrastructure the appliance manages, not the appliance itself. This extension covers that gap.

## What it monitors

- **Services & health**: vMon service state and health (CRIT on failure/degraded), appliance health areas (colour-mapped states)
- **Resources**: CPU utilization + steal, memory utilization + bytes + swap page rate (80/90%)
- **Storage**: per-filesystem usage, 80/90%, archive excluded by default
- **Network**: interface link/mode/gateway/throughput/errors/drops, DNS servers and hostname
- **Time**: sync mode, NTP reachability, measured clock drift (30/300s)
- **Update**: status, version, staleness of last repository check (14/30 days)
- **Security**: root password expiry (14/7 days), machine/signing/trusted-root certificates (30/15 days) with a hostname match check, access settings (SSH/DCUI/shell/CLI)
- **Optional, discovered only where configured**: proxy, syslog forwarding, pending shutdown, database usage, VCHA cluster, replication
- **Uptime**: via the built-in uptime check

Where an endpoint fails, only that section is affected; host-level services report the failure instead of disappearing. Every check ships with working defaults; no ruleset configuration is required.

## Example services

```
VCSA Service vpxd             OK    Startup type: AUTOMATIC, State: STARTED, Health: HEALTHY
VCSA Health Storage           OK    Status: green
VCSA CPU utilization          OK    Utilization: 13.25%, Steal: 0.42%
VCSA Memory utilization       OK    Utilization: 77.12%, 13.6 GiB of 17.6 GiB
VCSA Filesystem seat          OK    Used: 12.70%, 3.10 GiB of 24.4 GiB
VCSA Interface nic0           OK    Link: up, IPv4: 10.128.60.36, In: 12.7 kB/s, Out: 34.2 kB/s
VCSA DNS Configuration        OK    2 server(s): 10.128.60.21, 10.128.60.121
VCSA Time Synchronization     OK    Mode: NTP, Clock drift: 0.00 s, All 1 NTP servers reachable
VCSA Update                   OK    Update status: UP_TO_DATE, Version: 8.0.3.00900 build 25413364, Last update check: 10 days 2 hours ago
VCSA Root Password            OK    Root password expires in: 89 days 10 hours
VCSA Certificate              OK    Remaining validity: 295 days 20 hours
VCSA Certificate STS Signing  OK    Remaining validity: 6 years 315 days
VCSA Database Usage           OK    Stats 0.65%, Events 6.70%, Alarms <0.01%, Tasks 0.15%
VCSA Access Settings          OK    Enabled: Console CLI, DCUI, SSH
VCSA Pending Shutdown         OK    No shutdown or reboot pending
VCSA Syslog Forwarding        OK    1 target(s): 10.128.60.249:514 (UDP)
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

Each check has a matching ruleset (Setup > Services > Service monitoring rules, under Virtualization): service and health-area state mapping, CPU/memory/steal/page-rate levels, filesystem levels with an archive opt-in, interface link and error/drop levels plus an expected address mode, drift and NTP-reachability states, update severity states and staleness, root password and certificate validity levels, backup age, database usage levels (none by default), access/proxy/syslog/shutdown state overrides, and HA/replication overrides. Uptime uses the built-in Uptime ruleset. No configuration is required; every check ships with working defaults.

## Tested against

Validated in multiple production Checkmk environments, covering vCenter Server Appliance 7.0 and 8.0.

## Version history

- **1.1.2**: credential resolution now prefers the dedicated password store API on Checkmk 2.5 and later, falling back to the earlier module, so the credential is resolved inside the agent across the whole supported range; the update check now reports available updates from the appliance's pending update list rather than its cached status field, which could report the appliance as up to date while updates were available; available updates are reported with severity, type, release date and reboot requirement, with configurable states per severity, and the source consulted for the list is selectable in the datasource rule
- **1.1.1**: halves the number of monitoring API requests by reusing the query parameter style the appliance accepts; a failed DNS lookup now reports UNKNOWN instead of reporting the appliance as having no name servers; the database usage summary no longer repeats a category that breaches its levels, and its metrics now carry threshold lines
- **1.1.0**: adds access settings, proxy, syslog forwarding, pending shutdown, database usage, HA cluster and replication services; adds CPU steal, memory bytes, swap page rate, clock drift, interface address mode/gateway, and a certificate hostname check; filesystem percentages now taken from the appliance utilization metric with archive excluded by default; root password defaults changed to 14/7 days and reported even on account read failure; update staleness defaults changed to 14/30 days; credentials now resolved via the password store inside the agent
- **1.0.0**: initial release, vMon service states, appliance health areas, resource and filesystem usage, update status, backup status, certificates, root password expiry, time synchronization, network interfaces and DNS, with rulesets, graphing and checkman pages

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
