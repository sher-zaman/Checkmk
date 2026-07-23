# VMware vCenter Server Appliance (VCSA) Health Monitoring

Checkmk extension that monitors the vCenter Server Appliance itself through its REST API, using a single version-independent special agent. Tested on VCSA 7.x and 8.x and designed for 9.x.

## Why this exists

Standard vCenter monitoring focuses on the virtual infrastructure (hosts, VMs, datastores), not on the health of the appliance running vCenter itself. This extension monitors the VCSA as a managed appliance: its services, health areas, resource usage, filesystems, backups, and certificates, so problems with vCenter's own platform are caught directly.

## What it monitors

One special agent produces the following services, discovered automatically:

- **Service state and health** per vMon service (vpxd, vsphere-ui, sps, vsan-health, and so on), including the appliance's own health messages. Services set to start automatically are CRIT when not running and WARN when running but not healthy.
- **Appliance health areas** (System, Database, Storage, Memory, Swap, Load, Software Packages, and others), mapping the appliance colours to states: green OK, yellow and orange WARN, red CRIT, gray UNKNOWN.
- **CPU, memory, and swap utilization** from the appliance monitoring API, with performance data, default levels 80/90%.
- **Per-filesystem usage** (root, seat, db, dblog, log, and others), with performance data, default levels 80/90%.
- **Update status** and installed product version, WARN when updates are pending, CRIT on a failed install or rollback.
- **File-based (VAMI) backup**, last job result and backup age, CRIT on a failed job, age levels 26h WARN / 50h CRIT.
- **Machine TLS certificate** remaining validity, 30d WARN / 15d CRIT.
- **Uptime**, via the built-in uptime check.

All thresholds are configurable via rulesets. The extension works out of the box with sensible defaults, no ruleset configuration is required.

The backup and certificate services are optional: if the account lacks the corresponding permissions, or file-based backup is not configured, those sections are skipped automatically and the remaining services keep working. Individual API endpoint failures are tolerated the same way, so a single deprecated or unavailable endpoint never takes down the rest of the checks.

## Requirements

- Checkmk 2.3 or later (tested up to 2.5)
- A VCSA account authorized for the appliance management API

### Required permissions

For services, health areas, resource and filesystem usage, update, and uptime, the monitoring account must be a member of the `SystemConfiguration.Administrators` group (Administration > Single Sign On > Users and Groups > Groups). A plain read-only group is not sufficient for the services and monitoring endpoints.

The certificate service is optional and needs an extra privilege the built-in Read-only role does not include. To enable it: in the vSphere Client, go to Administration > Access Control > Roles, clone the Read-only role, add the "Certificate Management" privilege (the Administer entry), and save it. Then assign that cloned role to the monitoring account under Global Permissions with Propagate to children. Rerun discovery and the VCSA Certificate service appears.

## Installation

1. Install the MKP via **Setup > Extension Packages**, or run `mkp install vcsa_health-1.0.0.mkp`.
2. Create a host for the appliance. No Checkmk agent is required: set "Checkmk agent / API integrations" to "Configured API integrations, no Checkmk agent".
3. Add a rule under **Setup > Agents > Other integrations > "VMware vCenter Server Appliance (VCSA) health"** with the username and password. The password is stored in the Checkmk password store and referenced by ID.
4. Run a service discovery on the host.

## Superseded package

This extension supersedes the legacy `vcsa7_health_status` package by Thomas Sielaff and Martin Hasin, which targets the pre-2.0 plugin APIs and is not compatible with Checkmk 2.3 and later.

## Notes

- Authentication uses the `/api/session` endpoint introduced with vCenter 7.0, and the session is closed after each run to avoid session exhaustion.
- Endpoint-level fault tolerance also covers appliance health endpoints that VMware has flagged as deprecated in recent releases, so the extension degrades cleanly on newer builds.

## Version

**1.0.0**

## Author

Sher Zaman (sher_zaman[at]outlook[dot]com)

## License

GPL-2.0-only. See repository [LICENSE.md](../../LICENSE.md).
