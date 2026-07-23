#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA update status.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   update;<state>;<pending version>;<latest query epoch>
#   version;<version>;<build>;<product>

import time

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    render,
)

_UPDATE_STATES = {
    "UP_TO_DATE": State.OK,
    "UPDATES_PENDING": State.WARN,
    "STAGE_IN_PROGRESS": State.WARN,
    "INSTALL_IN_PROGRESS": State.WARN,
    "INSTALL_FAILED": State.CRIT,
    "ROLLBACK_IN_PROGRESS": State.CRIT,
}


def parse_vcsa_health_update(string_table):
    section = {}
    for line in string_table:
        if not line:
            continue
        if line[0] == "update" and len(line) >= 2:
            section["state"] = line[1]
            section["pending_version"] = line[2] if len(line) > 2 else ""
            try:
                section["query_time"] = float(line[3])
            except (IndexError, ValueError):
                pass
        elif line[0] == "version" and len(line) >= 2:
            section["version"] = line[1]
            section["build"] = line[2] if len(line) > 2 else ""
            section["product"] = line[3] if len(line) > 3 else ""
    return section or None


agent_section_vcsa_health_update = AgentSection(
    name="vcsa_health_update",
    parse_function=parse_vcsa_health_update,
)


def discover_vcsa_health_update(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_update(section) -> CheckResult:
    if not section:
        return

    update_state = section.get("state")
    if update_state:
        state = _UPDATE_STATES.get(update_state, State.UNKNOWN)
        summary = "Update status: %s" % update_state
        pending = section.get("pending_version")
        if pending and update_state != "UP_TO_DATE":
            summary += " (version %s)" % pending
        yield Result(state=state, summary=summary)

    version = section.get("version")
    if version:
        details = version
        if section.get("build"):
            details += " build %s" % section["build"]
        yield Result(state=State.OK, summary="Version: %s" % details)

    query_time = section.get("query_time")
    if query_time:
        age = time.time() - query_time
        yield Result(
            state=State.OK,
            notice="Last update check: %s ago" % render.timespan(max(age, 0)),
        )


check_plugin_vcsa_health_update = CheckPlugin(
    name="vcsa_health_update",
    service_name="VCSA Update",
    sections=["vcsa_health_update"],
    discovery_function=discover_vcsa_health_update,
    check_function=check_vcsa_health_update,
)
