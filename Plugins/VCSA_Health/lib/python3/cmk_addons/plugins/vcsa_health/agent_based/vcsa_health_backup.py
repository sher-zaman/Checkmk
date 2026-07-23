#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA file-based backup status.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   <job id>;<status>;<type>;<start epoch>;<end epoch>;<messages>

import time

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

_JOB_STATES = {
    "SUCCEEDED": State.OK,
    "RUNNING": State.OK,
    "IN_PROGRESS": State.OK,
    "PENDING": State.OK,
    "FAILED": State.CRIT,
    "BLOCKED": State.WARN,
    "CANCELLED": State.WARN,
    "NONE": State.WARN,
}


def parse_vcsa_health_backup(string_table):
    for line in string_table:
        if len(line) < 2:
            continue
        section = {
            "job_id": line[0],
            "status": line[1],
            "type": line[2] if len(line) > 2 else "",
            "messages": line[5] if len(line) > 5 else "",
        }
        for key, index in (("start", 3), ("end", 4)):
            try:
                section[key] = float(line[index])
            except (IndexError, ValueError):
                section[key] = None
        return section
    return None


agent_section_vcsa_health_backup = AgentSection(
    name="vcsa_health_backup",
    parse_function=parse_vcsa_health_backup,
)


def discover_vcsa_health_backup(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_backup(params, section) -> CheckResult:
    if not section:
        return

    status = section["status"]
    state = _JOB_STATES.get(status, State.UNKNOWN)
    summary = "Last backup job: %s" % status
    if section["type"]:
        summary += " (%s)" % section["type"]
    yield Result(state=state, summary=summary)

    reference = section.get("end") or section.get("start")
    if reference and status not in ("RUNNING", "IN_PROGRESS", "PENDING"):
        age = max(time.time() - reference, 0)
        yield from check_levels(
            age,
            levels_upper=params.get("age_levels"),
            metric_name="vcsa_backup_age",
            label="Age",
            render_func=render.timespan,
        )

    if section["messages"]:
        yield Result(state=State.OK, notice=section["messages"])


check_plugin_vcsa_health_backup = CheckPlugin(
    name="vcsa_health_backup",
    service_name="VCSA Backup",
    sections=["vcsa_health_backup"],
    discovery_function=discover_vcsa_health_backup,
    check_function=check_vcsa_health_backup,
    check_ruleset_name="vcsa_health_backup",
    check_default_parameters={"age_levels": ("fixed", (93600.0, 180000.0))},
)
