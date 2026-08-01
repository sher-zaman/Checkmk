#!/usr/bin/env python3
"""DHCP and IPAM checks for the Infoblox CSP special agent.

These run against the tenant host. DHCP ranges are served by the high
availability group rather than by an individual server, so they do not belong on
a piggyback host.

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
    CheckPlugin,
    DiscoveryResult,
    Metric,
    Result,
    RuleSetType,
    Service,
    State,
    check_levels,
    render,
)

HA_GROUP_STATES = {
    "ok": State.OK,
    "degraded": State.WARN,
    "error": State.CRIT,
    "down": State.CRIT,
}

HA_NODE_STATES = {
    "hot-standby": State.OK,
    "load-balancing": State.OK,
    "ready": State.OK,
    "backup": State.OK,
    "passive-backup": State.OK,
    "waiting": State.WARN,
    "syncing": State.WARN,
    "in-maintenance": State.WARN,
    "partner-in-maintenance": State.WARN,
    "communication-recovery": State.CRIT,
    "partner-down": State.CRIT,
    "terminated": State.CRIT,
}


def parse_json_section(string_table):
    if not string_table or not string_table[0]:
        return None
    try:
        return json.loads(string_table[0][0])
    except (ValueError, IndexError):
        return None


def to_epoch(value):
    """RFC 3339 to epoch. None for the epoch zero 'not applicable' sentinel."""
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


def resolve_state(raw, defaults, overrides):
    """Map an API status string to a Checkmk state.

    Ruleset override keys use underscores because form specification keys cannot
    contain hyphens or spaces, while the API returns values such as
    "hot-standby" and "awaiting approval". Both forms are accepted.
    """
    key = str(raw or "").strip().lower()
    norm = key.replace("-", "_").replace(" ", "_")
    if overrides and norm in overrides:
        return State(int(overrides[norm]))
    if key in defaults:
        return defaults[key]
    if norm in defaults:
        return defaults[norm]
    return State.UNKNOWN


def as_number(value):
    """Utilisation counts arrive as strings while percentages arrive as ints."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# High availability group
# ---------------------------------------------------------------------------
def discover_ha_group(section):
    for group in (section or {}).get("groups") or []:
        name = group.get("name")
        if name:
            yield Service(item=str(name))


def check_ha_group(item, params, section):
    groups = {
        str(group.get("name")): group
        for group in (section or {}).get("groups") or []
        if group.get("name")
    }
    group = groups.get(item)
    if group is None:
        return

    group_overrides = params.get("group_states")
    yield Result(
        state=resolve_state(group.get("status"), HA_GROUP_STATES, group_overrides),
        summary=f"Status: {group.get('status') or 'unknown'}",
    )

    if group.get("mode"):
        yield Result(state=State.OK, notice=f"Mode: {group['mode']}")

    # An empty status_v6 means IPv6 is not configured, not that it has failed.
    status_v6 = str(group.get("status_v6") or "").strip()
    if status_v6:
        yield Result(
            state=resolve_state(status_v6, HA_GROUP_STATES, group_overrides),
            summary=f"IPv6 status: {status_v6}",
        )

    node_overrides = params.get("node_states")
    oldest = None
    for member in group.get("hosts") or []:
        role = member.get("role") or "unknown"
        yield Result(
            state=resolve_state(member.get("state"), HA_NODE_STATES, node_overrides),
            notice=(
                f"{member.get('address') or 'unknown address'}: "
                f"{role}, {member.get('state') or 'unknown state'}"
            ),
        )
        for beat in member.get("heartbeats") or []:
            stamp = to_epoch(beat.get("successful_heartbeat"))
            if stamp is None:
                continue
            age = max(0.0, time.time() - stamp)
            if oldest is None or age > oldest:
                oldest = age

    if oldest is not None:
        yield from check_levels(
            oldest,
            levels_upper=params.get("heartbeat_levels"),
            metric_name="infoblox_ha_heartbeat_age",
            label="Oldest heartbeat",
            render_func=render.timespan,
            notice_only=True,
        )


