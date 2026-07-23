# Dell PowerVault ME5 Storage

Checkmk extension for monitoring Dell PowerVault ME5 series storage systems through the controller HTTPS management API.

## Why this exists

Out-of-the-box coverage for the ME5 over SNMP stops at generic system and network data, and the generic Redfish datasource surfaces only a subset of the array's health, often with incomplete or placeholder values and no capacity, cache, snapshot or connectivity detail. This extension talks to the same management API that PowerVault Manager uses, so it exposes the full picture with real values.

State for every object is taken from the array's own numeric health and status values, not the display strings, so alerting is unaffected by locale or firmware wording changes. All alert states and thresholds are configurable, and the extension works on any ME5 array regardless of naming.

## What it monitors

- **System health**: overall status plus management-controller redundancy and partner-controller state
- **Controllers** (per controller): health, operational status, fail-over, cache write policy and redundancy
- **Controller firmware** (per controller): informational version reporting
- **Host ports** (per port, single service): health, link status, type and negotiated speed, plus I/O statistics: throughput, IOPS, average/read/write response time, queue depth, and data read/written since the last counter reset. A link status other than Up is Critical by default and can be relaxed per port for uncabled ports; throughput and IOPS are graphed for trending
- **Disk groups** (per group): fault tolerance, RAID level, member and spare counts, and background jobs (verify/scrub informational, reconstruct alertable)
- **Pools** (per pool): capacity presented as a filesystem, so the built-in Filesystem ruleset applies (levels, magic factor, trend; default 80/90%)
- **Volumes** (per base volume): health, preferred-path ownership, allocated size, and optional thin-provisioning fill levels
- **Disks** (per drive): health, error and drive-down conditions, SMART status, plus SSD life remaining, temperature and power-on hours where reported
- **Power supplies** (per PSU): health and status
- **Fans** (per fan): health, status and speed, discovered when a live speed is reported
- **Temperature sensors** (per sensor): uses the built-in Temperature ruleset (default 60/70 C)
- **Sensors** (one service per type): voltage, current and the capacitor/supercap pack (charge, capacitance, resistance) are each aggregated into a single service that reports every reading and raises if any one sensor is not OK
- **Unwritable cache**: per controller, raises on any non-zero value by default
- **Snapshots** (per source volume): snapshot count, data footprint, and the age of the newest snapshot, with optional freshness alerting to catch a stalled snapshot schedule
- **Connected hosts** (per initiator): discovered while connected, so a later disconnect alerts

## Data source

The special agent authenticates to the controller management IP and collects the standard ME5 `show` commands (system, controllers, disk-groups, pools, volumes, disks, power-supplies, sensor-status, host-port-statistics, unwritable-cache, versions, host-groups, initiators) as JSON, emitting one section per command. Snapshots are derived from the volume data, so no separate snapshot query is required.

## Requirements

- Dell PowerVault ME5 series array with the management API reachable from the Checkmk site
- A read-only (monitor) local account
- Checkmk 2.3.0 or later

## Installation

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk, or place it in the site and run `mkp install`.
2. Create a host for the array.
3. Add a **Dell PowerVault ME5 storage** rule under **Setup > Agents > Other integrations**, pointing at the controller management IP with the monitor account (user and password).
4. Run a service discovery on the host.

The self-signed controller certificate is accepted by default; enable TLS verification in the rule once a trusted certificate is installed on the array.

## Configuration

Pool capacity uses the built-in Filesystem ruleset and temperature uses the built-in Temperature ruleset. Every other check has a dedicated ruleset, so all alert states and thresholds can be tuned per host or per item. Notable defaults:

- **Host port link down**: Critical. Scope a rule to any intentionally uncabled ports and set the state to OK.
- **Sensors**: any sensor not OK raises Warning by default, adjustable per sensor type.
- **Snapshot freshness**: off by default. Enable "upper levels on newest snapshot age" (for example 26h warning, 50h critical) to alert when a daily snapshot schedule stalls.
- **Unwritable cache**: any non-zero percentage raises by default.

## Validated

Validated in production Checkmk environments.

## Version history

- **1.1.0**: adds host port I/O monitoring (throughput, IOPS, average/read/write response time and queue depth) integrated into the host port service, with optional levels in the host port ruleset.
- **1.0.0**: initial release. System, controller, firmware, host port, disk group, pool, volume, disk, power supply, fan, temperature, sensor, unwritable cache, snapshot and connected-host checks, with dedicated rulesets and built-in Filesystem and Temperature integration.

## Author

Sher Zaman

## License

GPLv2. See the repository [LICENSE.md](../../LICENSE.md).
