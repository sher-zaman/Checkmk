#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA appliance filesystem usage.
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
#   <filesystem>;<used percent>;<used bytes or empty>;<total bytes or empty>
#
# The percentage comes from the appliance's own util metric rather than being
# derived, because the declared units on the used and totalsize metrics are not
# consistent between appliances. Absolute sizes are only present when both
# underlying values were reported in kb.

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

# The archive partition is designed to fill and is documented as safe to ignore
# when high, so it ships without default levels instead of alerting on every
# appliance. A ruleset can still impose levels where a site wants them.
NO_DEFAULT_LEVELS = {"archive"}


def parse_vcsa_health_filesystems(string_table):
    section = {}
    for line in string_table:
        if len(line) < 2:
            continue
        try:
            percent = float(line[1])
        except ValueError:
            continue

        def _optional(index):
            if len(line) > index and line[index]:
                try:
                    return float(line[index])
                except ValueError:
                    return None
            return None

        section[line[0]] = {
            "percent": percent,
            "used": _optional(2),
            "total": _optional(3),
        }
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

    levels = params.get("levels")
    if item in NO_DEFAULT_LEVELS and not params.get("apply_levels_to_archive"):
        levels = None

    yield from check_levels(
        data["percent"],
        levels_upper=levels,
        metric_name="vcsa_fs_used_percent",
        label="Used",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )

    used, total = data["used"], data["total"]
    if used is not None and total is not None and total > 0:
        yield Result(
            state=State.OK,
            summary="%s of %s" % (render.bytes(used), render.bytes(total)),
        )
        yield Metric("vcsa_fs_used", used, boundaries=(0.0, total))

    if levels is None:
        yield Result(state=State.OK, notice="No levels applied to this filesystem")


check_plugin_vcsa_health_filesystems = CheckPlugin(
    name="vcsa_health_filesystems",
    service_name="VCSA Filesystem %s",
    sections=["vcsa_health_filesystems"],
    discovery_function=discover_vcsa_health_filesystems,
    check_function=check_vcsa_health_filesystems,
    check_ruleset_name="vcsa_health_filesystems",
    check_default_parameters={
        "levels": ("fixed", (80.0, 90.0)),
        "apply_levels_to_archive": False,
    },
)
