#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA signing and trusted root certificate validity.
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
#   <item>;<valid_to epoch>

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


def parse_vcsa_health_certs(string_table):
    section = {}
    for line in string_table:
        if len(line) < 2:
            continue
        try:
            section[line[0]] = float(line[1])
        except ValueError:
            continue
    return section


agent_section_vcsa_health_certs = AgentSection(
    name="vcsa_health_certs",
    parse_function=parse_vcsa_health_certs,
)


def discover_vcsa_health_certs(section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_vcsa_health_certs(item, params, section) -> CheckResult:
    valid_to = section.get(item)
    if valid_to is None:
        return

    remaining = valid_to - time.time()
    if remaining <= 0:
        yield Result(
            state=State.CRIT,
            summary="Certificate expired %s ago" % render.timespan(-remaining),
        )
    else:
        yield from check_levels(
            remaining,
            levels_lower=params.get("validity_levels"),
            metric_name="vcsa_cert_remaining",
            label="Remaining validity",
            render_func=render.timespan,
        )
    yield Result(state=State.OK, notice="Expiry date: %s" % render.datetime(valid_to))


check_plugin_vcsa_health_certs = CheckPlugin(
    name="vcsa_health_certs",
    service_name="VCSA Certificate %s",
    sections=["vcsa_health_certs"],
    discovery_function=discover_vcsa_health_certs,
    check_function=check_vcsa_health_certs,
    check_ruleset_name="vcsa_health_certs",
    check_default_parameters={"validity_levels": ("fixed", (2592000.0, 1296000.0))},
)
