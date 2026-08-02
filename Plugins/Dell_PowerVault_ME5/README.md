# Dell PowerVault ME5 Storage

Checkmk extension for monitoring Dell PowerVault ME5 series storage systems through the controller HTTPS management API.

## Why this exists

SNMP on the ME5 exposes almost nothing storage-related, and the generic Redfish datasource returns incomplete or placeholder values with no capacity, performance or snapshot detail. This extension reads the same management API PowerVault Manager uses, so services report real values across the full array.

## What it monitors

- **System health** (one service): overall health, redundancy and partner-controller state
- **System performance** (one service): array-wide IOPS, throughput and response time (read/write split), controller CPU load
- **Health alerts** (one service): unresolved critical/warning alerts with component, reason and recommended action
- **Controllers** (per controller): health, status, fail-over, cache policy and redundancy
- **Controller firmware** (per controller): storage controller, management controller, expander and CPLD versions
- **Host ports** (per port): health, link status, speed, throughput, IOPS, response time and queue depth
- **Enclosures** (per enclosure): health, status, power draw and component counts
- **Disk groups** (per group): fault tolerance, RAID level, spares and background jobs
- **Pools** (per pool): capacity via the built-in Filesystem ruleset, with trend
- **Volumes** (per base volume): health, path ownership, capacity, throughput, IOPS and cache hit ratios
- **Disks** (per drive): health, SMART, SSD life, temperature, power-on hours, throughput, IOPS and predictive error counters
- **Power supplies** (per PSU): health and status
- **Fans** (per fan): health, status and speed
- **Temperature sensors** (per sensor): controller, I/O module, capacitor pack and power supply sensors
- **Supercapacitor** (per controller): charge, capacitance, resistance and cell voltages
- **Sensors** (per type): power-supply voltage and current sensors
- **Unwritable cache** (one service): per-controller unwritable cache percentage
- **Snapshots** (per source volume): snapshot count, data, newest age and the schedule that creates them
- **Schedules** (per schedule not tied to a volume): status, last run, next run and any error
- **Connected hosts** (per initiator): connectivity, alerts on disconnect

## Example services

A representative subset, out of roughly 70 services in total:

```
ME5 System Health                       OK    Health: OK, Redundancy: Redundant, Controller A: Operational, Controller B: Operational, Partner MC: Operational
ME5 System Performance                  OK    IOPS: 4200, Throughput: 512 kB/s, Avg response time: 312 microseconds
ME5 Health Alerts                       OK    No health alerts
ME5 Controller A                        OK    Health: OK, Status: Operational
ME5 Controller A Firmware               OK    Storage controller firmware: GTS270R008
ME5 Host Port A0                        OK    Health: OK, iSCSI Up, Throughput: 498 kB/s, IOPS: 39, Avg response time: 210 microseconds
ME5 Enclosure 0                         OK    Health: OK, Status: OK, Power: 245 W
ME5 Disk Group dgA01                    OK    Status: FTOL, RAID6, 12 disks
ME5 Pool A                              OK    Used: 61.20%, 18.4 TiB of 30.0 TiB, trend per 1 day 0 hours: +120 MiB, +0.01%
ME5 Volume vol01                        OK    Health: OK, size 2500.0GB, allocated 1200.0GB, Throughput: 340 kB/s, IOPS: 28
ME5 Disk 0.0                            OK    Health: OK, SAMSUNG MZILG1T9HCJRAD3, in virtual pool
ME5 Power Supply 0 Left                 OK    Health: OK, Status: Up
ME5 Fan 0                               OK    Health: OK, Status: Up, Speed: 4560 RPM
ME5 Temperature CPU Temperature-Ctlr A  OK    Temperature: 61.0 °C
ME5 Voltage Sensors                     OK    All 4 sensors OK
ME5 Supercapacitor Controller A         OK    All 8 sensors OK
ME5 Unwritable Cache                    OK    Unwritable cache: 0%
ME5 Snapshots vol01                     OK    2 snapshot(s), Newest snapshot age: 6 hours 40 minutes, Status: Ready, Last run: 2026-08-01 03:00, Next run: 2026-08-02 03:00
ME5 Connected Host esxi01               OK    Connected
```

## Graphing

- **System performance**: IOPS, throughput and response time (read/write split), plus controller CPU load.
- **Health alerts**: alert count.
- **Host ports**: throughput, IOPS, response time and queue depth.
- **Enclosures**: power, with a perfometer.
- **Pools**: capacity through the built-in Filesystem metrics.
- **Volumes and disks**: throughput, IOPS and cache hit ratios; disk predictive error counters on one combined graph.
- **Fan speed and SSD life remaining**: both with perfometers.
- **Supercapacitor**: capacitance, resistance and pack voltage, with charge on a perfometer.
- **Unwritable cache**: per controller.
- **Snapshots and schedules**: count, data, age and schedule timing.

Services with no metrics: system health, controllers, controller firmware, power supplies, connected hosts, and the voltage/current sensor services.

## Data source

The special agent authenticates to the controller management IP and collects the standard ME5 `show` commands as JSON: system, controllers, disk-groups, pools, volumes, disks, power-supplies, sensor-status, unwritable-cache, snapshots, initiators, alerts, enclosures, schedules, host-port-statistics, volume-statistics, disk-statistics and controller-statistics.

Where an object's health and its performance data come from two different commands, the agent joins them and emits a single section, so each check reads one section and discovery stays reliable.

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- Dell PowerVault ME5 series array with the management API reachable from the Checkmk site
- A read-only (monitor) local account

## Installation

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk.
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

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
