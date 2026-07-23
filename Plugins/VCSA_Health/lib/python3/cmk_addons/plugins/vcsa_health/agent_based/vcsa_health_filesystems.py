#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA appliance filesystem usage.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   <filesystem>;<used bytes>;<total bytes>

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    check_levels,
    render,
)


def parse_vcsa_health_filesystems(string_table):
    section = {}
    for line in string_table:
        if len(line) < 3:
            continue
        try:
            used, total = float(line[1]), float(line[2])
        except ValueError:
            continue
        if total > 0:
            section[line[0]] = (used, total)
    return section


agent_section_vcsa_health_filesystems = AgentSection(
    name="vcsa_health_filesystems",
    parse_function=parse_vcsa_health_filesystems,
)


def discover_vcsa_health_filesystems(section) -> DiscoveryResult:
    for filesystem in section:
        yield Service(item=filesystem)


def check_vcsa_health_filesystems(item, params, section) -> CheckResult:
    data = section.get(item)
    if data is None:
        return
    used, total = data
    used_percent = used / total * 100.0

    yield from check_levels(
        used_percent,
        levels_upper=params.get("levels"),
        metric_name="vcsa_fs_used_percent",
        label="Used",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )
    yield Result(
        state=State.OK,
        summary="%s of %s" % (render.bytes(used), render.bytes(total)),
    )
    yield Metric("vcsa_fs_used", used, boundaries=(0.0, total))


check_plugin_vcsa_health_filesystems = CheckPlugin(
    name="vcsa_health_filesystems",
    service_name="VCSA Filesystem %s",
    sections=["vcsa_health_filesystems"],
    discovery_function=discover_vcsa_health_filesystems,
    check_function=check_vcsa_health_filesystems,
    check_ruleset_name="vcsa_health_filesystems",
    check_default_parameters={"levels": ("fixed", (80.0, 90.0))},
)
