#!/usr/bin/env python3
"""Metric and graph definitions for the Infoblox CSP special agent.

The three usage figures are deliberately given separate graphs rather than one
combined graph. They are on unrelated scales, and each is a periodically
recomputed twenty four hour peak rather than a live rate, so overlaying them
would suggest a relationship that is not there.

Author:  Sher Zaman (sher[at]sherz[dot]dev, https://sherz.dev)
Repo:    https://github.com/sher-zaman/Checkmk
License: GPL-2.0-only
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, TimeNotation, Unit
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

UNIT_PERCENT = Unit(DecimalNotation("%"))
UNIT_COUNT = Unit(DecimalNotation(""))
UNIT_RATE = Unit(DecimalNotation("/s"))
UNIT_TIME = Unit(TimeNotation())

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
metric_infoblox_dns_qps_peak_24h = Metric(
    name="infoblox_dns_qps_peak_24h",
    title=Title("DNS queries, 24h peak"),
    unit=UNIT_RATE,
    color=Color.BLUE,
)

metric_infoblox_dhcp_lps_peak_24h = Metric(
    name="infoblox_dhcp_lps_peak_24h",
    title=Title("DHCP leases, 24h peak"),
    unit=UNIT_RATE,
    color=Color.GREEN,
)

metric_infoblox_objects_peak_24h = Metric(
    name="infoblox_objects_peak_24h",
    title=Title("IPAM objects, 24h peak"),
    unit=UNIT_COUNT,
    color=Color.PURPLE,
)

graph_infoblox_dns_qps = Graph(
    name="infoblox_dns_qps",
    title=Title("DNS queries, 24h peak"),
    simple_lines=["infoblox_dns_qps_peak_24h"],
    minimal_range=MinimalRange(0, 10),
)

graph_infoblox_dhcp_lps = Graph(
    name="infoblox_dhcp_lps",
    title=Title("DHCP leases, 24h peak"),
    simple_lines=["infoblox_dhcp_lps_peak_24h"],
    minimal_range=MinimalRange(0, 1),
)

graph_infoblox_objects = Graph(
    name="infoblox_objects",
    title=Title("IPAM objects, 24h peak"),
    simple_lines=["infoblox_objects_peak_24h"],
    minimal_range=MinimalRange(0, 100),
)

# ---------------------------------------------------------------------------
# IP utilisation
# ---------------------------------------------------------------------------
metric_infoblox_ip_utilization = Metric(
    name="infoblox_ip_utilization",
    title=Title("Address utilisation"),
    unit=UNIT_PERCENT,
    color=Color.BLUE,
)

metric_infoblox_dhcp_utilization = Metric(
    name="infoblox_dhcp_utilization",
    title=Title("DHCP pool utilisation"),
    unit=UNIT_PERCENT,
    color=Color.CYAN,
)

metric_infoblox_abandon_utilization = Metric(
    name="infoblox_abandon_utilization",
    title=Title("Abandoned addresses"),
    unit=UNIT_PERCENT,
    color=Color.ORANGE,
)

metric_infoblox_ip_used = Metric(
    name="infoblox_ip_used",
    title=Title("Used addresses"),
    unit=UNIT_COUNT,
    color=Color.DARK_BLUE,
)

metric_infoblox_ip_free = Metric(
    name="infoblox_ip_free",
    title=Title("Free addresses"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_infoblox_ip_total = Metric(
    name="infoblox_ip_total",
    title=Title("Total addresses"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

metric_infoblox_ip_static = Metric(
    name="infoblox_ip_static",
    title=Title("Static addresses"),
    unit=UNIT_COUNT,
    color=Color.PURPLE,
)

metric_infoblox_ip_dynamic = Metric(
    name="infoblox_ip_dynamic",
    title=Title("Dynamic addresses"),
    unit=UNIT_COUNT,
    color=Color.LIGHT_BLUE,
)

metric_infoblox_ip_abandoned = Metric(
    name="infoblox_ip_abandoned",
    title=Title("Abandoned addresses"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

graph_infoblox_ip_utilization = Graph(
    name="infoblox_ip_utilization",
    title=Title("Address utilisation"),
    simple_lines=[
        "infoblox_ip_utilization",
        "infoblox_dhcp_utilization",
        "infoblox_abandon_utilization",
    ],
    minimal_range=MinimalRange(0, 100),
)

graph_infoblox_ip_counts = Graph(
    name="infoblox_ip_counts",
    title=Title("Address counts"),
    simple_lines=["infoblox_ip_total"],
    compound_lines=[
        "infoblox_ip_static",
        "infoblox_ip_dynamic",
        "infoblox_ip_abandoned",
        "infoblox_ip_free",
    ],
)

perfometer_infoblox_ip_utilization = Perfometer(
    name="infoblox_ip_utilization",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["infoblox_ip_utilization"],
)

# ---------------------------------------------------------------------------
# Ages and durations
# ---------------------------------------------------------------------------
metric_infoblox_ha_heartbeat_age = Metric(
    name="infoblox_ha_heartbeat_age",
    title=Title("Oldest peer heartbeat age"),
    unit=UNIT_TIME,
    color=Color.ORANGE,
)

metric_infoblox_last_checkin_age = Metric(
    name="infoblox_last_checkin_age",
    title=Title("Time since last check-in"),
    unit=UNIT_TIME,
    color=Color.BLUE,
)

metric_infoblox_state_duration = Metric(
    name="infoblox_state_duration",
    title=Title("Time in current state"),
    unit=UNIT_TIME,
    color=Color.GRAY,
)

# ---------------------------------------------------------------------------
# Tenant counts
# ---------------------------------------------------------------------------
metric_infoblox_hosts_total = Metric(
    name="infoblox_hosts_total",
    title=Title("NIOS-X servers"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

metric_infoblox_hosts_online = Metric(
    name="infoblox_hosts_online",
    title=Title("NIOS-X servers online"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_infoblox_service_availability = Metric(
    name="infoblox_service_availability",
    title=Title("Service availability"),
    unit=UNIT_PERCENT,
    color=Color.GREEN,
)

metric_infoblox_service_instances = Metric(
    name="infoblox_service_instances",
    title=Title("Service instances"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

perfometer_infoblox_service_availability = Perfometer(
    name="infoblox_service_availability",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["infoblox_service_availability"],
)

metric_infoblox_dns_zones = Metric(
    name="infoblox_dns_zones",
    title=Title("Authoritative zones"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_infoblox_dns_zones_disabled = Metric(
    name="infoblox_dns_zones_disabled",
    title=Title("Disabled zones"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_infoblox_dns_zones_warning = Metric(
    name="infoblox_dns_zones_warning",
    title=Title("Zones with warnings"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_infoblox_dns_zones_signed = Metric(
    name="infoblox_dns_zones_signed",
    title=Title("DNSSEC signed zones"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_infoblox_threat_feeds = Metric(
    name="infoblox_threat_feeds",
    title=Title("Threat feeds"),
    unit=UNIT_COUNT,
    color=Color.PURPLE,
)

metric_infoblox_threat_feeds_legacy = Metric(
    name="infoblox_threat_feeds_legacy",
    title=Title("Legacy threat feeds"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_infoblox_anycast_members = Metric(
    name="infoblox_anycast_members",
    title=Title("Anycast member hosts"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

metric_infoblox_anycast_members_active = Metric(
    name="infoblox_anycast_members_active",
    title=Title("Anycast hosts advertising"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

graph_infoblox_anycast = Graph(
    name="infoblox_anycast",
    title=Title("Anycast advertisement"),
    simple_lines=[
        "infoblox_anycast_members",
        "infoblox_anycast_members_active",
    ],
)

metric_infoblox_external_networks = Metric(
    name="infoblox_external_networks",
    title=Title("External networks"),
    unit=UNIT_COUNT,
    color=Color.CYAN,
)

metric_infoblox_external_network_addresses = Metric(
    name="infoblox_external_network_addresses",
    title=Title("External network addresses"),
    unit=UNIT_COUNT,
    color=Color.DARK_CYAN,
)

metric_infoblox_dfp_configured = Metric(
    name="infoblox_dfp_configured",
    title=Title("DNS forwarding proxies configured"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

metric_infoblox_dfp_active = Metric(
    name="infoblox_dfp_active",
    title=Title("DNS forwarding proxies active"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

graph_infoblox_dfp = Graph(
    name="infoblox_dfp",
    title=Title("DNS forwarding proxies"),
    simple_lines=["infoblox_dfp_configured", "infoblox_dfp_active"],
)

metric_infoblox_policy_rules = Metric(
    name="infoblox_policy_rules",
    title=Title("Security policy rules"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_infoblox_maintenance_windows = Metric(
    name="infoblox_maintenance_windows",
    title=Title("Maintenance windows"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

metric_infoblox_dns_lame_ttl = Metric(
    name="infoblox_dns_lame_ttl",
    title=Title("Lame TTL"),
    unit=UNIT_TIME,
    color=Color.GRAY,
)

metric_infoblox_dns_max_cache_ttl = Metric(
    name="infoblox_dns_max_cache_ttl",
    title=Title("Maximum cache TTL"),
    unit=UNIT_TIME,
    color=Color.BLUE,
)

metric_infoblox_dns_max_negative_ttl = Metric(
    name="infoblox_dns_max_negative_ttl",
    title=Title("Maximum negative TTL"),
    unit=UNIT_TIME,
    color=Color.ORANGE,
)

graph_infoblox_hosts = Graph(
    name="infoblox_hosts",
    title=Title("NIOS-X servers"),
    simple_lines=["infoblox_hosts_total", "infoblox_hosts_online"],
)

graph_infoblox_dns_zones = Graph(
    name="infoblox_dns_zones",
    title=Title("DNS zones"),
    simple_lines=["infoblox_dns_zones"],
    compound_lines=[
        "infoblox_dns_zones_signed",
        "infoblox_dns_zones_warning",
        "infoblox_dns_zones_disabled",
    ],
)
