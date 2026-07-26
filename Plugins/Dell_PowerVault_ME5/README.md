# Dell PowerVault ME5 Storage

Checkmk extension for monitoring Dell PowerVault ME5 series storage systems through the controller HTTPS management API.

## Why this exists

Out-of-the-box coverage for the ME5 over SNMP stops at generic system and network data, and the generic Redfish datasource surfaces only a subset of the array's health, often with incomplete or placeholder values and no capacity, performance, cache, snapshot or connectivity detail. This extension talks to the same management API that PowerVault Manager uses, so it exposes the full picture with real values.

State for every object is taken from the array's own numeric health and status values, not the display strings, so alerting is unaffected by locale or firmware wording changes. Temperature state follows the array's own per-sensor verdict, because the array knows the correct limit for each sensor. All alert states and thresholds are configurable, and the extension works on any ME5 array regardless of naming or enclosure count.

## What it monitors

- **System health**: overall status plus management-controller redundancy and partner-controller state
- **System performance**: array-wide IOPS, throughput and average response time, each split into read and write, plus controller CPU load and write cache utilisation
- **Health alerts**: unresolved critical and warning alerts, with the affected component, reason and the array's recommended action
- **Controllers** (per controller): health, operational status, fail-over, cache write policy and redundancy
- **Controller firmware** (per controller): storage controller, management controller, expander and CPLD versions
- **Host ports** (per port): health, link status, type and negotiated speed, plus throughput, IOPS, average/read/write response time, queue depth and data transferred. A link status other than Up is Critical by default and can be relaxed per port for uncabled ports
- **Enclosures** (per enclosure): health, status and power draw, with model, midplane, slot and component counts
- **Disk groups** (per group): fault tolerance, RAID level, member and spare counts, and background jobs (verify/scrub informational, reconstruct alertable)
- **Pools** (per pool): capacity presented as a filesystem, so the built-in Filesystem ruleset applies (levels, magic factor, trend; default 80/90%)
- **Volumes** (per base volume): health, preferred-path ownership, allocated size and thin fill, plus throughput, IOPS with read/write split, and current read and write cache hit ratios
- **Disks** (per drive): health, error and drive-down conditions, SMART status, SSD life remaining, temperature and power-on hours, plus throughput, IOPS, queue depth and the predictive error counters (SMART events, media errors, bad blocks, block reassignments, spin-up retries, I/O timeouts, no-response events) which raise when they increase
- **Power supplies** (per PSU): health and status
- **Fans** (per fan): health, status and speed
- **Temperature sensors** (per sensor): controller, I/O module, capacitor pack and power supply sensors, with the array's verdict driving state and the built-in Temperature ruleset available for custom levels
- **Supercapacitor** (per controller): the cache-protection pack's charge, capacitance, internal resistance, pack voltage and cell voltages, with capacitance and resistance graphed as wear indicators
- **Sensors** (per type): power-supply voltage and current sensors, each type aggregated into one service that names any sensor that is not OK
- **Unwritable cache**: per controller, raises on any non-zero value by default
- **Snapshot protection** (per source volume): snapshot count, data footprint and newest snapshot age, together with the schedule that creates them (status, last run, next run, errors and overdue detection), so one service shows whether a volume is protected and whether protection is still running. A volume with a schedule but no snapshots is reported explicitly
- **Schedules** (per schedule not tied to a volume): status, last run, next run and any error
- **Connected hosts** (per initiator): discovered while connected, so a later disconnect alerts

## Data source

The special agent authenticates to the controller management IP and collects the standard ME5 `show` commands as JSON: system, controllers, disk-groups, pools, volumes, disks, power-supplies, sensor-status, unwritable-cache, snapshots, initiators, alerts, enclosures, schedules, host-port-statistics, volume-statistics, disk-statistics and controller-statistics.

Where an object's health and its performance data come from two different commands, the agent joins them and emits a single section, so each check reads one section and discovery stays reliable.

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
- **Temperature**: state follows the array's own sensor verdict; no numeric levels are applied unless you configure them.
- **Disk predictive counters**: Warning when a counter increases between checks. Non-media errors are reported but not alerted, since low non-zero values are normal.
- **Snapshot freshness**: off by default. Enable "upper levels on newest snapshot age" (for example 26h warning, 50h critical) to alert when snapshots stop being taken.
- **Schedule overdue**: OK by default, so arrays with abandoned or unbound schedules stay quiet. Raise it to alert on a stalled active schedule.
- **Unwritable cache**: any non-zero percentage raises by default.
- **Performance levels**: all off by default. Throughput, IOPS, latency and cache hit ratios are graphed regardless.

## Validated

Validated in production Checkmk environments.

## Version history

- **1.2.0**: adds system performance, health alerts, enclosure and supercapacitor checks; snapshot schedules are reported inside each volume's snapshot service, with a separate service only for schedules not tied to a volume; adds volume and disk performance with cache hit ratios and predictive error counters; snapshots now use the array's snapshot objects for accurate timestamps; temperature state now follows the array's own sensor verdict instead of fixed default levels. Service naming improved for temperature sensors, fans, power supplies, connected hosts, controller firmware and system health, so upgrading rediscovers those services under their new names.
- **1.1.0**: adds host port I/O monitoring (throughput, IOPS, average/read/write response time and queue depth) integrated into the host port service, with optional levels in the host port ruleset.
- **1.0.0**: initial release. System, controller, firmware, host port, disk group, pool, volume, disk, power supply, fan, temperature, sensor, unwritable cache, snapshot and connected-host checks, with dedicated rulesets and built-in Filesystem and Temperature integration.

## Author

Sher Zaman

## License

GPLv2. See the repository [LICENSE.md](../../LICENSE.md).
