#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA syslog forwarding.
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
#   <hostname>;<port>;<protocol>

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)


def parse_vcsa_health_syslog(string_table):
    targets = []
    for line in string_table:
        if not line or not line[0]:
            continue
        targets.append({
            "hostname": line[0],
            "port": line[1] if len(line) > 1 else "",
            "protocol": line[2] if len(line) > 2 else "",
        })
    return targets


agent_section_vcsa_health_syslog = AgentSection(
    name="vcsa_health_syslog",
    parse_function=parse_vcsa_health_syslog,
)


def discover_vcsa_health_syslog(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_syslog(params, section) -> CheckResult:
    if not section:
        # Only reachable if the section was emitted empty. A site that requires
        # forwarding can have this raise an alarm.
        yield Result(
            state=State(params["no_targets"]),
            summary="No syslog forwarding configured",
        )
        return

    described = [
        "%s:%s (%s)" % (t["hostname"], t["port"], t["protocol"]) for t in section
    ]
    yield Result(
        state=State.OK,
        summary="%d target(s): %s" % (len(section), ", ".join(described)),
    )


check_plugin_vcsa_health_syslog = CheckPlugin(
    name="vcsa_health_syslog",
    service_name="VCSA Syslog Forwarding",
    sections=["vcsa_health_syslog"],
    discovery_function=discover_vcsa_health_syslog,
    check_function=check_vcsa_health_syslog,
    check_ruleset_name="vcsa_health_syslog",
    check_default_parameters={"no_targets": 0},
)
