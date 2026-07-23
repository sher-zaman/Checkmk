#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA vMon service states.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   <name>;<startup_type>;<state>;<health>;<health messages>

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)


def parse_vcsa_health_services(string_table):
    section = {}
    for line in string_table:
        if len(line) < 4:
            continue
        name, startup, state, health = line[0], line[1], line[2], line[3]
        messages = line[4] if len(line) > 4 else ""
        section[name] = {
            "startup_type": startup,
            "state": state,
            "health": health,
            "messages": messages,
        }
    return section


agent_section_vcsa_health_services = AgentSection(
    name="vcsa_health_services",
    parse_function=parse_vcsa_health_services,
)


def discover_vcsa_health_services(section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_vcsa_health_services(item, params, section) -> CheckResult:
    svc = section.get(item)
    if svc is None:
        return

    startup = svc["startup_type"]
    svc_state = svc["state"]
    health = svc["health"]

    if svc_state == "STARTED":
        if health in ("HEALTHY", "-", ""):
            state = (
                State(params["disabled_started"])
                if startup == "DISABLED"
                else State.OK
            )
        elif health == "HEALTHY_WITH_WARNINGS":
            state = State(params["health_warnings"])
        elif health == "DEGRADED":
            state = State(params["health_degraded"])
        else:
            state = State.UNKNOWN
    else:  # not running
        if startup == "AUTOMATIC":
            state = State(params["automatic_stopped"])
        elif startup == "MANUAL":
            state = State(params["manual_stopped"])
        elif startup == "DISABLED":
            state = State(params["disabled_stopped"])
        else:
            state = State.UNKNOWN

    summary = "Startup type: %s, State: %s" % (startup, svc_state)
    if health not in ("", "-"):
        summary += ", Health: %s" % health
    yield Result(state=state, summary=summary)

    if svc["messages"]:
        yield Result(state=State.OK, notice=svc["messages"])


check_plugin_vcsa_health_services = CheckPlugin(
    name="vcsa_health_services",
    service_name="VCSA Service %s",
    sections=["vcsa_health_services"],
    discovery_function=discover_vcsa_health_services,
    check_function=check_vcsa_health_services,
    check_ruleset_name="vcsa_health_services",
    check_default_parameters={
        "automatic_stopped": 2,
        "manual_stopped": 0,
        "disabled_stopped": 0,
        "disabled_started": 1,
        "health_warnings": 1,
        "health_degraded": 2,
    },
)
