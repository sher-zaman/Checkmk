#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GPL-2.0-only
#
###############################################################################
# synology_smart - Per-disk SMART attribute monitoring for Synology NAS
###############################################################################
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
###############################################################################
#
# Monitors SMART attributes exposed by Synology DSM via SNMP
# (SYNOLOGY-SMART-MIB, .1.3.6.1.4.1.6574.5).
#
# - One service per physical disk, named by bay ("SMART Drive 1",
#   "SMART Drive 2 (DX517-1)"), matched on the slot number encoded in
#   the device name, since DSM lists neither the SMART table nor the
#   disk table in bay order reliably. Falls back to the device path
#   ("SMART /dev/sda") if the bays cannot be matched with certainty.
# - Attribute status as reported by DSM: any status other than OK is
#   CRIT, except In_the_past (the attribute fell below threshold at
#   some point in the drive's life but is fine now), which defaults
#   to OK and is configurable to WARN or CRIT.
#   The wording follows the upstream SMART WHEN_FAILED states, of which
#   there are three: a failure now, a failure that has since recovered,
#   and none. DSM reports OK for the last of those. Both the long and
#   short spellings of the first two are accepted, and any wording that
#   is not recognised is treated as a failure rather than assumed benign.
# - Thresholds on the raw value of the pre-failure counters
#   Reallocated_Sector_Ct, Current_Pending_Sector, Offline_Uncorrectable,
#   Reported_Uncorrect and UDMA_CRC_Error_Count (default WARN >= 1,
#   CRIT >= 10). Counters are only evaluated when the drive reports
#   them; absence is never flagged.
# - Power_On_Hours reported informationally with metric.
# - Temperature intentionally not covered (handled by the built-in
#   Synology disk check).
#
# Validated on DSM 6.2, 7.0 and 7.1 or later across DS, RS and FS
# series units, including DX-series expansion enclosures.
#
# 2026-08-04: 1.1.0 historic attribute failures (In_the_past) default to
#             OK instead of CRIT, state configurable via ruleset;
#             fixed bay naming on units where DSM lists disks out of bay
#             order, or has NVMe cache devices in the disk table
# 2026-07-28: 1.0.1 author metadata update
# 2026-07-15: 1.0.0 initial release
###############################################################################

import re

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


def _normalise_status(status):
    return status.strip().upper().replace(" ", "_").replace("-", "_")


# Values that mean "not failing". DSM reports OK, which is where smartctl
# prints a dash for an attribute that has never failed, has no threshold,
# or has no valid normalised value. The dash and empty strings are accepted
# too, in case a DSM build passes the upstream wording through unchanged.
_HEALTHY_STATUSES = frozenset({"", "OK", "_"})

# Wording for a failure that has since recovered. smartmontools prints
# In_the_past in full output and Past in brief output; DSM is known to use
# the full form. A failure happening now needs no set of its own, since it
# resolves to CRIT along with every other unrecognised value.
_HISTORIC_STATUSES = frozenset({"IN_THE_PAST", "PAST", "FAILED_PAST"})


def _is_healthy(status):
    return _normalise_status(status) in _HEALTHY_STATUSES


def _status_state(status, historic_state):
    """Map a DSM attribute status onto a monitoring state.

    A failure that has since recovered is history rather than a current
    fault, so its state is configurable. A failure happening now, and any
    wording that is not recognised, is CRIT: DSM does not document the set
    of values this field can take, so an unknown value is treated as a
    fault rather than assumed benign.
    """
    norm = _normalise_status(status)
    if norm in _HISTORIC_STATUSES:
        return historic_state
    return State.CRIT


def _device_sort_key(devname):
    """Natural sort key, so sata2 precedes sata10 and sda precedes sdfa.

    DSM does not always list disks in the SMART table in bay order, but
    device names are assigned by bay, so sorting on them restores it.
    """
    parts = re.split(r"(\d+)", devname)
    return [int(p) if p.isdigit() else p for p in parts]


def _parse_device(devname):
    """Map a device path to (enclosure key, slot number), or None.

    Synology encodes the physical slot in the device name: sata4 and sas4
    are slot 4, sdd is the fourth internal disk, and a two letter suffix
    such as sdfc is slot 3 of an expansion enclosure, where the first
    letter identifies which enclosure. NVMe devices are cache slots.
    """
    name = devname.rsplit("/", 1)[-1]
    match = re.fullmatch(r"(?:sata|sas|hd)(\d+)", name)
    if match:
        return ("internal", int(match.group(1)))
    match = re.fullmatch(r"nvme(\d+)n\d+", name)
    if match:
        return ("cache", int(match.group(1)) + 1)
    match = re.fullmatch(r"sd([a-z])", name)
    if match:
        return ("internal", ord(match.group(1)) - ord("a") + 1)
    match = re.fullmatch(r"sd([a-z])([a-z])", name)
    if match:
        return ("expansion:" + match.group(1), ord(match.group(2)) - ord("a") + 1)
    return None


