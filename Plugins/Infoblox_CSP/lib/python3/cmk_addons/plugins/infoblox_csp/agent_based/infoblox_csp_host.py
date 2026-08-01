#!/usr/bin/env python3
"""Per NIOS-X server checks for the Infoblox CSP special agent.

These plugins consume piggyback sections, so each one runs against a Checkmk
host representing a single NIOS-X server.

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
    HostLabel,
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
    check_levels,
    render,
)

# ---------------------------------------------------------------------------
# Display labels for service types.
#
# These values become the Checkmk item, so they are frozen. Changing one is a
# breaking rename that orphans the service and drops its history. Every entry
# is taken from Infoblox's own wording in the portal rather than invented.
# Types absent from this map fall back to the raw value uppercased.
# ---------------------------------------------------------------------------
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

# Expansions shown in the details line only. Unlike the labels above these are
# free to change between versions, because they never form part of an item.
SERVICE_TYPE_HINTS = {
    "discovery": "possibly NIOS-X Discovery, not confirmed",
    "dgw": "expansion not confirmed",
    "orpheus": "Infoblox internal component",
}

HOST_STATUS_STATES = {
    "online": State.OK,
    "degraded": State.WARN,
    "pending": State.WARN,
    "awaiting_approval": State.WARN,
    "error": State.CRIT,
    "offline": State.CRIT,
}

SERVICE_STATUS_STATES = {
    "started": State.OK,
    "starting": State.WARN,
    "stopping": State.WARN,
    "stopped": State.CRIT,
    "error": State.CRIT,
}

CONFIG_STATUS_STATES = {
    "online": State.OK,
    "degraded": State.WARN,
    "error": State.CRIT,
    "offline": State.CRIT,
}

# Kea high availability state machine values. In hot standby mode both nodes
# report hot-standby during normal operation, so a passive node reporting it is
# healthy rather than a fault.
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

HOST_TYPE_NAMES = {
    "1": "NIOS",
    "2": "NIOS HA",
    "3": "NIOS-X Virtual Server",
    "4": "NIOS-X Appliance",
    "5": "NIOS-X Container",
    "6": "cNIOS",
}


def parse_json_section(string_table):
    """Sections carry one JSON document on a single line."""
    if not string_table or not string_table[0]:
        return None
    try:
        return json.loads(string_table[0][0])
    except (ValueError, IndexError):
        return None


def to_epoch(value):
    """Convert an RFC 3339 timestamp to epoch seconds.

    Returns None for anything unparseable and for the epoch zero sentinel that
    Infoblox uses to mean 'not applicable', which would otherwise compute as
    decades of staleness.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.startswith("1970-01-01"):
        return None
    text = text.replace("Z", "+00:00")
    # Python accepts at most six fractional digits.
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


def type_label(service_type):
    key = str(service_type or "").strip().lower()
    return SERVICE_TYPE_LABELS.get(key, key.upper())


def build_items(rows):
    """Map item name to row, keeping items stable and unique.

    Rows are grouped by service type. A type appearing once uses the plain
    label. A type appearing more than once disambiguates every member of that
    group with its service name, rather than numbering them, because the API
    does not return services in a stable order and an index would flip between
    polls.
    """
    groups = {}
    for row in rows or []:
        key = str(row.get("service_type") or "").strip().lower()
        if not key:
            continue
        groups.setdefault(key, []).append(row)

    items = {}
    for key, members in groups.items():
        members.sort(key=lambda row: str(row.get("service_id") or ""))
        label = SERVICE_TYPE_LABELS.get(key, key.upper())
        if len(members) == 1:
            items[label] = members[0]
            continue
        for member in members:
            suffix = member.get("service_name") or member.get("service_id") or "?"
            items[f"{label} {suffix}"] = member
    return items


def decode_message(message):
    """Render the nested JSON error payload as readable lines.

    status.message is a JSON encoded string holding a JSON array, so it needs
    decoding twice. A failure to decode must not break the check.
    """
    if not message:
        return []
    if not isinstance(message, str):
        return [str(message)]
    try:
        payload = json.loads(message)
    except ValueError:
        return [message.strip()]
    if not isinstance(payload, list):
        return [message.strip()]

    lines = []
    for entry in payload:
        if not isinstance(entry, dict):
            lines.append(str(entry))
            continue
        container = entry.get("containerName")
        errors = entry.get("errorMessages") or []
        code = entry.get("exitCode")
        text = ", ".join(str(item) for item in errors) if errors else "no message"
        parts = []
        if container:
            parts.append(f"container {container}")
        parts.append(text)
        if code not in (None, ""):
            parts.append(f"exit code {code}")
        lines.append(": ".join(parts))
    return lines or [message.strip()]


