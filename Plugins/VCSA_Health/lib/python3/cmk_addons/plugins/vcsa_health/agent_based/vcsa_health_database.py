#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA vCenter database usage by category.
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
#   util;<category>;<percent>
#   size;<retention tier>;<bytes>
#
# No default levels are set. The appliance does not document what the reported
# percentage is relative to, so any shipped threshold would be a guess. The
# ruleset lets a site apply levels once it has seen its own values trend.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    render,
)

_CATEGORIES = {
    "stats": ("Stats", "vcsa_db_stats_util"),
    "events": ("Events", "vcsa_db_events_util"),
    "alarms": ("Alarms", "vcsa_db_alarms_util"),
    "tasks": ("Tasks", "vcsa_db_tasks_util"),
}

_TIERS = {
    "hourly": ("Hourly", "vcsa_db_stats_hourly"),
    "daily": ("Daily", "vcsa_db_stats_daily"),
    "monthly": ("Monthly", "vcsa_db_stats_monthly"),
    "yearly": ("Yearly", "vcsa_db_stats_yearly"),
}


def parse_vcsa_health_database(string_table):
    section = {"util": {}, "size": {}}
    for line in string_table:
        if len(line) < 3 or line[0] not in ("util", "size"):
            continue
        try:
            section[line[0]][line[1]] = float(line[2])
        except ValueError:
            continue
    if not section["util"] and not section["size"]:
        return None
    return section


agent_section_vcsa_health_database = AgentSection(
    name="vcsa_health_database",
    parse_function=parse_vcsa_health_database,
)


def discover_vcsa_health_database(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_database(params, section) -> CheckResult:
    if not section:
        return

    # State and summary are built directly rather than via check_levels, so a
    # category that breaches its levels is named once in the summary instead of
    # appearing both as a promoted notice and in the constructed text.
    overall = State.OK
    summary_parts = []
    for key, (label, metric) in _CATEGORIES.items():
        value = section["util"].get(key)
        if value is None:
            continue

        levels = params.get("%s_levels" % key)
        state, levels_text, bounds = State.OK, "", None
        if levels and levels[0] == "fixed":
            warn, crit = levels[1]
            bounds = (warn, crit)
            if value >= crit:
                state = State.CRIT
            elif value >= warn:
                state = State.WARN
            if state is not State.OK:
                levels_text = " (warn/crit at %s/%s)" % (
                    render.percent(warn),
                    render.percent(crit),
                )

        overall = State.worst(overall, state)
        summary_parts.append("%s %s%s" % (label, render.percent(value), levels_text))
        yield Metric(metric, value, levels=bounds, boundaries=(0.0, 100.0))

    if summary_parts:
        yield Result(state=overall, summary=", ".join(summary_parts))

    for key, (label, metric) in _TIERS.items():
        value = section["size"].get(key)
        if value is None:
            continue
        yield Result(
            state=State.OK, notice="%s stats: %s" % (label, render.bytes(value))
        )
        yield Metric(metric, value)


check_plugin_vcsa_health_database = CheckPlugin(
    name="vcsa_health_database",
    service_name="VCSA Database Usage",
    sections=["vcsa_health_database"],
    discovery_function=discover_vcsa_health_database,
    check_function=check_vcsa_health_database,
    check_ruleset_name="vcsa_health_database",
    check_default_parameters={},
)
