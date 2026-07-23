#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA CPU, memory and swap utilization.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   <metric id>;<value>;<unit>

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

_ITEMS = {
    "CPU": "vcsa_cpu_util",
    "Memory": "vcsa_mem_util",
    "Swap": "vcsa_swap_util",
}


def parse_vcsa_health_perf(string_table):
    section = {}
    for line in string_table:
        if len(line) < 2:
            continue
        resource = line[0]
        if resource not in _ITEMS:
            continue
        try:
            value = float(line[1])
        except ValueError:
            continue
        unit = line[2] if len(line) > 2 else "percent"
        section[resource] = {"metric": _ITEMS[resource], "value": value, "unit": unit}
    return section


agent_section_vcsa_health_perf = AgentSection(
    name="vcsa_health_perf",
    parse_function=parse_vcsa_health_perf,
)


def discover_vcsa_health_perf(section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_vcsa_health_perf(item, params, section) -> CheckResult:
    data = section.get(item)
    if data is None:
        return
    unit = data["unit"].lower()
    if unit and "percent" not in unit:
        yield Result(
            state=State.UNKNOWN,
            summary="Unexpected unit %r reported by the appliance API" % data["unit"],
        )
        return
    yield from check_levels(
        data["value"],
        levels_upper=params.get("levels"),
        metric_name=data["metric"],
        label="Utilization",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )


check_plugin_vcsa_health_perf = CheckPlugin(
    name="vcsa_health_perf",
    service_name="VCSA %s utilization",
    sections=["vcsa_health_perf"],
    discovery_function=discover_vcsa_health_perf,
    check_function=check_vcsa_health_perf,
    check_ruleset_name="vcsa_health_perf",
    check_default_parameters={"levels": ("fixed", (80.0, 90.0))},
)
