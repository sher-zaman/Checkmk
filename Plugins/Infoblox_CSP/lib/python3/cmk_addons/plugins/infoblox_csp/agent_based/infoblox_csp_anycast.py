#!/usr/bin/env python3
"""Anycast checks for the Infoblox CSP special agent.

Two views, mirroring the DHCP high availability pair. The tenant host gets one
service per anycast configuration; each NIOS-X server gets one service per
configuration it is a member of.

What this can and cannot tell you is worth being clear about. The portal reports
whether it believes a host is advertising a route. It does not prove the route
reached the upstream router, nor that clients can reach the anycast address.
Pairing these checks with an active DNS query against the anycast address is
what closes that loop.

Author:  Sher Zaman (sher[at]sherz[dot]dev, https://sherz.dev)
Repo:    https://github.com/sher-zaman/Checkmk
License: GPL-2.0-only
"""

import json

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
)

MAX_LISTED = 250

# Documented values for runtime_status on both a configuration and a member
# host. Anything else is reported as UNKNOWN rather than guessed at.
ANYCAST_STATES = {
    "active": State.OK,
    "degraded": State.WARN,
    "inactive": State.CRIT,
}


def parse_json_section(string_table):
    if not string_table or not string_table[0]:
        return None
    try:
        return json.loads(string_table[0][0])
    except (ValueError, IndexError):
        return None


def resolve_state(raw, overrides):
    key = str(raw or "").strip().lower()
    if overrides and key in overrides:
        return State(int(overrides[key]))
    return ANYCAST_STATES.get(key, State.UNKNOWN)


def routing_lines(member, indent="    "):
    """Render the routing configuration for one member host."""
    lines = []

    protocols = member.get("routing_protocols") or []
    if protocols:
        lines.append(f"{indent}protocols " + ", ".join(str(p) for p in protocols))

    bgp = member.get("config_bgp")
    if isinstance(bgp, dict) and bgp:
        parts = []
        asn = bgp.get("asn_text") or bgp.get("asn")
        if asn not in (None, "", 0):
            parts.append(f"local ASN {asn}")
        if bgp.get("keep_alive_secs"):
            parts.append(f"keepalive {bgp['keep_alive_secs']}s")
        if bgp.get("holddown_secs"):
            parts.append(f"holddown {bgp['holddown_secs']}s")
        if bgp.get("link_detect") is not None:
            parts.append(
                "link detect " + ("on" if bgp["link_detect"] else "off")
            )
        if parts:
            lines.append(f"{indent}BGP: " + ", ".join(parts))
        for neighbour in bgp.get("neighbors") or []:
            if not isinstance(neighbour, dict):
                continue
            detail = [f"{indent}  neighbour {neighbour.get('ip_address') or 'unknown'}"]
            peer_asn = neighbour.get("asn_text") or neighbour.get("asn")
            if peer_asn not in (None, "", 0):
                detail.append(f"ASN {peer_asn}")
            if neighbour.get("multihop"):
                hops = neighbour.get("max_hop_count")
                detail.append(
                    f"multihop, max {hops} hops" if hops else "multihop"
                )
            lines.append(", ".join(detail))

    for key, label in (("config_ospf", "OSPF"), ("config_ospfv3", "OSPFv3")):
        block = member.get(key)
        if not isinstance(block, dict) or not block:
            continue
        parts = []
        if block.get("area"):
            parts.append(f"area {block['area']}")
        if block.get("area_type"):
            parts.append(str(block["area_type"]))
        if block.get("interface"):
            parts.append(f"interface {block['interface']}")
        if block.get("cost") not in (None, 0):
            parts.append(f"cost {block['cost']}")
        if block.get("hello_interval"):
            parts.append(f"hello {block['hello_interval']}s")
        if block.get("dead_interval"):
            parts.append(f"dead {block['dead_interval']}s")
        if block.get("authentication_type"):
            parts.append(f"auth {block['authentication_type']}")
        if parts:
            lines.append(f"{indent}{label}: " + ", ".join(parts))

    return lines


# ---------------------------------------------------------------------------
# Tenant view, one service per anycast configuration
# ---------------------------------------------------------------------------
def _configs(section):
    return {
        str(config.get("name")): config
        for config in (section or {}).get("configs") or []
        if config.get("name")
    }


def discover_anycast(section):
    for name in _configs(section):
        yield Service(item=name)


