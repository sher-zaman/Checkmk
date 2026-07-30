#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA network interface link state and traffic metrics.
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only
#
# Agent section formats (sep 59):
#   vcsa_health_interfaces:  <name>;<status>;<mac>;<ipv4>;<mode>;<prefix>;<gateway>
#   vcsa_health_net_metrics: <interface>;<key>;<value>
#
# Interface naming differs between the networking API (nic0) and the
# monitoring API (eth0), so metrics are matched against name variants.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    check_levels,
    render,
)

_UP_STATES = {"up", "connected"}
_DOWN_STATES = {"down", "disconnected"}


def _variants(name):
    out = {name, name.lower()}
    for prefix, other in (("nic", "eth"), ("eth", "nic")):
        if name.startswith(prefix) and name[len(prefix) :].isdigit():
            out.add(other + name[len(prefix) :])
    return out


def parse_vcsa_health_interfaces(string_table):
    section = {}
    for line in string_table:
        if len(line) < 2:
            continue
        section[line[0]] = {
            "status": line[1],
            "mac": line[2] if len(line) > 2 else "",
            "address": line[3] if len(line) > 3 else "",
            "mode": line[4] if len(line) > 4 else "",
            "prefix": line[5] if len(line) > 5 else "",
            "gateway": line[6] if len(line) > 6 else "",
        }
    return section


def parse_vcsa_health_net_metrics(string_table):
    section = {}
    for line in string_table:
        if len(line) < 3:
            continue
        try:
            value = float(line[2])
        except ValueError:
            continue
        section.setdefault(line[0], {})[line[1]] = value
    return section


agent_section_vcsa_health_interfaces = AgentSection(
    name="vcsa_health_interfaces",
    parse_function=parse_vcsa_health_interfaces,
)

agent_section_vcsa_health_net_metrics = AgentSection(
    name="vcsa_health_net_metrics",
    parse_function=parse_vcsa_health_net_metrics,
)


def _metrics_for(item, section_metrics):
    if not section_metrics:
        return {}
    for name in _variants(item):
        if name in section_metrics:
            return section_metrics[name]
    return {}


def discover_vcsa_health_interfaces(
    section_vcsa_health_interfaces, section_vcsa_health_net_metrics
) -> DiscoveryResult:
    items = set(section_vcsa_health_interfaces or {})
    # Interfaces that only appear in the monitoring API still get a service.
    for name in section_vcsa_health_net_metrics or {}:
        if not any(name in _variants(existing) for existing in items):
            items.add(name)
    for item in sorted(items):
        yield Service(item=item)


def check_vcsa_health_interfaces(
    item, params, section_vcsa_health_interfaces, section_vcsa_health_net_metrics
) -> CheckResult:
    info = (section_vcsa_health_interfaces or {}).get(item)
    metrics = _metrics_for(item, section_vcsa_health_net_metrics)

    if info is None and not metrics:
        return

    if info is not None:
        status = info["status"].lower()
        if status in _UP_STATES:
            state = State.OK
        elif status in _DOWN_STATES:
            state = State(params["link_down"])
        else:
            state = State.UNKNOWN
        yield Result(state=state, summary="Link: %s" % (info["status"] or "unknown"))
        if info["address"]:
            yield Result(state=State.OK, summary="IPv4: %s" % info["address"])
        if info["mac"]:
            yield Result(state=State.OK, notice="MAC: %s" % info["mac"])
        if info["mode"]:
            yield Result(state=State.OK, notice="Address mode: %s" % info["mode"])
        if info["prefix"]:
            yield Result(state=State.OK, notice="Prefix: /%s" % info["prefix"])
        if info["gateway"]:
            yield Result(
                state=State.OK, notice="Default gateway: %s" % info["gateway"]
            )

        # A vCenter that has flipped from a static address to DHCP is a real
        # incident, so a site can declare the mode it expects. No default is
        # imposed because both modes are legitimate.
        expected = params.get("expected_address_mode", "any")
        if expected != "any" and info["mode"] and info["mode"].upper() != expected:
            yield Result(
                state=State(params["mode_deviation_state"]),
                summary="Address mode is %s but expected %s"
                % (info["mode"], expected),
            )

    if "rx_activity" in metrics:
        yield from check_levels(
            metrics["rx_activity"],
            metric_name="vcsa_if_in",
            label="In",
            render_func=render.iobandwidth,
        )
    if "tx_activity" in metrics:
        yield from check_levels(
            metrics["tx_activity"],
            metric_name="vcsa_if_out",
            label="Out",
            render_func=render.iobandwidth,
        )

    for key, metric, label in (
        ("rx_packets", "vcsa_if_in_packets", "Packets in"),
        ("tx_packets", "vcsa_if_out_packets", "Packets out"),
    ):
        if key in metrics:
            yield from check_levels(
                metrics[key],
                metric_name=metric,
                label=label,
                render_func=lambda v: "%.1f/s" % v,
                notice_only=True,
            )

    for key, metric, label, levels_key in (
        ("rx_errors", "vcsa_if_in_errors", "Errors in", "error_levels"),
        ("tx_errors", "vcsa_if_out_errors", "Errors out", "error_levels"),
        ("rx_drops", "vcsa_if_in_drops", "Drops in", "drop_levels"),
        ("tx_drops", "vcsa_if_out_drops", "Drops out", "drop_levels"),
    ):
        if key in metrics:
            yield from check_levels(
                metrics[key],
                levels_upper=params.get(levels_key),
                metric_name=metric,
                label=label,
                render_func=lambda v: "%.1f" % v,
                notice_only=True,
            )


check_plugin_vcsa_health_interfaces = CheckPlugin(
    name="vcsa_health_interfaces",
    service_name="VCSA Interface %s",
    sections=["vcsa_health_interfaces", "vcsa_health_net_metrics"],
    discovery_function=discover_vcsa_health_interfaces,
    check_function=check_vcsa_health_interfaces,
    check_ruleset_name="vcsa_health_interfaces",
    check_default_parameters={
        "link_down": 2,
        "expected_address_mode": "any",
        "mode_deviation_state": 1,
        "error_levels": ("fixed", (10.0, 100.0)),
        "drop_levels": ("fixed", (10.0, 100.0)),
    },
)