def _parse_bay(bay_name):
    """Map a disk table entry to (enclosure key, slot number), or None.

    Handles "Disk 4", "Drive 4", "Drive 3 (DX517-1)" and "Cache device 1".
    The enclosure ordinal in brackets is kept, so a second expansion unit
    stays distinct from the first.
    """
    name = bay_name.strip()
    match = re.fullmatch(r"Cache device\s+(\d+)", name, re.IGNORECASE)
    if match:
        return ("cache", int(match.group(1)))
    match = re.fullmatch(r"(?:Disk|Drive)\s+(\d+)", name, re.IGNORECASE)
    if match:
        return ("internal", int(match.group(1)))
    match = re.fullmatch(r"(?:Disk|Drive)\s+(\d+)\s*\(\S+?-(\d+)\)", name, re.IGNORECASE)
    if match:
        return ("expansion", int(match.group(2)), int(match.group(1)))
    return None


def _pair_bays_with_devices(devnames, bay_names):
    """Map bay name -> device name, or None if it cannot be done safely.

    Matching is on the slot numbers encoded in both names rather than on
    table order, because DSM lists neither table in bay order reliably.
    Expansion enclosures are matched by ordinal: the lowest device letter
    group is the first enclosure. A pairing is only returned when every
    disk with SMART data maps to exactly one bay, so a wrong drive label
    is never invented.
    """
    devices = {}
    for devname in devnames:
        parsed = _parse_device(devname)
        if parsed is None:
            return None
        devices[parsed] = devname

    # Expansion enclosures are keyed by device letter, which varies with
    # how many internal disks precede them. Rank them to get ordinals.
    letters = sorted({key[0] for key in devices if key[0].startswith("expansion:")})
    ordinals = {letter: index for index, letter in enumerate(letters, start=1)}
    normalised = {}
    for (enclosure, slot), devname in devices.items():
        if enclosure.startswith("expansion:"):
            normalised[("expansion", ordinals[enclosure], slot)] = devname
        else:
            normalised[(enclosure, slot)] = devname

    pairs = {}
    for bay_name in bay_names:
        key = _parse_bay(bay_name)
        if key is None or key not in normalised:
            continue
        if bay_name in pairs:
            return None
        pairs[bay_name] = normalised[key]

    # Every disk reporting SMART data must have been claimed exactly once.
    if sorted(pairs.values()) != sorted(devnames):
        return None
    return pairs


def parse_synology_smart(string_table):
    """Build {item: {"device": devname, "attributes": {name: {...}}}}.

    string_table[0]: SMART table rows [devname, attrname, current, worst,
                     threshold, raw, status]
    string_table[1]: disk table rows [bay name]
    """
    smart_rows, disk_rows = string_table

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
    devnames = sorted(devices, key=_device_sort_key)

    pairs = _pair_bays_with_devices(devnames, bay_names)
    if pairs is None:
        # Fallback: name services by device path.
        return {d: {"device": d, "attributes": devices[d]} for d in devnames}
    return {
        bay: {"device": devname, "attributes": devices[devname]}
        for bay, devname in pairs.items()
    }


def discover_synology_smart(section):
    for item in section:
        yield Service(item=item)


def check_synology_smart(item, params, section):
    data = section.get(item)
    if not data:
        return

    attributes = data["attributes"]
    device = data["device"]

    # 1) Attribute status as reported by DSM. A historic failure is
    #    named here and always visible in the details, but only
    #    changes the service state if a rule asks for that.
    historic_state = State(params.get("historic_failure_state", State.OK.value))

    flagged = []
    for name, attr in sorted(attributes.items()):
        if _is_healthy(attr["status"]):
            continue
        flagged.append((name, attr["status"], _status_state(attr["status"], historic_state)))

    if not flagged:
        yield Result(
            state=State.OK,
            summary=f"All {len(attributes)} attributes OK",
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"{len(attributes) - len(flagged)} of {len(attributes)} attributes OK",
        )
        for name, status, state in flagged:
            yield Result(state=state, notice=f"{name} status: {status}")

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
        "historic_failure_state": 0,  # OK
        "reallocated": ("fixed", (1, 10)),
        "pending": ("fixed", (1, 10)),
        "offline_uncorrectable": ("fixed", (1, 10)),
        "reported_uncorrect": ("fixed", (1, 10)),
        "udma_crc": ("fixed", (1, 10)),
    },
    check_ruleset_name="synology_smart",
)
