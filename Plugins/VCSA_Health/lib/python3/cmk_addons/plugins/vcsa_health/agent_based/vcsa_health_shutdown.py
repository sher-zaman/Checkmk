#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA pending shutdown or reboot.
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   error;<http status>
#   shutdown;<action>;<reason>;<scheduled epoch>

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


def parse_vcsa_health_shutdown(string_table):
    for line in string_table:
        if not line:
            continue
        if line[0] == "error":
            return {"error": line[1] if len(line) > 1 else "unknown"}
        if line[0] == "shutdown":
            scheduled = None
            if len(line) > 3 and line[3]:
                try:
                    scheduled = float(line[3])
                except ValueError:
                    scheduled = None
            return {
                "action": line[1] if len(line) > 1 else "",
                "reason": line[2] if len(line) > 2 else "",
                "scheduled": scheduled,
            }
    return None


agent_section_vcsa_health_shutdown = AgentSection(
    name="vcsa_health_shutdown",
    parse_function=parse_vcsa_health_shutdown,
)


def discover_vcsa_health_shutdown(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_shutdown(params, section) -> CheckResult:
    if not section:
        return

    if "error" in section:
        yield Result(
            state=State.UNKNOWN,
            summary="Unable to retrieve shutdown status (HTTP %s)" % section["error"],
        )
        return

    action = section["action"]
    if not action:
        yield Result(state=State.OK, summary="No shutdown or reboot pending")
        return

    yield Result(
        state=State(params["pending_state"]),
        summary="Pending %s" % action,
    )
    if section["scheduled"]:
        yield Result(
            state=State.OK,
            summary="scheduled for %s" % render.datetime(section["scheduled"]),
        )
    if section["reason"]:
        yield Result(state=State.OK, notice="Reason: %s" % section["reason"])


check_plugin_vcsa_health_shutdown = CheckPlugin(
    name="vcsa_health_shutdown",
    service_name="VCSA Pending Shutdown",
    sections=["vcsa_health_shutdown"],
    discovery_function=discover_vcsa_health_shutdown,
    check_function=check_vcsa_health_shutdown,
    check_ruleset_name="vcsa_health_shutdown",
    check_default_parameters={"pending_state": 1},
)
