#!/usr/bin/env python3
"""Tenant wide rollups, update deferrals, Data Connector flows and inventory.

Author:  Sher Zaman (sher[at]sherz[dot]dev, https://sherz.dev)
Repo:    https://github.com/sher-zaman/Checkmk
License: GPL-2.0-only
"""

import json
import re
import time
from datetime import datetime

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    CheckPlugin,
    InventoryPlugin,
    Metric,
    Result,
    Service,
    State,
    check_levels,
    render,
)


MAX_LISTED = 250

# Same frozen label map used for the per server service items, so a service
# type reads identically whether you are looking at a server or at the tenant.
SERVICE_TYPE_LABELS = {
    "dns": "DNS",
    "dhcp": "DHCP",
    "ntp": "NTP",
    "dfp": "DNS Forwarding Proxy",
    "cdc": "Data Connector",
    "anycast": "Anycast",
    "authn": "Access Authentication",
    "msad": "MS AD Sync",
    "platform": "Platform Management",
    "appmgmt": "Application Management",
}


def type_label(service_type):
    key = str(service_type or "").strip().lower()
    return SERVICE_TYPE_LABELS.get(key, key.upper())


def group_by_type(services):
    groups = {}
    for svc in services or []:
        key = str(svc.get("service_type") or "").strip().lower()
        if not key:
            continue
        groups.setdefault(type_label(key), []).append(svc)
    return groups



def parse_json_section(string_table):
    if not string_table or not string_table[0]:
        return None
    try:
        return json.loads(string_table[0][0])
    except (ValueError, IndexError):
        return None


def to_epoch(value):
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.startswith("1970-01-01"):
        return None
    text = text.replace("Z", "+00:00")
    match = re.match(r"^(.*\.\d{1,6})\d*([+-]\d{2}:\d{2})$", text)
    if match:
        text = match.group(1) + match.group(2)
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Host rollup
# ---------------------------------------------------------------------------
def discover_hosts_summary(section):
    if section is not None and section.get("hosts") is not None:
        yield Service()


def check_hosts_summary(params, section):
    if section is None:
        return
    hosts = section.get("hosts") or []

    counts = {}
    for host in hosts:
        status = str(host.get("composite_status") or "unknown").strip().lower()
        counts[status] = counts.get(status, 0) + 1

    online = counts.get("online", 0)
    yield Result(state=State.OK, summary=f"{online} of {len(hosts)} servers online")
    yield Metric("infoblox_hosts_total", float(len(hosts)))
    yield Metric("infoblox_hosts_online", float(online))

    not_online = [
        f"{host.get('display_name') or 'unnamed'} ({host.get('composite_status')})"
        for host in hosts
        if str(host.get("composite_status") or "").strip().lower() != "online"
    ]
    if not_online:
        yield Result(
            state=State(params.get("not_online_state", 2)),
            summary=f"{len(not_online)} servers not online",
            details="\n".join(not_online),
        )

    versions = sorted({
        str(host.get("host_version")) for host in hosts if host.get("host_version")
    })
    if versions:
        yield Result(state=State.OK, notice="Versions: " + ", ".join(versions))

    # Full server list in the details. This is the tenant wide view, so it
    # includes servers for which no Checkmk host exists yet, which is the one
    # thing the per server checks cannot show.
    lines = []
    for host in sorted(hosts, key=lambda item: str(item.get("display_name") or "")):
        parts = [str(host.get("display_name") or "unnamed")]
        parts.append(str(host.get("composite_status") or "unknown status"))
        if host.get("host_version"):
            parts.append(str(host["host_version"]))
        if host.get("ophid"):
            parts.append(f"ophid {host['ophid']}")
        lines.append("  " + ", ".join(parts))
    if lines:
        yield Result(
            state=State.OK,
            notice="Servers:",
            details="Servers:\n" + "\n".join(lines[:MAX_LISTED]),
        )


