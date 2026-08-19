#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA Enhanced Linked Mode replication.
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
#   node;<node>;<comma separated partners>
#   status;<node>;<partner>;<1 available | 0>;<lag>
#
# The section is only emitted for appliances that actually have replication
# partners, so standalone embedded deployments get no service.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)


def parse_vcsa_health_replication(string_table):
    section = {"nodes": [], "status": []}
    for line in string_table:
        if not line:
            continue
        if line[0] == "node" and len(line) >= 2:
            partners = [p for p in (line[2].split(",") if len(line) > 2 else []) if p]
            section["nodes"].append({"node": line[1], "partners": partners})
        elif line[0] == "status" and len(line) >= 3:
            lag = None
            if len(line) > 4 and line[4]:
                try:
                    lag = float(line[4])
                except ValueError:
                    lag = None
            section["status"].append({
                "node": line[1],
                "partner": line[2],
                "available": line[3] == "1" if len(line) > 3 else None,
                "lag": lag,
            })
    if not section["nodes"]:
        return None
    return section


agent_section_vcsa_health_replication = AgentSection(
    name="vcsa_health_replication",
    parse_function=parse_vcsa_health_replication,
)


def discover_vcsa_health_replication(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_replication(params, section) -> CheckResult:
    if not section:
        return

    partner_count = sum(len(n["partners"]) for n in section["nodes"])
    yield Result(
        state=State.OK,
        summary="%d node(s), %d replication partner(s)"
        % (len(section["nodes"]), partner_count),
    )

    for node in section["nodes"]:
        yield Result(
            state=State.OK,
            notice="%s partners: %s" % (node["node"], ", ".join(node["partners"])),
        )

    unavailable = [s for s in section["status"] if s["available"] is False]
    if unavailable:
        for entry in unavailable:
            yield Result(
                state=State(params["partner_unavailable_state"]),
                summary="Replication partner %s unavailable from %s"
                % (entry["partner"], entry["node"]),
            )

    for entry in section["status"]:
        if entry["lag"] is not None:
            yield Result(
                state=State.OK,
                notice="%s to %s lag: %s"
                % (entry["node"], entry["partner"], entry["lag"]),
            )


check_plugin_vcsa_health_replication = CheckPlugin(
    name="vcsa_health_replication",
    service_name="VCSA Replication",
    sections=["vcsa_health_replication"],
    discovery_function=discover_vcsa_health_replication,
    check_function=check_vcsa_health_replication,
    check_ruleset_name="vcsa_health_replication",
    check_default_parameters={"partner_unavailable_state": 2},
)
