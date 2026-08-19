#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA appliance health areas.
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
#   <area>;<color>

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

# Colour to parameter key. "grey" is accepted as an alias for "gray".
_COLOR_KEYS = {
    "green": "green",
    "yellow": "yellow",
    "orange": "orange",
    "red": "red",
    "gray": "gray",
    "grey": "gray",
}


def parse_vcsa_health_appliance(string_table):
    return {line[0]: line[1] for line in string_table if len(line) >= 2}


agent_section_vcsa_health_appliance = AgentSection(
    name="vcsa_health_appliance",
    parse_function=parse_vcsa_health_appliance,
)


def discover_vcsa_health_appliance(section) -> DiscoveryResult:
    for area in section:
        yield Service(item=area)


def check_vcsa_health_appliance(item, params, section) -> CheckResult:
    color = section.get(item)
    if color is None:
        return
    key = _COLOR_KEYS.get(color)
    state = State(params[key]) if key and key in params else State.UNKNOWN
    yield Result(state=state, summary="Status: %s" % color)


check_plugin_vcsa_health_appliance = CheckPlugin(
    name="vcsa_health_appliance",
    service_name="VCSA Health %s",
    sections=["vcsa_health_appliance"],
    discovery_function=discover_vcsa_health_appliance,
    check_function=check_vcsa_health_appliance,
    check_ruleset_name="vcsa_health_appliance",
    check_default_parameters={
        "green": 0,
        "yellow": 1,
        "orange": 1,
        "red": 2,
        "gray": 3,
    },
)
