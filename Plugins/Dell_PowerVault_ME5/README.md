# Dell PowerVault ME5 Storage

Checkmk extension for monitoring Dell PowerVault ME5 series storage systems through the controller HTTPS management API.

## Why this exists

Out-of-the-box coverage for the ME5 over SNMP stops at generic interface and system data, and the generic Redfish datasource does not surface much of the array's real health and capacity detail. This extension talks to the same management API that PowerVault Manager uses, so it exposes the full picture: system and controller health, capacity, disks, environmental sensors and connectivity, with real values rather than placeholders.

State for every object is taken from the array's own numeric health and status enums, not the display strings, so alerting is unaffected by locale or firmware wording changes.

## What it monitors

- **System health**, overall status plus management-controller redundancy and partner-MC state
- **Controllers**, per controller: health, operational status, fail-over, cache write policy and redundancy
- **Controller firmware**, per controller, informational
- **Host ports**, per port: health, link status, type and negotiated speed. Link status defaults to OK so uncabled ports do not false-alarm
- **Disk groups**, per group: fault tolerance, RAID level, member and spare counts, and background jobs (verify/scrub informational, reconstruct alertable)
- **Pools**, per pool, presented as a filesystem so the built-in Filesystem ruleset applies (levels, magic factor, trend; default 80/90%)
- **Volumes**, per volume: health, preferred-path ownership, RAID type, allocated size, optional thin-fill levels
- **Disks**, per drive: health, error and drive-down conditions, SMART status, plus SSD life, temperature and power-on hours where reported
- **Power supplies**, per PSU: health and status
- **Fans**, per fan: health, status and speed, discovered only when a live speed is reported
- **Temperature sensors**, per sensor, uses the built-in Temperature ruleset (default 60/70 C)
- **Sensors**, per non-temperature sensor: voltage, current and the capacitor/supercap pack, state driven
- **Unwritable cache**, per controller, raises on any non-zero value by default
- **Snapshots**, per source volume: count and snapshot data
- **Connected hosts**, per initiator, discovered while connected so a later disconnect is CRIT by default

## Data source

The special agent authenticates to the controller management IP and collects the standard ME5 `show` commands (system, controllers, disk-groups, pools, volumes, disks, power-supplies, sensor-status, unwritable-cache, versions, snapshots, initiators) as JSON, emitting one section per command.

## Requirements

- Dell PowerVault ME5 series array with the management API reachable from the Checkmk site
- A read-only (monitor) local account (SHA-256 login)
- Checkmk 2.3.0 or later

## Installation

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk, or place it in `local/` and run `mkp install`.
2. Create a host for the array.
3. Add a **Dell PowerVault ME5 storage** rule under **Setup > Agents > Other integrations**, pointing at the controller management IP with the monitor account (user and password).
4. Run a service discovery on the host.

The self-signed controller certificate is accepted by default; enable TLS verification in the rule once a trusted certificate is installed on the array.

## Configuration

Pool capacity uses the built-in Filesystem ruleset and temperature uses the built-in Temperature ruleset. Every other check has a dedicated ruleset, so all alert states and thresholds can be tuned per host or per item.

## Notes

Validated in production Checkmk environments.

## Version

**1.0.0**

## Author

Sher Zaman (sher_zaman[at]outlook[dot]com)

## License

GPL-2.0-only. See repository [LICENSE.md](../../LICENSE.md).
