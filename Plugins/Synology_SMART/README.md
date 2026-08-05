# Synology SMART Attributes

Checkmk extension for monitoring per-disk SMART attributes on Synology NAS units through SNMP.

## Why this exists

DSM only populates the disk health field from version 7.1 onwards, so earlier releases show "Health: Not provided" with no per-disk data at all. The SMART attribute table is populated from DSM 6.2, making it the only reliable health source across a mixed fleet. State comes from DSM's own per-attribute verdict on raw values, so a disk is flagged on its first reallocated or pending sector rather than when a normalised score finally drops.

## What it monitors

- **SMART Disk n** or **SMART Drive n**: the status DSM reports for every SMART attribute on the disk, CRIT on any status other than OK. One exception: an attribute that failed at some point and has since recovered stays OK by default but is always named in the details. Pre-failure counters are checked against configurable levels, power-on time is reported informationally, and the full attribute table is written to the details.

One service per physical disk, named by drive bay including DX-series expansion enclosures, matched on the slot number in the device name since DSM doesn't list either table in bay order reliably; falls back to the device path if a match isn't certain. Attribute sets vary by vendor, so a counter is only evaluated when present. Temperature is intentionally skipped, since the built-in disk check covers it. No ruleset configuration required.

## Example services

Discovery on a unit with a DX517 expansion enclosure attached:

```
SMART Disk 1                      OK    All 23 attributes OK, Device: /dev/sda
SMART Disk 3                      OK    All 23 attributes OK, Device: /dev/sdc
SMART Disk 6                      OK    All 23 attributes OK, Device: /dev/sdf
SMART Disk 1 (DX517-1)            OK    All 23 attributes OK, Device: /dev/sdga
SMART Disk 5 (DX517-1)            OK    All 23 attributes OK, Device: /dev/sdge
SMART Disk 2                      WARN  Airflow_Temperature_Cel status: In_the_past
SMART Disk 12                     CRIT  Reallocated_Sector_Ct: 33 (warn/crit at 1/10)
```

A single service, showing the checked counters, power-on time, and the full attribute table in the details:

```
Summary   All 23 attributes OK, Device: /dev/sdga

Details   All 23 attributes OK
          Device: /dev/sdga
          Reallocated_Sector_Ct: 0
          Current_Pending_Sector: 0
          Offline_Uncorrectable: 0
          Reported_Uncorrect: 0
          UDMA_CRC_Error_Count: 0
          Powered on: 4 years 302 days
          Airflow_Temperature_Cel: raw 20 (current 80, worst 64, threshold 40, status OK)
          Command_Timeout: raw 0 (current 100, worst 100, threshold 0, status OK)
          Current_Pending_Sector: raw 0 (current 100, worst 100, threshold 0, status OK)
          End-to-End_Error: raw 0 (current 100, worst 100, threshold 99, status OK)
          G-Sense_Error_Rate: raw 0 (current 100, worst 100, threshold 0, status OK)
          Head_Flying_Hours: raw 6480 (current 100, worst 253, threshold 0, status OK)
          High_Fly_Writes: raw 0 (current 100, worst 100, threshold 0, status OK)
          Load_Cycle_Count: raw 99890 (current 51, worst 51, threshold 0, status OK)
          Offline_Uncorrectable: raw 0 (current 100, worst 100, threshold 0, status OK)
          Power-Off_Retract_Count: raw 48210 (current 76, worst 76, threshold 0, status OK)
          Power_Cycle_Count: raw 4 (current 100, worst 100, threshold 20, status OK)
          Power_On_Hours: raw 42300 (current 52, worst 52, threshold 0, status OK)
          Raw_Read_Error_Rate: raw 8889600 (current 69, worst 64, threshold 44, status OK)
          Reallocated_Sector_Ct: raw 0 (current 100, worst 100, threshold 10, status OK)
          Reported_Uncorrect: raw 0 (current 100, worst 100, threshold 0, status OK)
          Seek_Error_Rate: raw 15842500 (current 72, worst 60, threshold 45, status OK)
          Spin_Retry_Count: raw 0 (current 100, worst 100, threshold 97, status OK)
          Spin_Up_Time: raw 0 (current 94, worst 94, threshold 0, status OK)
          Start_Stop_Count: raw 51680 (current 50, worst 50, threshold 20, status OK)
          Temperature_Celsius: raw 20 (current 20, worst 40, threshold 0, status OK)
          Total_LBAs_Read: raw 1948000000 (current 100, worst 253, threshold 0, status OK)
          Total_LBAs_Written: raw 2776000000 (current 100, worst 253, threshold 0, status OK)
          UDMA_CRC_Error_Count: raw 0 (current 200, worst 200, threshold 0, status OK)
```

## Graphing

- **SMART disks**: reallocated, pending and offline uncorrectable sectors, reported uncorrectable errors, and UDMA CRC errors, all five on one combined graph.
- **SMART disks**: power-on time, on its own graph.

## Data source

`SYNOLOGY-SMART-MIB` disk SMART table at `.1.3.6.1.4.1.6574.5.1.1` for attribute names, raw values and per-attribute status, joined with the disk table at `.1.3.6.1.4.1.6574.2.1.1` to name each service by its physical drive bay.

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- Synology DSM 6.2 or later
- SNMP enabled on the NAS, v2c or v3
- No additional MIBs required on the Checkmk server

## Installation

1. Install the package via **Setup > Extension packages > Upload package**.
2. Run a service discovery on the host. Services appear based on what the device actually reports, so no manual disk selection is required.

## Configuration

- **Synology SMART attributes**: levels on the five pre-failure counters, per host and per drive, all defaulting to WARN at 1 and CRIT at 10, plus the state for an attribute that failed in the past, default OK. WARN at 1 is deliberately loud, since the first reallocated or pending sector is the earliest reliable failure signal. Raise the WARN floor on a disk carrying a fixed, non-growing value rather than suppressing the service. A historic failure defaults to OK because it is held in the drive and cannot be cleared, but it is always named in the service details, and the rule can raise it to WARN or CRIT to be notified of it instead.

No ruleset configuration is required. Every check ships with working defaults.

## Validated

DSM 6.2, 7.0, and 7.1 or later, on DS, RS and FS series units including DX-series expansion enclosures.

## Version history

- **1.1.0**: attributes reported as having failed in the past no longer affect the service state by default, but remain visible in the service details, with the state configurable in the ruleset. Corrected drive bay naming on units where DSM does not list disks in bay order, or has NVMe cache devices in the disk table, which changes service names on those hosts and requires a rediscovery
- **1.0.1**: author metadata update
- **1.0.0**: initial release, per-disk SMART health with bay-correlated service names, pre-failure counter levels with a dedicated ruleset, error counter and power-on time metrics

## Author

Sher Zaman, sher[at]sherz[dot]dev, [sherz.dev](https://sherz.dev), [LinkedIn](https://www.linkedin.com/in/sher-zaman-95b008114/)

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