def check_anycast(item, params, section):
    config = _configs(section).get(item)
    if config is None:
        return

    overrides = params.get("status_states")
    yield Result(
        state=resolve_state(config.get("runtime_status"), overrides),
        summary=f"Status: {config.get('runtime_status') or 'unknown'}",
    )

    members = config.get("onprem_hosts") or []
    active = [
        member for member in members
        if str(member.get("runtime_status") or "").strip().lower() == "active"
    ]

    # Anycast exists so that losing one advertiser is survivable, so the
    # operational question is how many advertisers remain rather than whether
    # the configuration is nominally healthy. This is counted here rather than
    # inferred from the reported status, which does not distinguish losing one
    # member from losing all but one.
    minimum = params.get("minimum_active")
    if members:
        if not active:
            state = State(params.get("no_active_state", 2))
        elif minimum is not None and len(active) < int(minimum):
            state = State(params.get("below_minimum_state", 2))
        elif len(active) < len(members):
            state = State(params.get("reduced_redundancy_state", 1))
        else:
            state = State.OK
        yield Result(
            state=state,
            summary=f"{len(active)} of {len(members)} hosts advertising",
        )
        yield Metric("infoblox_anycast_members", float(len(members)))
        yield Metric("infoblox_anycast_members_active", float(len(active)))

    if config.get("is_configured") is False:
        yield Result(
            state=State(params.get("unconfigured_state", 1)),
            summary="Configuration has not been applied to its hosts",
        )

    heading = []
    if config.get("service"):
        heading.append(f"Service: {config['service']}")
    if config.get("anycast_ip_address"):
        heading.append(f"Anycast address: {config['anycast_ip_address']}")
    if config.get("anycast_ipv6_address"):
        heading.append(f"Anycast IPv6: {config['anycast_ipv6_address']}")
    if heading:
        yield Result(state=State.OK, summary=", ".join(heading))

    notices = []
    if config.get("description"):
        notices.append(str(config["description"]))
    if config.get("id") is not None:
        notices.append(f"id {config['id']}")
    if config.get("updated_at"):
        notices.append(f"updated {config['updated_at']}")
    if notices:
        yield Result(state=State.OK, notice=", ".join(notices))

    lines = []
    for member in sorted(members, key=lambda entry: str(entry.get("name") or "")):
        header = [str(member.get("name") or "unnamed")]
        header.append(str(member.get("runtime_status") or "unknown status"))
        if member.get("ip_address"):
            header.append(str(member["ip_address"]))
        if member.get("ipv6_address"):
            header.append(str(member["ipv6_address"]))
        if member.get("ophid"):
            header.append(f"ophid {member['ophid']}")
        lines.append("  " + ", ".join(header))
        lines.extend(routing_lines(member))

    if lines:
        yield Result(
            state=State.OK,
            notice="Member hosts:",
            details="Member hosts:\n" + "\n".join(lines[:MAX_LISTED]),
        )

    if not active and members:
        yield Result(
            state=State.OK,
            details=(
                "No host is advertising this address. Clients cannot reach "
                f"{config.get('anycast_ip_address') or 'the anycast address'} "
                "through this configuration."
            ),
        )


agent_section_infoblox_csp_anycast = AgentSection(
    name="infoblox_csp_anycast",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_anycast = CheckPlugin(
    name="infoblox_csp_anycast",
    service_name="Infoblox Anycast %s",
    discovery_function=discover_anycast,
    check_function=check_anycast,
    check_default_parameters={
        "no_active_state": 2,
        "reduced_redundancy_state": 1,
        "below_minimum_state": 2,
        "unconfigured_state": 1,
    },
    check_ruleset_name="infoblox_csp_anycast",
)


# ---------------------------------------------------------------------------
# Per server view, one service per configuration the host belongs to
# ---------------------------------------------------------------------------
def _memberships(section):
    return {
        str(entry.get("config_name")): entry
        for entry in (section or {}).get("configs") or []
        if entry.get("config_name")
    }


def discover_anycast_node(section):
    for name in _memberships(section):
        yield Service(item=name)


def check_anycast_node(item, params, section):
    entry = _memberships(section).get(item)
    if entry is None:
        return

    overrides = params.get("status_states")
    yield Result(
        state=resolve_state(entry.get("runtime_status"), overrides),
        summary=(
            f"This host: {entry.get('runtime_status') or 'unknown'}"
        ),
    )

    config_status = entry.get("config_runtime_status")
    if config_status:
        yield Result(
            state=State(params.get("config_status_state", 0)),
            notice=f"Configuration overall: {config_status}",
        )

    heading = []
    if entry.get("service"):
        heading.append(f"Service: {entry['service']}")
    if entry.get("anycast_ip_address"):
        heading.append(f"Anycast address: {entry['anycast_ip_address']}")
    if entry.get("anycast_ipv6_address"):
        heading.append(f"Anycast IPv6: {entry['anycast_ipv6_address']}")
    if heading:
        yield Result(state=State.OK, summary=", ".join(heading))

    lines = routing_lines(entry, indent="  ")
    if lines:
        yield Result(
            state=State.OK,
            notice="Routing:",
            details="Routing:\n" + "\n".join(lines[:MAX_LISTED]),
        )


agent_section_infoblox_csp_anycast_node = AgentSection(
    name="infoblox_csp_anycast_node",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_anycast_node = CheckPlugin(
    name="infoblox_csp_anycast_node",
    service_name="Infoblox Anycast Node %s",
    discovery_function=discover_anycast_node,
    check_function=check_anycast_node,
    check_default_parameters={"config_status_state": 0},
    check_ruleset_name="infoblox_csp_anycast_node",
)
