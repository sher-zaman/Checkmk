#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA proxy configuration.
#
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   <protocol>;<server>;<port>
#
# The section is only emitted when a proxy is actually enabled, so appliances
# without one get no service.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)


def parse_vcsa_health_proxy(string_table):
    section = {}
    for line in string_table:
        if len(line) < 2:
            continue
        section[line[0]] = {
            "server": line[1],
            "port": line[2] if len(line) > 2 else "",
        }
    return section


agent_section_vcsa_health_proxy = AgentSection(
    name="vcsa_health_proxy",
    parse_function=parse_vcsa_health_proxy,
)


def discover_vcsa_health_proxy(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_proxy(params, section) -> CheckResult:
    if not section:
        return

    parts = []
    for protocol in sorted(section):
        cfg = section[protocol]
        target = cfg["server"]
        if cfg["port"]:
            target += ":%s" % cfg["port"]
        parts.append("%s %s" % (protocol, target))

    yield Result(state=State.OK, summary="Enabled: %s" % ", ".join(parts))

    expected = params.get("expected_state", "any")
    if expected == "disabled":
        yield Result(
            state=State(params["deviation_state"]),
            summary="Proxy is enabled but expected disabled",
        )


check_plugin_vcsa_health_proxy = CheckPlugin(
    name="vcsa_health_proxy",
    service_name="VCSA Proxy",
    sections=["vcsa_health_proxy"],
    discovery_function=discover_vcsa_health_proxy,
    check_function=check_vcsa_health_proxy,
    check_ruleset_name="vcsa_health_proxy",
    check_default_parameters={"expected_state": "any", "deviation_state": 1},
)