agent_section_infoblox_csp_hosts_summary = AgentSection(
    name="infoblox_csp_hosts_summary",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_hosts_summary = CheckPlugin(
    name="infoblox_csp_hosts_summary",
    service_name="Infoblox Hosts",
    discovery_function=discover_hosts_summary,
    check_function=check_hosts_summary,
    check_default_parameters={"not_online_state": 2},
    check_ruleset_name="infoblox_csp_hosts_summary",
)


# ---------------------------------------------------------------------------
# Service rollup
# ---------------------------------------------------------------------------
# The tenant service list has no check plugin of its own. It is the data source
# for the per type availability checks and for the active DNS forwarding proxy
# check, both of which declare it explicitly.
agent_section_infoblox_csp_services_summary = AgentSection(
    name="infoblox_csp_services_summary",
    parse_function=parse_json_section,
)


# ---------------------------------------------------------------------------
# Service availability per service type
#
# Mirrors the Service Availability tile in the portal dashboard: one service
# per deployed service type, showing how many instances of it are online across
# the whole tenant. Complements the per server checks, which show one instance
# each and cannot express "DNS is fine on one node and down on the other".
# ---------------------------------------------------------------------------
def discover_service_availability(section):
    for item in group_by_type((section or {}).get("services")):
        yield Service(item=item)


def check_service_availability(item, params, section):
    groups = group_by_type((section or {}).get("services"))
    instances = groups.get(item)
    if instances is None:
        return

    online = [
        svc for svc in instances
        if str(svc.get("composite_status") or "").strip().lower() == "online"
    ]
    percent = 100.0 * len(online) / len(instances) if instances else 0.0

    unhealthy = [svc for svc in instances if svc not in online]
    state = (
        State.OK if not unhealthy
        else State(params.get("degraded_state", 2))
    )
    yield Result(
        state=state,
        summary=(
            f"{len(online)} of {len(instances)} online "
            f"({percent:.0f}%)"
        ),
    )
    yield Metric("infoblox_service_availability", percent, boundaries=(0.0, 100.0))
    yield Metric("infoblox_service_instances", float(len(instances)))

    lines = []
    for svc in sorted(instances, key=lambda entry: str(entry.get("name") or "")):
        parts = [str(svc.get("name") or "unnamed")]
        parts.append(
            f"{svc.get('composite_status') or 'unknown'}"
            f"/{svc.get('composite_state') or 'unknown'}"
        )
        if svc.get("current_version"):
            parts.append(str(svc["current_version"]))
        hosts_on = [name for name in (svc.get("hosts") or []) if name]
        if hosts_on:
            parts.append("on " + ", ".join(str(name) for name in hosts_on))
        lines.append("  " + ", ".join(parts))
    if lines:
        yield Result(
            state=State.OK,
            notice="Instances:",
            details="Instances:\n" + "\n".join(lines[:MAX_LISTED]),
        )

    if unhealthy:
        yield Result(
            state=State.OK,
            details="Not online:\n" + "\n".join(
                f"  {svc.get('name')}: {svc.get('composite_status')}"
                f"/{svc.get('composite_state')}"
                for svc in unhealthy
            ),
        )

    mismatched = []
    for svc in instances:
        desired = str(svc.get("desired_state") or "").strip().lower()
        actual = str(svc.get("composite_state") or "").strip().lower()
        if desired == "start" and actual not in ("started", "starting", ""):
            mismatched.append(f"{svc.get('name')}: wanted start, is {actual}")
        elif desired == "stop" and actual not in ("stopped", "stopping", ""):
            mismatched.append(f"{svc.get('name')}: wanted stop, is {actual}")
    if mismatched:
        yield Result(
            state=State(params.get("desired_state_mismatch", 1)),
            summary=f"{len(mismatched)} not in their desired state",
            details="\n".join(mismatched),
        )

    versions = sorted({
        str(svc.get("current_version")) for svc in instances
        if svc.get("current_version")
    })
    if len(versions) > 1:
        yield Result(
            state=State(params.get("version_mismatch_state", 0)),
            notice="Versions differ across instances: " + ", ".join(versions),
        )

    pending = [
        f"{svc.get('name')}: {svc.get('current_version')} to {svc.get('desired_version')}"
        for svc in instances
        if svc.get("desired_version")
        and svc.get("current_version")
        and str(svc["desired_version"]) != str(svc["current_version"])
    ]
    if pending:
        yield Result(
            state=State.OK,
            summary=f"{len(pending)} with a pending update",
            details="\n".join(pending),
        )


check_plugin_infoblox_csp_service_availability = CheckPlugin(
    name="infoblox_csp_service_availability",
    sections=["infoblox_csp_services_summary"],
    service_name="Infoblox Service Availability %s",
    discovery_function=discover_service_availability,
    check_function=check_service_availability,
    check_default_parameters={
        "degraded_state": 2,
        "desired_state_mismatch": 1,
        "version_mismatch_state": 0,
    },
    check_ruleset_name="infoblox_csp_service_availability",
)

# ---------------------------------------------------------------------------
# Software update deferrals
# ---------------------------------------------------------------------------
def discover_deferral(section):
    if section is not None and section.get("records") is not None:
        yield Service()


def check_deferral(section):
    if section is None:
        return
    windows = section.get("records") or []

    if not windows:
        yield Result(
            state=State.OK,
            summary="No maintenance windows configured, updates apply automatically",
        )
        yield Metric("infoblox_maintenance_windows", 0.0)
        return

    yield Result(state=State.OK, summary=f"{len(windows)} maintenance windows")
    yield Metric("infoblox_maintenance_windows", float(len(windows)))

    for window in windows[:20]:
        name = window.get("name") or window.get("id") or "unnamed"
        parts = [str(name)]
        for key in ("start_time", "end_time", "recurrence", "state"):
            value = window.get(key)
            if value:
                parts.append(f"{key.replace('_', ' ')}: {value}")
        yield Result(state=State.OK, notice=", ".join(parts))


agent_section_infoblox_csp_deferral = AgentSection(
    name="infoblox_csp_deferral",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_deferral = CheckPlugin(
    name="infoblox_csp_deferral",
    service_name="Infoblox Update Deferrals",
    discovery_function=discover_deferral,
    check_function=check_deferral,
)


# ---------------------------------------------------------------------------
# Inventory, on the piggyback host
# ---------------------------------------------------------------------------
HOST_TYPE_NAMES = {
    "1": "NIOS",
    "2": "NIOS HA",
    "3": "NIOS-X Virtual Server",
    "4": "NIOS-X Appliance",
    "5": "NIOS-X Container",
    "6": "cNIOS",
}


def inventory_infoblox_csp(section):
    if not section:
        return

    hardware = {
        "manufacturer": "Infoblox",
        "product": HOST_TYPE_NAMES.get(
            str(section.get("host_type")), section.get("host_type")
        ),
        "serial": section.get("serial_number"),
        "model": section.get("size"),
    }
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            key: value for key, value in hardware.items() if value not in (None, "")
        },
    )

    software = {
        "version": section.get("host_version"),
        "build": section.get("build_version"),
        "os_version": section.get("os_version"),
        "kernel_version": section.get("kernel_version"),
        "kubernetes_version": section.get("k8s_version"),
        "container_runtime": section.get("container_runtime_version"),
        "boot_mode": section.get("boot_mode"),
    }
    yield Attributes(
        path=["software", "applications", "infoblox", "niosx"],
        inventory_attributes={
            key: value for key, value in software.items() if value not in (None, "")
        },
    )

    platform = {
        "display_name": section.get("display_name"),
        "ophid": section.get("ophid"),
        "legacy_id": section.get("legacy_id"),
        "ip_address": section.get("ip_address"),
        "nat_ip": section.get("nat_ip"),
        "mac_address": section.get("mac_address"),
        "ip_space": section.get("ip_space"),
        "site_id": section.get("site_id"),
        "timezone": section.get("timezone"),
        "cloud_provider": section.get("cloud_provider"),
        "deployment_type": section.get("deployment_type"),
        "virtualization": section.get("virtualization"),
        "pool_name": section.get("pool_name"),
        "template_name": section.get("template_name"),
        "lock_type": section.get("lock_type"),
        "created_at": section.get("created_at"),
    }
    yield Attributes(
        path=["software", "applications", "infoblox", "csp"],
        inventory_attributes={
            key: value for key, value in platform.items() if value not in (None, "")
        },
    )


agent_section_infoblox_csp_inventory = AgentSection(
    name="infoblox_csp_inventory",
    parse_function=parse_json_section,
)

inventory_plugin_infoblox_csp = InventoryPlugin(
    name="infoblox_csp_inventory",
    inventory_function=inventory_infoblox_csp,
)
