#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA DNS server configuration.
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
#   dns;<mode>;<comma separated servers>;<hostname>

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)


def parse_vcsa_health_dns(string_table):
    for line in string_table:
        if not line:
            continue
        if line[0] == "error":
            return {"error": line[1] if len(line) > 1 else "unknown"}
        if line[0] != "dns":
            continue
        servers = []
        if len(line) > 2 and line[2]:
            servers = [s for s in line[2].split(",") if s]
        return {
            "mode": line[1] if len(line) > 1 else "",
            "servers": servers,
            "hostname": line[3] if len(line) > 3 else "",
        }
    return None


agent_section_vcsa_health_dns = AgentSection(
    name="vcsa_health_dns",
    parse_function=parse_vcsa_health_dns,
)


def discover_vcsa_health_dns(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_dns(params, section) -> CheckResult:
    if not section:
        return

    # A failed lookup must not present as an appliance with no name servers.
    if "error" in section:
        yield Result(
            state=State.UNKNOWN,
            summary="Unable to retrieve DNS configuration (HTTP %s)" % section["error"],
        )
        return

    servers = section["servers"]
    if not servers:
        yield Result(
            state=State(params["no_servers"]),
            summary="No DNS server configured",
        )
    else:
        yield Result(
            state=State.OK,
            summary="%d server(s): %s" % (len(servers), ", ".join(servers)),
        )

    if section["mode"]:
        yield Result(state=State.OK, notice="Mode: %s" % section["mode"])
    if section.get("hostname"):
        yield Result(
            state=State.OK, notice="Hostname (PNID): %s" % section["hostname"]
        )

    yield Metric("vcsa_dns_servers", len(servers))


check_plugin_vcsa_health_dns = CheckPlugin(
    name="vcsa_health_dns",
    service_name="VCSA DNS Configuration",
    sections=["vcsa_health_dns"],
    discovery_function=discover_vcsa_health_dns,
    check_function=check_vcsa_health_dns,
    check_ruleset_name="vcsa_health_dns",
    check_default_parameters={"no_servers": 2},
)
