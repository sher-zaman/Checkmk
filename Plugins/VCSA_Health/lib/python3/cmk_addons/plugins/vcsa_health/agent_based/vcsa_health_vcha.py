#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA High Availability (VCHA) cluster.
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
#   cluster;<mode>;<health>
#   node;<role>;<state>;<failover ip>
#
# NOTE: this check has not been verified against a live VCHA deployment. Where
# the expected fields are absent the result is UNKNOWN rather than a health
# verdict, so an unexpected response shape cannot yield a confident but wrong
# answer. It is refined when real data becomes available.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

_HEALTHY_MODES = {"ENABLED"}
_DEGRADED_MODES = {"MAINTENANCE", "CONFIGURING"}
_HEALTHY_NODE_STATES = {"UP", "HEALTHY"}


def parse_vcsa_health_vcha(string_table):
    section = {"mode": "", "health": "", "nodes": []}
    seen = False
    for line in string_table:
        if not line:
            continue
        if line[0] == "cluster":
            seen = True
            section["mode"] = line[1] if len(line) > 1 else ""
            section["health"] = line[2] if len(line) > 2 else ""
        elif line[0] == "node" and len(line) >= 2:
            seen = True
            section["nodes"].append({
                "role": line[1],
                "state": line[2] if len(line) > 2 else "",
                "address": line[3] if len(line) > 3 else "",
            })
    return section if seen else None


agent_section_vcsa_health_vcha = AgentSection(
    name="vcsa_health_vcha",
    parse_function=parse_vcsa_health_vcha,
)


def discover_vcsa_health_vcha(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_vcha(params, section) -> CheckResult:
    if not section:
        return

    mode = (section["mode"] or "").upper()
    if not mode:
        # Refuse to assert health from a shape we do not recognise.
        yield Result(
            state=State.UNKNOWN,
            summary="VCHA cluster reported without a recognisable mode",
        )
    elif mode in _HEALTHY_MODES:
        yield Result(state=State.OK, summary="Cluster mode: %s" % section["mode"])
    elif mode in _DEGRADED_MODES:
        yield Result(
            state=State(params["degraded_state"]),
            summary="Cluster mode: %s" % section["mode"],
        )
    elif mode == "DISABLED":
        yield Result(
            state=State(params["disabled_state"]),
            summary="Cluster mode: %s" % section["mode"],
        )
    else:
        yield Result(state=State.UNKNOWN, summary="Cluster mode: %s" % section["mode"])

    if section["health"]:
        yield Result(state=State.OK, notice="Cluster health: %s" % section["health"])

    for node in section["nodes"]:
        state_text = (node["state"] or "").upper()
        if not state_text:
            node_state = State.UNKNOWN
        elif state_text in _HEALTHY_NODE_STATES:
            node_state = State.OK
        else:
            node_state = State(params["node_down_state"])
        detail = "%s node: %s" % (node["role"].capitalize(), node["state"] or "unknown")
        if node["address"]:
            detail += " (%s)" % node["address"]
        yield Result(state=node_state, notice=detail)


check_plugin_vcsa_health_vcha = CheckPlugin(
    name="vcsa_health_vcha",
    service_name="VCSA VCHA Cluster",
    sections=["vcsa_health_vcha"],
    discovery_function=discover_vcsa_health_vcha,
    check_function=check_vcsa_health_vcha,
    check_ruleset_name="vcsa_health_vcha",
    check_default_parameters={
        "degraded_state": 1,
        "disabled_state": 1,
        "node_down_state": 2,
    },
)