# ---------------------------------------------------------------------------
# Server status
# ---------------------------------------------------------------------------
def host_labels_infoblox_csp_host(section):
    """Emit host labels from the Infoblox provided host tags.

    A strict allowlist is applied in the agent. Tags are user writable, so
    labels are never generated from arbitrary keys.
    """
    if not section:
        return
    labels = section.get("labels") or {}
    for key in ("cloud_provider", "deployment_type", "virtualization", "host_subtype"):
        value = labels.get(key)
        if value:
            yield HostLabel(f"infoblox/{key}", str(value))
    for service_type in labels.get("services") or []:
        yield HostLabel(f"infoblox/service_{service_type}", "yes")


def discover_host(section):
    if section:
        yield Service()


def check_host(params, section):
    if not section:
        return

    state = resolve_state(
        section.get("composite_status"),
        HOST_STATUS_STATES,
        params.get("status_states"),
    )
    yield Result(
        state=state,
        summary=f"Status: {section.get('composite_status') or 'unknown'}",
    )

    version = section.get("host_version")
    host_type = HOST_TYPE_NAMES.get(str(section.get("host_type")), None)
    detail = []
    if version:
        detail.append(f"Version: {version}")
    if host_type:
        detail.append(f"Type: {host_type}")
    elif section.get("host_type"):
        detail.append(f"Type code: {section.get('host_type')}")
    if section.get("size"):
        detail.append(f"Size: {section['size']}")
    if section.get("ip_address"):
        detail.append(f"Address: {section['ip_address']}")
    if section.get("nat_ip"):
        detail.append(f"NAT address: {section['nat_ip']}")
    if detail:
        yield Result(state=State.OK, notice=", ".join(detail))

    if str(section.get("maintenance_mode") or "").lower() not in ("", "disabled"):
        yield Result(
            state=State.OK,
            summary=f"Maintenance mode: {section['maintenance_mode']}",
        )

    checked_in = to_epoch(section.get("updated_at"))
    if checked_in is not None:
        age = max(0.0, time.time() - checked_in)
        yield from check_levels(
            age,
            levels_upper=params.get("last_seen_levels"),
            metric_name="infoblox_last_checkin_age",
            label="Last check-in",
            render_func=render.timespan,
            notice_only=True,
        )

    count = section.get("service_count")
    if count is not None:
        yield Result(state=State.OK, notice=f"{count} services identified")

    skipped = [name for name in (section.get("skipped_services") or []) if name]
    if skipped:
        yield Result(
            state=State.WARN,
            summary=f"{len(skipped)} services skipped, no service type reported",
            details="Skipped: " + ", ".join(str(name) for name in skipped),
        )


agent_section_infoblox_csp_host = AgentSection(
    name="infoblox_csp_host",
    parse_function=parse_json_section,
    host_label_function=host_labels_infoblox_csp_host,
)

check_plugin_infoblox_csp_host = CheckPlugin(
    name="infoblox_csp_host",
    service_name="Infoblox Server Status",
    discovery_function=discover_host,
    check_function=check_host,
    check_default_parameters={
        "last_seen_levels": ("fixed", (1800.0, 3600.0)),
    },
    check_ruleset_name="infoblox_csp_host",
)


# ---------------------------------------------------------------------------
# Deployed services and platform managed services
# ---------------------------------------------------------------------------
def _discover_rows(section):
    if not section:
        return
    for item, row in build_items(section.get("rows")).items():
        labels = []
        if row.get("service_type"):
            labels.append(
                ServiceLabel("infoblox/service_type", str(row["service_type"]).lower())
            )
        yield Service(item=item, labels=labels)


def _check_rows(item, params, section, state_map, params_key):
    if not section:
        return
    row = build_items(section.get("rows")).get(item)
    if row is None:
        # Deliberately yields nothing. Checkmk then reports UNKNOWN with
        # "item not found", which is the signal that a service has been
        # removed. Yielding an OK result here would hide exactly that.
        return

    yield Result(
        state=resolve_state(row.get("status"), state_map, params.get(params_key)),
        summary=f"Status: {row.get('status') or 'unknown'}",
    )

    notices = []
    if row.get("current_version"):
        notices.append(f"Version: {row['current_version']}")
    if row.get("service_name"):
        notices.append(f"Service: {row['service_name']}")

    raw_type = str(row.get("service_type") or "").strip().lower()
    hint = SERVICE_TYPE_HINTS.get(raw_type)
    if raw_type not in SERVICE_TYPE_LABELS:
        notices.append(f"Type: {raw_type}" + (f" ({hint})" if hint else ""))

    if notices:
        yield Result(state=State.OK, notice=", ".join(notices))

    changed = to_epoch(row.get("status_updated_at"))
    if changed is not None:
        age = max(0.0, time.time() - changed)
        yield Result(
            state=State.OK,
            notice=f"In this state for {render.timespan(age)}",
        )
        yield Metric("infoblox_state_duration", age)

    upgraded = to_epoch(row.get("upgraded_at"))
    if upgraded is not None:
        yield Result(
            state=State.OK,
            notice=f"Last upgraded {render.datetime(upgraded)}",
        )

    for line in decode_message(row.get("message")):
        yield Result(state=State.OK, notice=line)


def check_service(item, params, section):
    yield from _check_rows(
        item, params, section, SERVICE_STATUS_STATES, "service_states"
    )


