#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA time synchronization and measured clock drift.
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
#   mode;<NTP|HOST|DISABLED>
#   drift;<seconds, signed>
#   clock;<date>;<time>;<timezone>
#   server;<address>;<status>;<message>

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
)

_REACHABLE = "SERVER_REACHABLE"


def parse_vcsa_health_timesync(string_table):
    section = {"mode": None, "servers": [], "drift": None, "clock": None}
    for line in string_table:
        if not line:
            continue
        if line[0] == "mode" and len(line) >= 2:
            section["mode"] = line[1]
        elif line[0] == "drift" and len(line) >= 2:
            try:
                section["drift"] = float(line[1])
            except ValueError:
                pass
        elif line[0] == "clock" and len(line) >= 2:
            section["clock"] = {
                "date": line[1],
                "time": line[2] if len(line) > 2 else "",
                "timezone": line[3] if len(line) > 3 else "",
            }
        elif line[0] == "server" and len(line) >= 2:
            section["servers"].append({
                "address": line[1],
                "status": line[2] if len(line) > 2 else "",
                "message": line[3] if len(line) > 3 else "",
            })
    if section["mode"] is None and not section["servers"] and section["drift"] is None:
        return None
    return section


agent_section_vcsa_health_timesync = AgentSection(
    name="vcsa_health_timesync",
    parse_function=parse_vcsa_health_timesync,
)


def discover_vcsa_health_timesync(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_timesync(params, section) -> CheckResult:
    if not section:
        return

    mode = section["mode"]
    if mode:
        if mode.upper() == "DISABLED":
            yield Result(
                state=State(params["mode_disabled"]),
                summary="Time synchronization is disabled",
            )
        else:
            yield Result(state=State.OK, summary="Mode: %s" % mode)

    # Drift is compared as a magnitude: an appliance running fast is as much of
    # a problem as one running slow.
    if section["drift"] is not None:
        yield from check_levels(
            abs(section["drift"]),
            levels_upper=params.get("drift_levels"),
            metric_name="vcsa_time_drift",
            label="Clock drift",
            render_func=lambda v: "%.2f s" % v,
        )

    clock = section["clock"]
    if clock:
        yield Result(
            state=State.OK,
            notice="Appliance time: %s %s %s"
            % (clock["date"], clock["time"], clock["timezone"]),
        )

    servers = section["servers"]
    if not servers:
        if mode and mode.upper() == "NTP":
            yield Result(
                state=State(params["no_servers"]),
                summary="No NTP server configured",
            )
        return

    rated = [s for s in servers if s["status"]]
    reachable = [s for s in rated if s["status"].upper() == _REACHABLE]

    if not rated:
        yield Result(
            state=State.OK,
            summary="%d server(s) configured, reachability not reported" % len(servers),
        )
    elif not reachable:
        yield Result(
            state=State(params["none_reachable"]),
            summary="No NTP server reachable (%d configured)" % len(rated),
        )
    elif len(reachable) < len(rated):
        yield Result(
            state=State(params["some_unreachable"]),
            summary="%d of %d NTP servers reachable" % (len(reachable), len(rated)),
        )
    else:
        yield Result(state=State.OK, summary="All %d NTP servers reachable" % len(rated))

    yield Metric("vcsa_ntp_servers_reachable", len(reachable), boundaries=(0, len(servers)))

    for server in servers:
        detail = server["address"]
        if server["status"]:
            detail += ": %s" % server["status"]
        if server["message"]:
            detail += " (%s)" % server["message"]
        yield Result(state=State.OK, notice=detail)


check_plugin_vcsa_health_timesync = CheckPlugin(
    name="vcsa_health_timesync",
    service_name="VCSA Time Synchronization",
    sections=["vcsa_health_timesync"],
    discovery_function=discover_vcsa_health_timesync,
    check_function=check_vcsa_health_timesync,
    check_ruleset_name="vcsa_health_timesync",
    check_default_parameters={
        "mode_disabled": 2,
        "no_servers": 2,
        "none_reachable": 2,
        "some_unreachable": 1,
        "drift_levels": ("fixed", (30.0, 300.0)),
    },
)
