#!/usr/bin/env python3
"""Threat Defense checks for the Infoblox CSP special agent, on the tenant host.

These endpoints return configuration rather than health, so the checks are
assertions about how a tenant is set up rather than state monitoring. Health of
the DNS Forwarding Proxy itself comes from the per host service check.

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


def parse_json_section(string_table):
    if not string_table or not string_table[0]:
        return None
    try:
        return json.loads(string_table[0][0])
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Security policies
# ---------------------------------------------------------------------------
def discover_security_policy(section):
    for entry in (section or {}).get("records") or []:
        name = entry.get("name")
        if name:
            yield Service(item=str(name))


def check_security_policy(item, params, section):
    entries = {
        str(entry.get("name")): entry
        for entry in (section or {}).get("records") or []
        if entry.get("name")
    }
    policy = entries.get(item)
    if policy is None:
        return

    if policy.get("is_default"):
        yield Result(state=State.OK, summary="Default policy")
    else:
        yield Result(state=State.OK, summary="Policy present")

    rules = policy.get("rules") or []
    yield Result(state=State.OK, notice=f"{len(rules)} rules")
    yield Metric("infoblox_policy_rules", float(len(rules)))

    action = policy.get("default_action")
    if action:
        expected = params.get("expected_default_action")
        if expected and str(action) != str(expected):
            yield Result(
                state=State(params.get("mismatch_state", 1)),
                summary=f"Default action is {action}, expected {expected}",
            )
        else:
            yield Result(state=State.OK, notice=f"Default action: {action}")

    for key, label in (
        ("safe_search", "Safe search"),
        ("doh_enabled", "DNS over HTTPS"),
        ("block_dns_rebind_attack", "DNS rebind protection"),
        ("ecs", "EDNS client subnet"),
    ):
        value = policy.get(key)
        if value is None:
            continue
        yield Result(
            state=State.OK,
            notice=f"{label}: {'enabled' if value else 'disabled'}",
        )

    dfps = policy.get("dfps") or []
    if dfps:
        yield Result(state=State.OK, notice=f"{len(dfps)} DNS forwarding proxies bound")

    migration = policy.get("migration_status") or {}
    if migration.get("uses_legacy_feeds"):
        yield Result(
            state=State(params.get("legacy_feed_state", 1)),
            summary="Policy still references legacy threat feeds",
        )

    if policy.get("precedence") is not None:
        yield Result(state=State.OK, notice=f"Precedence: {policy['precedence']}")


agent_section_infoblox_csp_security_policy = AgentSection(
    name="infoblox_csp_security_policy",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_security_policy = CheckPlugin(
    name="infoblox_csp_security_policy",
    service_name="Infoblox Security Policy %s",
    discovery_function=discover_security_policy,
    check_function=check_security_policy,
    check_default_parameters={"mismatch_state": 1, "legacy_feed_state": 1},
    check_ruleset_name="infoblox_csp_security_policy",
)


# ---------------------------------------------------------------------------
# DNS Forwarding Proxy configuration
# ---------------------------------------------------------------------------
# The proxy configuration list has no check plugin of its own. It is the data
# source for the active proxy check, which declares it explicitly and reports
# every proxy in one service.
agent_section_infoblox_csp_dfp_service = AgentSection(
    name="infoblox_csp_dfp_service",
    parse_function=parse_json_section,
)


# ---------------------------------------------------------------------------
# Threat feeds, reported as one aggregate service
# ---------------------------------------------------------------------------
def discover_threat_feeds(section):
    if section is not None and section.get("records") is not None:
        yield Service()


def check_threat_feeds(params, section):
    if section is None:
        return
    feeds = section.get("records") or []

    yield Result(state=State.OK, summary=f"{len(feeds)} threat feeds subscribed")
    yield Metric("infoblox_threat_feeds", float(len(feeds)))

    legacy = [
        str(feed.get("name") or feed.get("key") or "unnamed")
        for feed in feeds
        if feed.get("legacy")
    ]
    if legacy:
        yield Result(
            state=State(params.get("legacy_state", 0)),
            summary=f"{len(legacy)} legacy feeds",
            details="Legacy feeds: " + ", ".join(legacy),
        )
    yield Metric("infoblox_threat_feeds_legacy", float(len(legacy)))

    levels = {}
    for feed in feeds:
        level = str(feed.get("threat_level") or "unspecified")
        levels[level] = levels.get(level, 0) + 1
    if levels:
        yield Result(
            state=State.OK,
            notice="Threat levels: "
            + ", ".join(f"{key} {value}" for key, value in sorted(levels.items())),
        )

    lines = []
    for feed in sorted(feeds, key=lambda item: str(item.get("name") or "")):
        name = feed.get("name") or feed.get("key") or "unnamed"
        parts = [str(name)]
        if feed.get("threat_level"):
            parts.append(f"threat {feed['threat_level']}")
        if feed.get("confidence_level"):
            parts.append(f"confidence {feed['confidence_level']}")
        if feed.get("legacy"):
            parts.append("legacy")
        if feed.get("source"):
            parts.append(f"source {feed['source']}")
        lines.append("  " + ", ".join(parts))
    if lines:
        yield Result(
            state=State.OK,
            notice="Feeds:",
            details="Feeds:\n" + "\n".join(lines[:MAX_LISTED]),
        )

    expected = params.get("expected_minimum")
    if expected is not None and len(feeds) < int(expected):
        yield Result(
            state=State(params.get("shortfall_state", 1)),
            summary=f"Fewer feeds than the expected minimum of {expected}",
        )


agent_section_infoblox_csp_threat_feed = AgentSection(
    name="infoblox_csp_threat_feed",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_threat_feed = CheckPlugin(
    name="infoblox_csp_threat_feed",
    service_name="Infoblox Threat Feeds",
    discovery_function=discover_threat_feeds,
    check_function=check_threat_feeds,
    check_default_parameters={"legacy_state": 0, "shortfall_state": 1},
    check_ruleset_name="infoblox_csp_threat_feeds",
)


# ---------------------------------------------------------------------------
# External networks
#
# Mirrors the External Networks count in the portal dashboard. These are the
# public address ranges registered against the tenant so that queries arriving
# from them are attributed to it. An address whose approval has not completed is
# registered but not in effect, which is the reason this is a check rather than
# pure inventory.
# ---------------------------------------------------------------------------
APPROVED_STATES = ("AUTO_VERIFIED", "VERIFIED", "APPROVED")


def discover_external_network(section):
    if section is not None and section.get("records") is not None:
        yield Service()


def check_external_network(params, section):
    if section is None:
        return
    lists = section.get("records") or []

    addresses = 0
    unapproved = []
    for entry in lists:
        items = entry.get("items") or []
        addresses += len(items)
        for approval in entry.get("item_approvals") or []:
            status = str(approval.get("approval_status") or "").strip().upper()
            if status and status not in APPROVED_STATES:
                unapproved.append(
                    f"{entry.get('name') or 'unnamed'}: "
                    f"{approval.get('address') or 'unknown address'} is {status}"
                )

    yield Result(
        state=State.OK,
        summary=f"{len(lists)} external networks, {addresses} addresses",
    )
    yield Metric("infoblox_external_networks", float(len(lists)))
    yield Metric("infoblox_external_network_addresses", float(addresses))

    if unapproved:
        yield Result(
            state=State(params.get("unapproved_state", 1)),
            summary=f"{len(unapproved)} addresses not approved",
            details="Not approved:\n" + "\n".join(f"  {line}" for line in unapproved),
        )

    lines = []
    for entry in sorted(lists, key=lambda item: str(item.get("name") or "")):
        header = [str(entry.get("name") or "unnamed")]
        if entry.get("policy_name"):
            header.append(f"policy {entry['policy_name']}")
        elif entry.get("policy_id") is not None:
            header.append(f"policy id {entry['policy_id']}")
        if entry.get("id") is not None:
            header.append(f"id {entry['id']}")
        if entry.get("description"):
            header.append(str(entry["description"]))
        lines.append("  " + ", ".join(header))

        described = {}
        for block in entry.get("addr_block") or []:
            if block.get("address"):
                described[block["address"]] = block.get("description") or ""
        approvals = {}
        for approval in entry.get("item_approvals") or []:
            if approval.get("address"):
                approvals[approval["address"]] = approval

        for address in entry.get("items") or []:
            detail = [f"    {address}"]
            note = described.get(address)
            if note:
                detail.append(str(note))
            approval = approvals.get(address) or {}
            if approval.get("approval_status"):
                detail.append(str(approval["approval_status"]))
            if approval.get("requested_at"):
                detail.append(f"requested {approval['requested_at']}")
            if approval.get("company_name"):
                detail.append(str(approval["company_name"]))
            if approval.get("username"):
                detail.append(f"by {approval['username']}")
            if approval.get("comments"):
                detail.append(str(approval["comments"]))
            lines.append(", ".join(detail))

        stamps = []
        if entry.get("created_time"):
            stamps.append(f"created {entry['created_time']}")
        if entry.get("updated_time"):
            stamps.append(f"updated {entry['updated_time']}")
        if stamps:
            lines.append("    " + ", ".join(stamps))

    if lines:
        yield Result(
            state=State.OK,
            notice="Networks:",
            details="Networks:\n" + "\n".join(lines[:MAX_LISTED]),
        )

    expected = params.get("expected_minimum")
    if expected is not None and len(lists) < int(expected):
        yield Result(
            state=State(params.get("shortfall_state", 1)),
            summary=f"Fewer external networks than the expected minimum of {expected}",
        )


agent_section_infoblox_csp_external_network = AgentSection(
    name="infoblox_csp_external_network",
    parse_function=parse_json_section,
)

check_plugin_infoblox_csp_external_network = CheckPlugin(
    name="infoblox_csp_external_network",
    service_name="Infoblox External Networks",
    discovery_function=discover_external_network,
    check_function=check_external_network,
    check_default_parameters={"unapproved_state": 1, "shortfall_state": 1},
    check_ruleset_name="infoblox_csp_external_network",
)


# ---------------------------------------------------------------------------
# Active DNS Forwarding Proxies
#
# Mirrors the Active DFPs count in the portal dashboard. The configuration
# endpoint alone cannot say whether a proxy is actually running, so this reads
# both the proxy configurations and the tenant service list and correlates them
# by host name.
# ---------------------------------------------------------------------------
def proxy_name(proxy):
    return proxy.get("name") or proxy.get("service_name") or proxy.get("id") or "unnamed"


def discover_dfp_summary(
    section_infoblox_csp_dfp_service,
    section_infoblox_csp_services_summary,
):
    # Sections arrive by keyword, named section_<section_name>.
    section_dfp = section_infoblox_csp_dfp_service
    if section_dfp is not None and section_dfp.get("records") is not None:
        yield Service()


def check_dfp_summary(
    params,
    section_infoblox_csp_dfp_service,
    section_infoblox_csp_services_summary,
):
    section_dfp = section_infoblox_csp_dfp_service
    section_services = section_infoblox_csp_services_summary
    if section_dfp is None:
        return
    proxies = section_dfp.get("records") or []

    running_hosts = set()
    for svc in (section_services or {}).get("services") or []:
        if str(svc.get("service_type") or "").strip().lower() != "dfp":
            continue
        if str(svc.get("composite_status") or "").strip().lower() != "online":
            continue
        for host in svc.get("hosts") or []:
            if host:
                running_hosts.add(str(host))

    def is_active(proxy):
        names = {str(proxy.get("name") or "")}
        for host in proxy.get("host") or []:
            if isinstance(host, dict) and host.get("name"):
                names.add(str(host["name"]))
        return bool(names & running_hosts)

    known_state = section_services is not None
    active = [proxy for proxy in proxies if is_active(proxy)] if known_state else []

    if known_state:
        inactive = [proxy for proxy in proxies if proxy not in active]
        percent = 100.0 * len(active) / len(proxies) if proxies else 0.0
        yield Result(
            state=State.OK if not inactive
            else State(params.get("inactive_state", 2)),
            summary=f"{len(active)} of {len(proxies)} proxies active ({percent:.0f}%)",
        )
        yield Metric("infoblox_dfp_active", float(len(active)))
        if inactive:
            yield Result(
                state=State.OK,
                details="Not active:\n" + "\n".join(
                    f"  {proxy.get('name') or 'unnamed'}" for proxy in inactive
                ),
            )
    else:
        yield Result(
            state=State.OK,
            summary=f"{len(proxies)} proxies configured, run state unavailable",
        )

    yield Metric("infoblox_dfp_configured", float(len(proxies)))

    # Forwarding policy assertion, applied across every proxy so a single
    # misconfigured one is visible.
    expected = params.get("expected_forwarding_policy")
    if expected:
        wrong = [
            f"{proxy.get('name') or 'unnamed'}: {proxy.get('forwarding_policy')}"
            for proxy in proxies
            if str(proxy.get("forwarding_policy") or "") != str(expected)
        ]
        if wrong:
            yield Result(
                state=State(params.get("mismatch_state", 1)),
                summary=f"{len(wrong)} with an unexpected forwarding policy",
                details=f"Expected {expected}:\n"
                + "\n".join(f"  {line}" for line in wrong),
            )

    policies = sorted({
        str(proxy.get("forwarding_policy")) for proxy in proxies
        if proxy.get("forwarding_policy")
    })
    if policies:
        yield Result(
            state=State.OK,
            summary="Forwarding policy: " + ", ".join(policies),
        )

    lines = []
    for proxy in sorted(proxies, key=lambda item: str(proxy_name(item))):
        header = [str(proxy_name(proxy))]
        if known_state:
            header.append("active" if proxy in active else "not active")
        if proxy.get("forwarding_policy"):
            header.append(f"forwarding {proxy['forwarding_policy']}")
        if proxy.get("policy_name"):
            header.append(f"policy {proxy['policy_name']}")
        elif proxy.get("policy_id") is not None:
            header.append(f"policy id {proxy['policy_id']}")
        lines.append("  " + ", ".join(header))

        if proxy.get("service_name"):
            lines.append(f"    service {proxy['service_name']}")

        hosts = [
            str(host.get("name"))
            for host in proxy.get("host") or []
            if isinstance(host, dict) and host.get("name")
        ]
        if hosts:
            lines.append("    hosts " + ", ".join(hosts))

        detailed = proxy.get("resolvers_all") or []
        if detailed:
            for resolver in detailed:
                if not isinstance(resolver, dict):
                    continue
                parts = [f"    resolver {resolver.get('address') or 'unknown'}"]
                protocols = resolver.get("protocols") or []
                if protocols:
                    parts.append(", ".join(str(item) for item in protocols))
                parts.append("fallback" if resolver.get("is_fallback") else "primary")
                if resolver.get("is_local"):
                    parts.append("local")
                lines.append(", ".join(parts))
        else:
            resolvers = proxy.get("default_resolvers") or []
            if resolvers:
                lines.append(
                    "    resolvers " + ", ".join(str(item) for item in resolvers)
                )

        extras = []
        if proxy.get("mode") is not None:
            extras.append(f"mode {proxy['mode']}")
        if proxy.get("mode_started_at"):
            extras.append(f"since {proxy['mode_started_at']}")
        if proxy.get("pop_region_id") is not None:
            extras.append(f"pop region {proxy['pop_region_id']}")
        if proxy.get("dnstap_cache_log") is not None:
            extras.append(
                "dnstap cache log "
                + ("on" if proxy["dnstap_cache_log"] else "off")
            )
        domain_lists = proxy.get("internal_domain_lists") or []
        if domain_lists:
            extras.append(f"{len(domain_lists)} internal domain lists")
        source_routing = proxy.get("source_routing") or []
        if source_routing:
            extras.append(f"{len(source_routing)} source routes")
        if extras:
            lines.append("    " + ", ".join(extras))

        ids = []
        if proxy.get("id") is not None:
            ids.append(f"id {proxy['id']}")
        if proxy.get("ophid"):
            ids.append(f"ophid {proxy['ophid']}")
        if proxy.get("site_id"):
            ids.append(f"site {proxy['site_id']}")
        if ids:
            lines.append("    " + ", ".join(ids))

        stamps = []
        if proxy.get("created_time"):
            stamps.append(f"created {proxy['created_time']}")
        if proxy.get("updated_time"):
            stamps.append(f"updated {proxy['updated_time']}")
        if stamps:
            lines.append("    " + ", ".join(stamps))

    if lines:
        yield Result(
            state=State.OK,
            notice="Proxies:",
            details="Proxies:\n" + "\n".join(lines[:MAX_LISTED]),
        )


check_plugin_infoblox_csp_dfp_summary = CheckPlugin(
    name="infoblox_csp_dfp_summary",
    sections=["infoblox_csp_dfp_service", "infoblox_csp_services_summary"],
    service_name="Infoblox Active DFPs",
    discovery_function=discover_dfp_summary,
    check_function=check_dfp_summary,
    check_default_parameters={"inactive_state": 2, "mismatch_state": 1},
    check_ruleset_name="infoblox_csp_dfp_summary",
)
