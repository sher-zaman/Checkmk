#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA appliance health areas.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
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

_COLOR_STATES = {
    "green": State.OK,
    "yellow": State.WARN,
    "orange": State.WARN,
    "red": State.CRIT,
    "gray": State.UNKNOWN,
    "grey": State.UNKNOWN,
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


def check_vcsa_health_appliance(item, section) -> CheckResult:
    color = section.get(item)
    if color is None:
        return
    state = _COLOR_STATES.get(color, State.UNKNOWN)
    yield Result(state=state, summary="Status: %s" % color)


check_plugin_vcsa_health_appliance = CheckPlugin(
    name="vcsa_health_appliance",
    service_name="VCSA Health %s",
    sections=["vcsa_health_appliance"],
    discovery_function=discover_vcsa_health_appliance,
    check_function=check_vcsa_health_appliance,
)