agent_section_infoblox_csp_ha_group = AgentSection(
    name="infoblox_csp_ha_group",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_ha_group = CheckPlugin(
    name="infoblox_csp_ha_group",
    service_name="Infoblox DHCP HA Group %s",
    discovery_function=discover_ha_group,
    check_function=check_ha_group,
    check_default_parameters={
        "heartbeat_levels": ("fixed", (300.0, 900.0)),
    },
    check_ruleset_name="infoblox_csp_ha_group",
)


# ---------------------------------------------------------------------------
# Shared utilisation rendering for ranges, subnets and address blocks
# ---------------------------------------------------------------------------
def _yield_utilisation(entry, params, has_pool):
    utilisation = entry.get("utilization") or {}

    percent = as_number(utilisation.get("utilization"))
    total = as_number(utilisation.get("total"))
    used = as_number(utilisation.get("used"))
    free = as_number(utilisation.get("free"))

    # Objects with no DHCP pool are allocation records rather than pools. They
    # are saturated by design, so alarming on their utilisation would produce a
    # permanent alarm nobody can clear.
    levels_key = "levels_pool" if has_pool else "levels_static"
    levels = params.get(levels_key)

    if percent is not None:
        detail = ""
        if used is not None and total is not None:
            detail = f" ({used:.0f} of {total:.0f} used)"
        yield from check_levels(
            percent,
            levels_upper=levels,
            metric_name="infoblox_ip_utilization",
            label="Utilization",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
        )
        if detail:
            yield Result(state=State.OK, notice=f"Addresses{detail}")

    if free is not None:
        yield from check_levels(
            free,
            levels_lower=params.get("free_levels_lower"),
            metric_name="infoblox_ip_free",
            label="Free addresses",
            render_func=lambda value: f"{value:.0f}",
            notice_only=True,
        )
    if used is not None:
        yield Metric("infoblox_ip_used", used)
    if total is not None:
        yield Metric("infoblox_ip_total", total)

    for key, metric_name, label in (
        ("static", "infoblox_ip_static", "Static"),
        ("dynamic", "infoblox_ip_dynamic", "Dynamic"),
    ):
        value = as_number(utilisation.get(key))
        if value is not None:
            yield Metric(metric_name, value)
            yield Result(state=State.OK, notice=f"{label}: {value:.0f}")

    abandoned = as_number(utilisation.get("abandoned"))
    abandon_percent = as_number(utilisation.get("abandon_utilization"))
    if abandoned is not None:
        yield Metric("infoblox_ip_abandoned", abandoned)
    if abandon_percent is not None:
        yield from check_levels(
            abandon_percent,
            levels_upper=params.get("abandoned_levels"),
            metric_name="infoblox_abandon_utilization",
            label="Abandoned",
            render_func=render.percent,
            notice_only=True,
        )

    dhcp = entry.get("dhcp_utilization") or {}
    dhcp_percent = as_number(dhcp.get("dhcp_utilization"))
    dhcp_total = as_number(dhcp.get("dhcp_total"))
    if dhcp_percent is not None and dhcp_total:
        yield from check_levels(
            dhcp_percent,
            levels_upper=levels,
            metric_name="infoblox_dhcp_utilization",
            label="DHCP pool",
            render_func=render.percent,
            notice_only=True,
        )

    threshold = entry.get("threshold") or {}
    if threshold.get("enabled"):
        yield Result(
            state=State.OK,
            notice=(
                f"Infoblox thresholds: high {threshold.get('high')}%, "
                f"low {threshold.get('low')}%"
            ),
        )


# ---------------------------------------------------------------------------
# DHCP ranges
# ---------------------------------------------------------------------------
def range_item(entry):
    start = entry.get("start") or "?"
    end = entry.get("end") or "?"
    base = f"{start}-{end}"
    name = str(entry.get("name") or "").strip()
    return f"{base} ({name})" if name else base


def discover_range(section):
    for entry in (section or {}).get("ranges") or []:
        yield Service(item=range_item(entry))


def check_range(item, params, section):
    entries = {
        range_item(entry): entry
        for entry in (section or {}).get("ranges") or []
    }
    entry = entries.get(item)
    if entry is None:
        return

    if entry.get("disable_dhcp"):
        yield Result(state=State.WARN, summary="DHCP is disabled on this range")

    yield from _yield_utilisation(entry, params, has_pool=True)

    notices = []
    if entry.get("space_name"):
        notices.append(f"IP space: {entry['space_name']}")
    if entry.get("comment"):
        notices.append(str(entry["comment"]))
    exclusions = entry.get("exclusion_ranges") or []
    if exclusions:
        notices.append(f"{len(exclusions)} exclusion ranges")
    if notices:
        yield Result(state=State.OK, notice=", ".join(notices))


agent_section_infoblox_csp_range = AgentSection(
    name="infoblox_csp_range",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_range = CheckPlugin(
    name="infoblox_csp_range",
    service_name="Infoblox DHCP Range %s",
    discovery_function=discover_range,
    check_function=check_range,
    check_default_parameters={
        "levels_pool": ("fixed", (80.0, 90.0)),
        "levels_static": ("no_levels", None),
        "abandoned_levels": ("fixed", (10.0, 25.0)),
    },
    check_ruleset_name="infoblox_csp_ip_utilization",
)


# ---------------------------------------------------------------------------
# Subnets and address blocks, both discovered only when enabled
# ---------------------------------------------------------------------------
def network_item(entry):
    address = entry.get("address") or "?"
    cidr = entry.get("cidr")
    base = f"{address}/{cidr}" if cidr is not None else str(address)
    name = str(entry.get("name") or "").strip()
    return f"{base} ({name})" if name else base


def _discover_networks(params, section) -> DiscoveryResult:
    if not params.get("discover"):
        return
    minimum = params.get("minimum_addresses", 0) or 0
    for entry in (section or {}).get("objects") or []:
        total = as_number((entry.get("utilization") or {}).get("total"))
        if minimum and total is not None and total < minimum:
            continue
        yield Service(item=network_item(entry))


def _check_networks(item, params, section):
    payload = section or {}
    entries = {
        network_item(entry): entry
        for entry in payload.get("objects") or []
    }
    entry = entries.get(item)
    if entry is None:
        return

    pool_parents = set(payload.get("pool_parents") or [])
    has_pool = bool(entry.get("id")) and entry["id"] in pool_parents

    if not has_pool:
        yield Result(
            state=State.OK,
            notice="No DHCP range inside this object, treated as an allocation record",
        )

    yield from _yield_utilisation(entry, params, has_pool=has_pool)

    if entry.get("asm_scope_flag"):
        yield Result(
            state=State.WARN,
            summary="Infoblox predicts this scope may run out of addresses",
        )
    if entry.get("comment"):
        yield Result(state=State.OK, notice=str(entry["comment"]))


agent_section_infoblox_csp_subnet = AgentSection(
    name="infoblox_csp_subnet",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_subnet = CheckPlugin(
    name="infoblox_csp_subnet",
    service_name="Infoblox Subnet %s",
    discovery_function=_discover_networks,
    discovery_default_parameters={"discover": False, "minimum_addresses": 4},
    discovery_ruleset_name="infoblox_csp_network_discovery",
    discovery_ruleset_type=RuleSetType.MERGED,
    check_function=_check_networks,
    check_default_parameters={
        "levels_pool": ("fixed", (80.0, 90.0)),
        "levels_static": ("no_levels", None),
        "abandoned_levels": ("fixed", (10.0, 25.0)),
    },
    check_ruleset_name="infoblox_csp_ip_utilization",
)

agent_section_infoblox_csp_address_block = AgentSection(
    name="infoblox_csp_address_block",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_address_block = CheckPlugin(
    name="infoblox_csp_address_block",
    service_name="Infoblox Address Block %s",
    discovery_function=_discover_networks,
    discovery_default_parameters={"discover": False, "minimum_addresses": 4},
    discovery_ruleset_name="infoblox_csp_network_discovery",
    discovery_ruleset_type=RuleSetType.MERGED,
    check_function=_check_networks,
    check_default_parameters={
        "levels_pool": ("fixed", (80.0, 90.0)),
        "levels_static": ("no_levels", None),
        "abandoned_levels": ("fixed", (10.0, 25.0)),
    },
    check_ruleset_name="infoblox_csp_ip_utilization",
)


# ---------------------------------------------------------------------------
# IP space rollup
# ---------------------------------------------------------------------------
def discover_ip_space(section):
    for entry in (section or {}).get("spaces") or []:
        name = entry.get("name")
        if name:
            yield Service(item=str(name))


def check_ip_space(item, params, section):
    entries = {
        str(entry.get("name")): entry
        for entry in (section or {}).get("spaces") or []
        if entry.get("name")
    }
    entry = entries.get(item)
    if entry is None:
        return
    yield from _yield_utilisation(entry, params, has_pool=True)


agent_section_infoblox_csp_ip_space = AgentSection(
    name="infoblox_csp_ip_space",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_ip_space = CheckPlugin(
    name="infoblox_csp_ip_space",
    service_name="Infoblox IP Space %s",
    discovery_function=discover_ip_space,
    check_function=check_ip_space,
    check_default_parameters={
        "levels_pool": ("fixed", (80.0, 90.0)),
        "levels_static": ("no_levels", None),
        "abandoned_levels": ("fixed", (10.0, 25.0)),
    },
    check_ruleset_name="infoblox_csp_ip_utilization",
)


# ---------------------------------------------------------------------------
# Global DHCP configuration
# ---------------------------------------------------------------------------
def discover_dhcp_global(section):
    if (section or {}).get("records"):
        yield Service()


def check_dhcp_global(section):
    records = (section or {}).get("records") or []
    if not records:
        return
    config = records[0]

    yield Result(state=State.OK, summary="Global DHCP configuration present")

    ddns = config.get("ddns_enabled")
    if ddns is not None:
        yield Result(
            state=State.OK,
            notice=f"Dynamic DNS updates: {'enabled' if ddns else 'disabled'}",
        )

    threshold = config.get("dhcp_threshold") or {}
    if threshold:
        parts = [f"{key}: {value}" for key, value in sorted(threshold.items())]
        yield Result(state=State.OK, notice="Thresholds: " + ", ".join(parts))


agent_section_infoblox_csp_dhcp_global = AgentSection(
    name="infoblox_csp_dhcp_global",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_dhcp_global = CheckPlugin(
    name="infoblox_csp_dhcp_global",
    service_name="Infoblox DHCP Global Configuration",
    discovery_function=discover_dhcp_global,
    check_function=check_dhcp_global,
)