def check_config(item, params, section):
    yield from _check_rows(
        item, params, section, CONFIG_STATUS_STATES, "config_states"
    )


agent_section_infoblox_csp_service = AgentSection(
    name="infoblox_csp_service",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_service = CheckPlugin(
    name="infoblox_csp_service",
    service_name="Infoblox Service %s",
    discovery_function=_discover_rows,
    check_function=check_service,
    check_default_parameters={},
    check_ruleset_name="infoblox_csp_service",
)

agent_section_infoblox_csp_config = AgentSection(
    name="infoblox_csp_config",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_config = CheckPlugin(
    name="infoblox_csp_config",
    service_name="Infoblox %s",
    discovery_function=_discover_rows,
    check_function=check_config,
    check_default_parameters={},
    check_ruleset_name="infoblox_csp_config",
)


# ---------------------------------------------------------------------------
# Peak usage
# ---------------------------------------------------------------------------
USAGE_FIELDS = (
    ("dns_qps", "DNS queries", "infoblox_dns_qps_peak_24h", "/s"),
    ("dhcp_lps", "DHCP leases", "infoblox_dhcp_lps_peak_24h", "/s"),
    ("objects", "IPAM objects", "infoblox_objects_peak_24h", ""),
)


def discover_usage(section):
    if section and any(key in section for key, _, _, _ in USAGE_FIELDS):
        yield Service()


def check_usage(section):
    if not section:
        return

    for key, label, metric_name, suffix in USAGE_FIELDS:
        block = section.get(key)
        if not isinstance(block, dict):
            continue
        current = block.get("current")
        if current is None:
            continue
        try:
            value = float(current)
        except (TypeError, ValueError):
            continue

        text = f"{label}: {value:g}{suffix} in the last 24h"
        peak = block.get("peak")
        stamp = to_epoch(block.get("peak_timestamp"))
        if peak is not None:
            try:
                text += f", highest recorded {float(peak):g}{suffix}"
            except (TypeError, ValueError):
                pass
            if stamp is not None:
                text += f" on {render.date(stamp)}"

        yield Result(state=State.OK, summary=text)
        yield Metric(metric_name, value)

    if section.get("size"):
        yield Result(state=State.OK, notice=f"Size: {section['size']}")


agent_section_infoblox_csp_usage = AgentSection(
    name="infoblox_csp_usage",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_usage = CheckPlugin(
    name="infoblox_csp_usage",
    service_name="Infoblox Peak Usage",
    discovery_function=discover_usage,
    check_function=check_usage,
)


# ---------------------------------------------------------------------------
# DHCP high availability, from this host's point of view
# ---------------------------------------------------------------------------
def discover_ha_node(section):
    if section and section.get("role"):
        yield Service()


def check_ha_node(params, section):
    if not section:
        return

    overrides = params.get("node_states")
    role = section.get("role") or "unknown"
    yield Result(
        state=resolve_state(section.get("state"), HA_NODE_STATES, overrides),
        summary=f"Role: {role}, state: {section.get('state') or 'unknown'}",
    )

    notices = []
    if section.get("group_name"):
        notices.append(f"Group: {section['group_name']}")
    if section.get("mode"):
        notices.append(f"Mode: {section['mode']}")
    if section.get("address"):
        notices.append(f"Address: {section['address']}")
    if notices:
        yield Result(state=State.OK, notice=", ".join(notices))

    # state_v6 is an empty string when IPv6 is not configured, which must not
    # be treated as a failure.
    state_v6 = str(section.get("state_v6") or "").strip()
    if state_v6:
        yield Result(
            state=resolve_state(state_v6, HA_NODE_STATES, overrides),
            summary=f"IPv6 state: {state_v6}",
        )

    oldest = None
    peers = []
    for beat in section.get("heartbeats") or []:
        stamp = to_epoch(beat.get("successful_heartbeat"))
        peer = beat.get("peer") or "unknown peer"
        if stamp is None:
            continue
        age = max(0.0, time.time() - stamp)
        peers.append(f"{peer} {render.timespan(age)} ago")
        if oldest is None or age > oldest:
            oldest = age

    if oldest is None:
        yield Result(state=State.OK, notice="No heartbeat timestamp reported")
        return

    yield from check_levels(
        oldest,
        levels_upper=params.get("heartbeat_levels"),
        metric_name="infoblox_ha_heartbeat_age",
        label="Oldest peer heartbeat",
        render_func=render.timespan,
    )
    if peers:
        yield Result(state=State.OK, notice="Heartbeats: " + "; ".join(peers))


agent_section_infoblox_csp_ha_node = AgentSection(
    name="infoblox_csp_ha_node",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_ha_node = CheckPlugin(
    name="infoblox_csp_ha_node",
    service_name="Infoblox DHCP HA Node",
    discovery_function=discover_ha_node,
    check_function=check_ha_node,
    check_default_parameters={
        "heartbeat_levels": ("fixed", (300.0, 900.0)),
    },
    check_ruleset_name="infoblox_csp_ha_node",
)
