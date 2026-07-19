# Synology SMART Attribute Monitoring (SNMP)

Checkmk extension for monitoring per-disk SMART attributes on Synology NAS units via SNMP.

## Why this exists

The built-in Synology disk check in Checkmk does not report SMART health on DSM versions below 7.1. This extension fills that gap by reading SMART data directly from the `SYNOLOGY-SMART-MIB`, giving visibility into disk health regardless of DSM version.

## What it monitors

One service is produced per physical disk, named by drive bay (including expansion units). Each service reports:

- DSM-reported SMART attribute failures (pass/fail from the NAS itself)
- Reallocated sector count
- Pending sector count
- Uncorrectable sector count
- UDMA CRC error count

Rising counts on the pre-failure attributes above are treated as early warning signs, even before DSM itself flags a failure.

## Requirements

- Synology DSM with SNMP enabled
- Checkmk 2.3.0 or later
- SNMP read access to the NAS from the Checkmk site

## Installation

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk, or place it in `local/` and run `mkp install`.
2. Run a service discovery on the Synology host.
3. One service per disk bay should appear.

## Configuration

An optional ruleset is available for per-service threshold adjustment on the pre-failure counters, so you can tune sensitivity per host or per disk model without editing the plugin.

## Version

**1.0.0**

## Author

Sher Zaman (FirmaTrust)

## License

See repository [LICENSE.md](../../LICENSE.md).
