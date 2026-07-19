#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# synology_smart - Per-disk SMART attribute monitoring for Synology NAS
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# Monitors SMART attributes exposed by Synology DSM via SNMP
# (SYNOLOGY-SMART-MIB, .1.3.6.1.4.1.6574.5).
#
# - One service per physical disk, named by bay ("SMART Drive 1",
#   "SMART Drive 2 (DX517-1)") when the disk table and SMART table
#   agree on disk count; falls back to device path ("SMART /dev/sda")
#   otherwise.
# - CRIT if DSM reports any SMART attribute status other than OK.
# - Thresholds on the raw value of the pre-failure counters
#   Reallocated_Sector_Ct, Current_Pending_Sector, Offline_Uncorrectable,
#   Reported_Uncorrect and UDMA_CRC_Error_Count (default WARN >= 1,
#   CRIT >= 10). Counters are only evaluated when the drive reports
#   them; absence is never flagged.
# - Power_On_Hours reported informationally with metric.
# - Temperature intentionally not covered (handled by the built-in
#   Synology disk check).
#
# Validated against DSM 6.2 and DSM 7.0 on DS418, DS916+, DS918+,
# DS1517+ (incl. DX517 expansion) and RS4021xs+.
#
# 2026-07-15: v1.0.0 initial release
###############################################################################

from cmk.agent_based.v2 import (
    CheckPlugin,
    SNMPSection,
    SNMPTree,
    Service,
    Result,
    State,
    check_levels,
    render,
    all_of,
    exists,
    startswith,
)

# SMART attributes evaluated against thresholds (raw value).
# Maps SMART attribute name -> parameter key in the ruleset.
_LEVELED_ATTRIBUTES = {
    "Reallocated_Sector_Ct": "reallocated",
    "Current_Pending_Sector": "pending",
    "Offline_Uncorrectable": "offline_uncorrectable",
    "Reported_Uncorrect": "reported_uncorrect",
    "UDMA_CRC_Error_Count": "udma_crc",
}

_METRIC_NAMES = {
    "Reallocated_Sector_Ct": "synology_smart_reallocated",
    "Current_Pending_Sector": "synology_smart_pending",
    "Offline_Uncorrectable": "synology_smart_offline_uncorrectable",
    "Reported_Uncorrect": "synology_smart_reported_uncorrect",
    "UDMA_CRC_Error_Count": "synology_smart_udma_crc",
}


def parse_synology_smart(string_table):
    """Build {item: {"device": devname, "attributes": {name: {...}}}}.

    string_table[0]: SMART table rows [devname, attrname, current, worst,
                     threshold, raw, status]
    string_table[1]: disk table rows [bay name], index order = bay order
    """
    smart_rows, disk_rows = string_table

    # Group SMART rows per device, keeping first-appearance order.
    devices = {}
    for row in smart_rows:
        if len(row) < 7:
            continue
        devname, attrname, current, worst, threshold, raw, status = (
            c.strip() for c in row[:7]
        )
        if not devname or not attrname:
            continue
        dev = devices.setdefault(devname, {})
        dev[attrname] = {
            "current": current,
            "worst": worst,
            "threshold": threshold,
            "raw": raw,
            "status": status,
        }

    bay_names = [row[0].strip() for row in disk_rows if row and row[0].strip()]

    section = {}
    devnames = list(devices)
    if len(bay_names) == len(devnames) and len(set(bay_names)) == len(bay_names):
        # Positional correlation: SMART devices in first-appearance
        # order match disk table bays in index order.
        for devname, bay in zip(devnames, bay_names):
            section[bay] = {"device": devname, "attributes": devices[devname]}
    else:
        # Fallback: name services by device path.
        for devname in devnames:
            section[devname] = {"device": devname, "attributes": devices[devname]}
    return section


def discover_synology_smart(section):
    for item in section:
        yield Service(item=item)


def check_synology_smart(item, params, section):
    data = section.get(item)
    if not data:
        return

    attributes = data["attributes"]
    device = data["device"]

    # 1) DSM-reported per-attribute status
    failed = [
        (name, attr["status"])
        for name, attr in attributes.items()
        if attr["status"].upper() != "OK"
    ]
    if failed:
        for name, status in failed:
            yield Result(
                state=State.CRIT,
                summary=f"{name} status: {status}",
            )
    else:
        yield Result(
            state=State.OK,
            summary=f"All {len(attributes)} attributes OK",
        )

    yield Result(state=State.OK, summary=f"Device: {device}")

    # 2) Pre-failure counters against thresholds (only when present)
    for attrname, param_key in _LEVELED_ATTRIBUTES.items():
        attr = attributes.get(attrname)
        if attr is None:
            continue
        try:
            raw_value = int(attr["raw"])
        except ValueError:
            yield Result(
                state=State.UNKNOWN,
                summary=f"{attrname}: unparsable raw value {attr['raw']!r}",
            )
            continue
        yield from check_levels(
            raw_value,
            levels_upper=params.get(param_key),
            metric_name=_METRIC_NAMES[attrname],
            label=attrname,
            render_func=lambda v: str(int(v)),
            notice_only=True,
        )

    # 3) Power on hours, informational
    poh = attributes.get("Power_On_Hours")
    if poh is not None:
        try:
            poh_seconds = int(poh["raw"]) * 3600
        except ValueError:
            poh_seconds = None
        if poh_seconds is not None:
            yield from check_levels(
                poh_seconds,
                metric_name="synology_smart_power_on_hours",
                label="Powered on",
                render_func=render.timespan,
                notice_only=True,
            )

    # 4) Full attribute dump in the details
    details = "\n".join(
        f"{name}: raw {attr['raw']} (current {attr['current']}, "
        f"worst {attr['worst']}, threshold {attr['threshold']}, "
        f"status {attr['status']})"
        for name, attr in sorted(attributes.items())
    )
    if details:
        yield Result(state=State.OK, notice="SMART attributes", details=details)


snmp_section_synology_smart = SNMPSection(
    name="synology_smart",
    parse_function=parse_synology_smart,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Linux"),
        exists(".1.3.6.1.4.1.6574.1.5.1.0"),  # Synology ModelName
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.6574.5.1.1",  # diskSMARTInfoTable
            oids=[
                "2",  # diskSMARTInfoDevName
                "3",  # diskSMARTAttrName
                "5",  # diskSMARTAttrCurrent
                "6",  # diskSMARTAttrWorst
                "7",  # diskSMARTAttrThreshold
                "8",  # diskSMARTAttrRaw
                "9",  # diskSMARTAttrStatus
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.6574.2.1.1",  # diskTable
            oids=[
                "2",  # diskID (bay name, e.g. "Drive 1")
            ],
        ),
    ],
)

check_plugin_synology_smart = CheckPlugin(
    name="synology_smart",
    service_name="SMART %s",
    discovery_function=discover_synology_smart,
    check_function=check_synology_smart,
    check_default_parameters={
        "reallocated": ("fixed", (1, 10)),
        "pending": ("fixed", (1, 10)),
        "offline_uncorrectable": ("fixed", (1, 10)),
        "reported_uncorrect": ("fixed", (1, 10)),
        "udma_crc": ("fixed", (1, 10)),
    },
    check_ruleset_name="synology_smart",
)
