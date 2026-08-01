#!/usr/bin/env python3
"""DNS checks for the Infoblox CSP special agent, on the tenant host.

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
    check_levels,
)


MAX_LISTED = 250


def parse_json_section(string_table):
    if not string_table or not string_table[0]:
        return None
    try:
        return json.loads(string_table[0][0])
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Authoritative zones, reported as one aggregate service
# ---------------------------------------------------------------------------
def discover_dns_zones(section):
    if section is not None and section.get("records") is not None:
        yield Service()


def check_dns_zones(params, section):
    if section is None:
        return
    zones = section.get("records") or []

    yield Result(state=State.OK, summary=f"{len(zones)} authoritative zones")
    yield Metric("infoblox_dns_zones", float(len(zones)))

    disabled = [
        zone.get("fqdn") or zone.get("protocol_fqdn") or "unnamed"
        for zone in zones
        if zone.get("disabled")
    ]
    warned = [
        (zone.get("fqdn") or "unnamed", zone.get("warnings") or [])
        for zone in zones
        if zone.get("warnings")
    ]

    if disabled:
        yield Result(
            state=State(params.get("disabled_state", 1)),
            summary=f"{len(disabled)} zones disabled",
            details="Disabled: " + ", ".join(str(name) for name in disabled),
        )
    yield Metric("infoblox_dns_zones_disabled", float(len(disabled)))

    if warned:
        lines = []
        for name, warnings in warned:
            texts = [
                str(item.get("message") if isinstance(item, dict) else item)
                for item in warnings
            ]
            lines.append(f"{name}: " + "; ".join(texts))
        yield Result(
            state=State(params.get("warning_state", 1)),
            summary=f"{len(warned)} zones reporting warnings",
            details="\n".join(lines),
        )
    yield Metric("infoblox_dns_zones_warning", float(len(warned)))

    signed = sum(
        1 for zone in zones
        if str(zone.get("dnssec_status") or "").strip().upper() not in ("", "UNSIGNED")
    )
    if zones:
        yield Result(
            state=State.OK,
            notice=f"DNSSEC signed: {signed} of {len(zones)}",
        )
    yield Metric("infoblox_dns_zones_signed", float(signed))

    # Full zone inventory in the details. Capped, because a large tenant can
    # hold thousands of zones and an unbounded details field is unusable.
    listed = sorted(
        zones,
        key=lambda zone: str(zone.get("fqdn") or zone.get("protocol_fqdn") or ""),
    )
    lines = []
    for zone in listed[:MAX_LISTED]:
        name = zone.get("fqdn") or zone.get("protocol_fqdn") or "unnamed"
        parts = [str(name)]
        primary = zone.get("primary_type")
        if primary:
            parts.append(str(primary))
        dnssec = str(zone.get("dnssec_status") or "").strip()
        parts.append(f"DNSSEC {dnssec}" if dnssec else "DNSSEC unknown")
        if zone.get("disabled"):
            parts.append("DISABLED")
        if zone.get("warnings"):
            parts.append("WARNING")
        view = zone.get("view_name") or zone.get("view")
        if view:
            parts.append(f"view {view}")
        lines.append("  " + ", ".join(parts))
    if len(listed) > MAX_LISTED:
        lines.append(f"  ... {len(listed) - MAX_LISTED} more not listed")
    if lines:
        yield Result(
            state=State.OK,
            notice="Zones:",
            details="Zones:\n" + "\n".join(lines),
        )


agent_section_infoblox_csp_dns_zones = AgentSection(
    name="infoblox_csp_dns_zones",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_dns_zones = CheckPlugin(
    name="infoblox_csp_dns_zones",
    service_name="Infoblox DNS Zones",
    discovery_function=discover_dns_zones,
    check_function=check_dns_zones,
    check_default_parameters={"disabled_state": 1, "warning_state": 1},
    check_ruleset_name="infoblox_csp_dns_zones",
)


# ---------------------------------------------------------------------------
# DNS views, used as configuration assertions
# ---------------------------------------------------------------------------
ASSERTIONS = (
    ("dnssec_enabled", "DNSSEC"),
    ("dnssec_enable_validation", "DNSSEC validation"),
    ("dnssec_validate_expiry", "DNSSEC expiry validation"),
)


def discover_dns_view(section):
    for entry in (section or {}).get("records") or []:
        name = entry.get("name")
        if name:
            yield Service(item=str(name))


def check_dns_view(item, params, section):
    entries = {
        str(entry.get("name")): entry
        for entry in (section or {}).get("records") or []
        if entry.get("name")
    }
    entry = entries.get(item)
    if entry is None:
        return

    expected = params.get("expect") or {}
    problems = 0

    for key, label in ASSERTIONS:
        actual = entry.get(key)
        if actual is None:
            continue
        text = "enabled" if actual else "disabled"
        want_raw = expected.get(key)
        # The ruleset offers "enabled" and "disabled" rather than booleans.
        want = None if want_raw is None else str(want_raw).strip().lower() == "enabled"
        if want is None or bool(actual) == want:
            yield Result(state=State.OK, notice=f"{label}: {text}")
            continue
        problems += 1
        yield Result(
            state=State(params.get("mismatch_state", 1)),
            summary=(
                f"{label} is {text}, expected "
                f"{'enabled' if want else 'disabled'}"
            ),
        )

    if not problems:
        yield Result(state=State.OK, summary="Configuration as expected")

    if entry.get("comment"):
        yield Result(state=State.OK, notice=str(entry["comment"]))


agent_section_infoblox_csp_dns_view = AgentSection(
    name="infoblox_csp_dns_view",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_dns_view = CheckPlugin(
    name="infoblox_csp_dns_view",
    service_name="Infoblox DNS View %s",
    discovery_function=discover_dns_view,
    check_function=check_dns_view,
    check_default_parameters={"mismatch_state": 1},
    check_ruleset_name="infoblox_csp_dns_view",
)


# ---------------------------------------------------------------------------
# Global DNS configuration
# ---------------------------------------------------------------------------
def discover_dns_global(section):
    if (section or {}).get("records"):
        yield Service()


def check_dns_global(section):
    records = (section or {}).get("records") or []
    if not records:
        return
    config = records[0]

    yield Result(state=State.OK, summary="Global DNS configuration present")

    for key, label in (
        ("dnssec_enable_validation", "DNSSEC validation"),
        ("dnssec_validate_expiry", "DNSSEC expiry validation"),
        ("recursion_enabled", "Recursion"),
        ("add_edns_option_in_outgoing_query", "EDNS in outgoing queries"),
    ):
        value = config.get(key)
        if value is None:
            continue
        yield Result(
            state=State.OK,
            notice=f"{label}: {'enabled' if value else 'disabled'}",
        )

    forwarders = config.get("forwarders") or []
    if forwarders:
        addresses = [
            str(entry.get("address") if isinstance(entry, dict) else entry)
            for entry in forwarders
        ]
        yield Result(
            state=State.OK,
            notice=f"Forwarders: {', '.join(addresses)}",
        )

    for key, metric_name, label in (
        ("lame_ttl", "infoblox_dns_lame_ttl", "Lame TTL"),
        ("max_cache_ttl", "infoblox_dns_max_cache_ttl", "Maximum cache TTL"),
        ("max_negative_ttl", "infoblox_dns_max_negative_ttl", "Maximum negative TTL"),
    ):
        value = config.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            yield from check_levels(
                float(value),
                metric_name=metric_name,
                label=label,
                render_func=lambda seconds: f"{seconds:.0f}s",
                notice_only=True,
            )


agent_section_infoblox_csp_dns_global = AgentSection(
    name="infoblox_csp_dns_global",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_dns_global = CheckPlugin(
    name="infoblox_csp_dns_global",
    service_name="Infoblox DNS Global Configuration",
    discovery_function=discover_dns_global,
    check_function=check_dns_global,
)
